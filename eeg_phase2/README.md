# Dados EEG e demos exploratórias

Os scripts desta pasta não demonstram consciência, não calculam IIT Φ e não estabelecem convergência ou correlação EEG↔DIWT. Eles oferecem uma ingestão opcional de dados públicos EEGBCI, uma tarefa de classificação offline definida e exemplos de simulação.

## Ingestão EEGBCI

`download_eeg_data.py` usa MNE e `mne.datasets.eegbci.load_data` para obter o caminho local retornado pelo MNE, ler o EDF e aplicar um filtro passa-banda de 1–45 Hz. A função do MNE pode baixar dados do PhysioNet se ainda não estiverem no cache ([documentação oficial](https://mne.tools/stable/generated/mne.datasets.eegbci.load_data.html)). O comando, portanto, precisa de MNE e pode usar a rede:

```bash
python eeg_phase2/download_eeg_data.py
```

Por padrão, o script grava `~/.cache/diwt-v3.7-real-eeg/raw_eeg.npy` e `raw_eeg.provenance.json`; o cache EDF do MNE fica em `~/.cache/diwt-v3.7-real-eeg/eegbci`. Ambos são fora do repositório. `--output` e `--dataset-dir` podem receber caminhos explícitos, mas o downloader recusa qualquer caminho que, após resolução, fique dentro da raiz Git — antes de baixar ou gravar EEG. A saída inclui origem, processamento, dimensão, unidade, frequência amostral e SHA-256 do array. O gravador exige que checksum, formato e frequência coincidam com o sidecar; isso detecta troca ou corrupção acidental, mas não autentica o sidecar. Se MNE não estiver instalado, o downloader falha explicitamente; não fabrica dados. Também não sobrescreve saídas existentes e publica o par sem deixar saídas parciais em falhas normais. O downloader legado não faz parte da execução abaixo.

## Classificação offline de imagética motora com EEG humano público

`classify_motor_imagery.py` executa uma tarefa de duas classes com dados reais do [PhysioNet EEG Motor Movement/Imagery Database](https://physionet.org/content/eegmmidb/1.0.0/), obtidos por [`mne.datasets.eegbci.load_data`](https://mne.tools/stable/generated/mne.datasets.eegbci.load_data.html). Usa o sujeito 1 e somente os runs 4, 8 e 12. A documentação do dataset e do MNE identifica esses runs como imagética unilateral de mão; neste contexto T1 é imagética da mão/punho esquerdo e T2 da mão/punho direito. O significado de T1/T2 depende do run, então não se deve reaproveitar esse mapeamento para tarefas de mão/pé.

O protocolo usa validação leave-one-run-out: em cada fold, um run inteiro é teste e os outros dois são treino. Não divide épocas do mesmo run entre treino e teste; CSP e LDA são ajustados novamente apenas com os runs de treino de cada fold. A análise usa referência média projetada, montage `colin27_1005`, filtro FIR passa-banda 7–30 Hz, épocas de 1,0 a 2,0 s após o evento, CSP com 4 componentes (`log=True`, `norm_trace=False`) e `LinearDiscriminantAnalysis(solver="svd")`, seguindo o pipeline do [tutorial oficial CSP do MNE](https://mne.tools/stable/auto_examples/decoding/decoding_csp_eeg.html). Não há busca de hiperparâmetros neste conjunto.

Crie um ambiente virtual fora do repositório e instale as dependências; a primeira execução pode baixar os EDFs públicos para o cache indicado:

```bash
python3 -m venv /tmp/diwt-eeg-venv
/tmp/diwt-eeg-venv/bin/pip install mne scikit-learn
/tmp/diwt-eeg-venv/bin/python eeg_phase2/classify_motor_imagery.py \
  --dataset-dir "$HOME/.cache/diwt-v3.7-real-eeg/eegbci" \
  --output "$HOME/.cache/diwt-v3.7-real-eeg/subject-01-runs-04-08-12.json"
```

A saída padrão de métricas/proveniência é fora da árvore do repositório. `--output` permite escolher outro caminho, mas a saída nunca sobrescreve um arquivo existente. O cache de EEG bruto também precisa ficar fora do repositório; o script rejeita um diretório de dados dentro dele. O JSON registra arquivos-fonte e seus hashes, data/hora UTC, versões de Python/MNE/NumPy/scikit-learn, parâmetros, código de execução e métricas. Para cada run de teste e para as previsões agregadas, são informadas balanced accuracy, acurácia, matriz de confusão e suporte por classe. A balanced accuracy agregada é calculada das previsões concatenadas dos três folds, não é a média simples dos resultados por fold.

### Resultado da execução real de referência

Na execução de 2026-11-20, foram retidas 15 épocas por run (45 no total; 23 exemplos `left_hand` e 22 `right_hand`). A matriz de confusão abaixo usa linhas como classe real e colunas como classe prevista, na ordem `[left_hand, right_hand]`.

| Run inteiro de teste | Balanced accuracy | Acurácia | Matriz de confusão |
|---|---:|---:|---|
| 4 | 0,7857 | 0,8000 | `[[8, 0], [3, 4]]` |
| 8 | 0,4732 | 0,4667 | `[[3, 5], [3, 4]]` |
| 12 | 0,6161 | 0,6000 | `[[6, 1], [5, 3]]` |
| Agregado (45 previsões de teste) | 0,6196 | 0,6222 | `[[17, 6], [11, 11]]` |

O [relatório técnico em PDF](../v4.0-closed-loop/diwt_v40_eegbci_baseline.pdf) e seu [Markdown-fonte](../v4.0-closed-loop/diwt_v40_eegbci_baseline.md) registram os resultados e limites. O JSON com proveniência e resultados foi salvo fora do clone em `/tmp/diwt-v37-eeg-baseline-verified-20261120.json` (SHA-256 `6fd52273d937300969010d5badfcbee61f3fa96a24d16db9615090034fb6a504`). A primeira execução e a repetição após ajustar o nome do montage produziram as mesmas métricas. É um resultado descritivo de um sujeito em três runs, não uma estimativa de desempenho em outras pessoas, sessões ou condições.

## Avaliação entre participantes: leave-one-subject-out

Os scripts `classify_motor_imagery_loso_strict.py` e `classify_motor_imagery_loso.py` tentam todos os participantes EEGMMIDB de 1 a 109 e deixam cada participante inteiro de fora do treino uma vez. CSP e LDA são ajustados novamente dentro de cada fold; nenhum run ou época da pessoa de teste entra no treino. Os [protocolos fixos](LOSO_PROTOCOL.md) e [da variante harmonizada](LOSO_PROTOCOL_RESAMPLED_128HZ.md) descrevem elegibilidade, pipeline, métricas e fontes.

| Variante | Participantes incluídos | Excluídos | Épocas | Balanced accuracy média por participante (IC95%) | Acurácia média por participante (IC95%) |
|---|---:|---:|---:|---:|---:|
| Estrita, frequência nativa comum | 106 | 3 (88, 92, 100; 128 Hz versus 160 Hz) | 4.768 | 57,62% (55,48–59,89%) | 57,48% (55,33–59,72%) |
| Secundária, reamostrada a 128 Hz | 109 | 0 | 4.918 | 57,69% (55,74–59,70%) | 57,54% (55,57–59,57%) |

As métricas principais são médias com peso igual por participante; os ICs são bootstrap percentil com 10.000 reamostragens de participantes (seed `20261120`). As contagens pooled de épocas são descritivas. Os folds LOSO compartilham participantes nos conjuntos de treino, então esses intervalos não cobrem toda a incerteza do ajuste nem garantem desempenho numa nova população.

A execução estrita excluiu os IDs 88, 92 e 100 por incompatibilidade de frequência amostral nativa. A variante a 128 Hz foi criada depois dessa análise, reamostra todos os sinais antes do filtro e inclui os três. Ela é secundária/pós-hoc, não um holdout independente. Como muda simultaneamente a frequência processada e a cobertura de participantes, a diferença entre médias não isola o efeito de nenhuma das duas mudanças.

Os relatórios JSON completos foram mantidos fora do Git, em `/workspace/diwt-v37-eegbci-loso-results/eegbci_loso_runs_04_08_12_20261120.json` (estrita) e `/workspace/diwt-v37-eegbci-loso-results/eegbci_loso_runs_04_08_12_resampled128_20261120.json` (128 Hz). Os hashes SHA-256 dos scripts e do baseline helper registrados neles coincidem com os arquivos integrados. Nos dois registros históricos, `execution.repository.branch` está vazio (`""`); portanto, eles não identificam em qual branch foram executados, embora guardem commit e hashes de código. Os EDFs permanecem no cache externo; nenhum dado EEG bruto foi copiado para o repositório.

Para reproduzir em uma máquina com acesso à internet, instale MNE e scikit-learn num ambiente virtual. O primeiro uso pode baixar os EDFs públicos; mantenha o cache e os relatórios fora do clone, e escolha caminhos de saída novos porque os scripts nunca sobrescrevem resultados:

```bash
python3 -m venv /tmp/diwt-eegbci-loso-venv
/tmp/diwt-eegbci-loso-venv/bin/pip install mne scikit-learn

cache="$HOME/.cache/diwt-v37-eegbci-loso/eegbci"
out="$HOME/.cache/diwt-v37-eegbci-loso"
/tmp/diwt-eegbci-loso-venv/bin/python eeg_phase2/classify_motor_imagery_loso_strict.py \
  --dataset-dir "$cache" --output "$out/strict-20261120.json"
/tmp/diwt-eegbci-loso-venv/bin/python eeg_phase2/classify_motor_imagery_loso.py \
  --dataset-dir "$cache" --output "$out/resampled128-20261120.json"
```

O script estrito usa a frequência nativa comum e não aceita `--target-sfreq-hz`; a variante secundária usa 128 Hz por padrão. Para os testes offline, rode `python3 -m pytest -q tests/test_eeg_loso.py`; não baixam EEG, e o teste real de preservação dos tempos de evento é pulado se MNE não estiver instalado.

Os resultados descrevem somente decoding offline para um sujeito em três runs de um dataset público. Eles não demonstram IIT Φ, consciência, eficácia ética, generalização populacional ou desempenho de BCI online. O carregamento de dados públicos não transforma os exemplos `MockDIWT`, o gravador/reprodutor de demonstração, ou os campos simulados abaixo em medidas reais.

## Atribuição e referências

Este material contém informação da [EEG Motor Movement/Imagery Database (EEGMMIDB)](https://www.physionet.org/content/eegmmidb/1.0.0/), disponibilizada sob a [ODC Attribution License v1.0](https://www.physionet.org/content/eegmmidb/view-license/1.0.0/). O aviso identifica a fonte e a licença do banco de dados, mas não resolve eventuais direitos adicionais sobre conteúdos individuais, ressalvados pela própria licença.

Referências solicitadas pelo PhysioNet:

- Schalk, G. (2009). *EEG Motor Movement/Imagery Dataset* (version 1.0.0). PhysioNet. RRID:SCR_007345. [DOI: 10.13026/C28G6P](https://doi.org/10.13026/C28G6P).
- Schalk, G., McFarland, D.J., Hinterberger, T., Birbaumer, N., & Wolpaw, J.R. (2004). BCI2000: A General-Purpose Brain-Computer Interface (BCI) System. *IEEE Transactions on Biomedical Engineering, 51*(6), 1034–1043. [DOI: 10.1109/TBME.2004.827072](https://doi.org/10.1109/TBME.2004.827072).
- Pollard, T., Moody, B.E., Lehman, L., Gow, B., Fernandes, C., Xie, C., Johnson, A., Mark, R.G., & Heldt, T. (2026). PhysioNet as a global platform for biomedical research. *Nature Health*. [DOI: 10.1038/s44360-026-00096-z](https://doi.org/10.1038/s44360-026-00096-z).

Os testes unitários do classificador não acessam a rede nem exigem MNE ou scikit-learn:

```bash
python3 -m pytest -q tests/test_eeg_motor_imagery.py
```

## Demo offline

Depois de uma ingestão EEGBCI com sidecar válido, o gravador pode criar um JSON separado, sem tocar no arquivo arquivado:

```bash
python eeg_phase2/download_eeg_data.py
python v4.0-closed-loop/record_first_session.py --seed 1
```

A saída padrão do downloader (`~/.cache/diwt-v3.7-real-eeg/raw_eeg.npy`) é também o `--input` padrão do gravador; os dois comandos podem ser executados sem informar `--input`. A saída JSON padrão é `v4.0-closed-loop/session_recording.generated.json`; ela contém metadados de proveniência, a contagem de símbolos binários por bloco e valores explicitamente simulados para previsão/controlador. `eeg_binary_symbol_count` é apenas uma contagem de valores após limiarização pela mediana, não é Φ de IIT. A previsão, o controlador `MockDIWT` e as ações são simulados, não são sinais ou comandos de um BCI em tempo real. O gravador recusa arrays sem sidecar EEGBCI correspondente, sidecars marcados como sintéticos ou sem frequência amostral válida, e caminhos de saída já existentes. O sidecar é metadado local, não prova independente da procedência do arquivo.

Para ler uma sessão gerada, passe-a explicitamente ao reprodutor. A reprodução não sobrescreve arquivos e permite desativar a figura:

```bash
python v4.0-closed-loop/replay_session.py --session v4.0-closed-loop/session_recording.generated.json --no-delay
```

## Outros scripts e artefatos

- `neural_state_mapper.py` contém `train_mock_model`, uma demonstração com entradas `torch.randn` e alvos `torch.rand`; não treina com EEG real, não é um decodificador validado e seu escalar não mede consciência nem IIT Φ. PyTorch é necessário; a disponibilidade de Mamba também depende do ambiente. Se executada, a rotina grava apenas pesos de demonstração em `~/.cache/diwt-v3.7-mock/neural_state_mapper.mock.generated.pth`, sem sobrescrever um arquivo existente.
- `convergence_plot.py` gera duas curvas sintéticas e compara as curvas geradas; não carrega EEG. A saída nova é identificada como sintética e o script recusa sobrescrita.
- A figura versionada `visualizations_v37/eeg_convergence.png` é mantida intacta; sua proveniência não foi verificada nesta correção.

Não há base neste checkout para afirmar correlação experimental, validade de uma medida de consciência ou gravação humana ao vivo.
