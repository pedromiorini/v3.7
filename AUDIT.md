# Auditoria técnica e de evidência — DIWT v3.7 → v4.0

Data da revisão: 2026-11-20
Checkout: `master`, base `aab70b638f7b86cbda203032f5dc48fd6fc12702`
Estado ao fim da auditoria inicial (2026-11-20): alterações locais não commitadas; nenhum push ou publicação tinha sido feito. O estado atual está registrado ao fim deste relatório.

## Prompt de execução refinado

> Audite e melhore este repositório, primeiro verificando o checkout, os arquivos de instrução e as alterações locais. Separe fatos observados, inferências e hipóteses, e fundamente alegações científicas em fontes primárias confiáveis. Não transforme simulações em resultados reais por renomeação nem invente dados: preserve-as como simulações identificadas; quando uma tarefa real apropriada existir, implemente um baseline reproduzível com dados públicos e proveniência. Não alegue IIT Φ, consciência, eficácia ética, BCI online ou generalização sem experimento e validação adequados. Faça mudanças pequenas, reversíveis e testáveis, preserve os artefatos históricos e evite sobrescrita. Valide com testes offline, compilação e revisão de diff; registre os comandos, resultados e limites. Não faça commit ou publicação sem instrução.

## Achados e mudanças

1. **Simulação v3.7 não é uma medida de consciência.** `src/diwt_v37_experiment.py` atualiza três escalares por regras fixas e calcula sua média aritmética. O nome histórico `phi` não faz dela uma medida de IIT Φ. O log versionado `data/triade_log.json` descreve 200 ciclos, média inicial 0,850, mínimo 0,3123, valor final 0,3329 e oito intervenções da própria simulação. O código agora grava novas simulações em arquivo separado, com marcação explícita, e se recusa a substituir arquivos existentes.

2. **O visualizador antigo fabricava séries ausentes.** `src/visualizer_etico.py` gerava trajetória sintética quando faltava log, e sorteava valência/intervenções sem que essas séries existissem nos dados. Agora valida e plota apenas `phi_history` registrado, rejeita histórico ausente/inconsistente, usa rótulo não-IIT e cria figura em caminho novo. Valência, eventos por ciclo e comparação empírica não são inferidos.

3. **Sessão v4.0 legada não sustenta as alegações publicadas.** `v4.0-closed-loop/session_recording.json` não inclui proveniência; os 100 registros têm `phi_eeg=2.0` constante. Uma série constante não dá suporte a correlação 0,91. O PDF e o TeX antigos faziam alegações de correlação EEG humano e “traço de consciência”. Foram preservados byte a byte, mas movidos para `v4.0-closed-loop/archive/unverified_legacy/` e marcados explicitamente como não verificáveis, não como evidência. Em seu lugar, criei uma nota técnica em Markdown e PDF com o baseline CSP+LDA real, sem alegações fora do que os dados permitem.

4. **O fallback anterior misturava dados aleatórios com EEG.** `eeg_phase2/download_eeg_data.py` agora requer MNE, usa o caminho EDF retornado pelo MNE, não fabrica EEG, registra sidecar local e hash do array, e recusa sobrescrita. O cache EDF e o array processado padrão ficam em `~/.cache/diwt-v3.7-real-eeg/`; os parâmetros explícitos `--dataset-dir` e `--output` são rejeitados se apontarem para dentro do repositório. O sidecar/hash detecta troca ou corrupção acidental do array, mas não autentica independentemente o EDF nem o próprio sidecar.

5. **Baseline real adicionado, separado da simulação.** `eeg_phase2/classify_motor_imagery.py` usa o EEG Motor Movement/Imagery Database público do [PhysioNet](https://physionet.org/content/eegmmidb/1.0.0/), carregado pela [API EEGBCI do MNE](https://mne.tools/stable/generated/mne.datasets.eegbci.load_data.html), para sujeito 1, runs 4, 8 e 12. Nesses runs, T1/T2 são imagética unilateral de mão esquerda/direita. O baseline CSP+LDA usa filtro FIR 7–30 Hz, épocas 1–2 s após o evento e leave-one-run-out: um run inteiro é teste; CSP e LDA ajustam-se apenas nos outros dois. A escolha do pipeline segue o [tutorial oficial CSP do MNE](https://mne.tools/stable/auto_examples/decoding/decoding_csp_eeg.html).

### Resultado real de referência

Foram retidas 15 épocas por run (45 no total). Confusion matrices em ordem `[left_hand, right_hand]`, linhas reais e colunas previstas:

| Run de teste | Balanced accuracy | Acurácia | Matriz |
|---|---:|---:|---|
| 4 | 0,7857 | 0,8000 | `[[8, 0], [3, 4]]` |
| 8 | 0,4732 | 0,4667 | `[[3, 5], [3, 4]]` |
| 12 | 0,6161 | 0,6000 | `[[6, 1], [5, 3]]` |
| Agregado | 0,6196 | 0,6222 | `[[17, 6], [11, 11]]` |

O resultado é descritivo de um sujeito e três runs, não é avaliação populacional e não demonstra eficácia online. A nota técnica está em `v4.0-closed-loop/diwt_v40_eegbci_baseline.md` e `v4.0-closed-loop/diwt_v40_eegbci_baseline.pdf`. O JSON com métricas, hashes EDF, parâmetros, dependências e origem está fora do repositório em `/tmp/diwt-v37-eeg-baseline-verified-20261120.json` (SHA-256 `6fd52273d937300969010d5badfcbee61f3fa96a24d16db9615090034fb6a504`). O hash do script registrado no JSON coincide com o arquivo executado: `e9ce1b4bb6a028f60ee936bde009cacfdebcbb4a4d12ef4c6700ea472c688634`.

6. **Generalização entre participantes avaliada separadamente.** `eeg_phase2/classify_motor_imagery_loso_strict.py` tenta todos os 109 participantes e usa leave-one-subject-out. A análise estrita incluiu 106 (4.768 épocas) e excluiu 88, 92 e 100 por frequência nativa de 128 Hz, incompatível com os 160 Hz dos demais; balanced accuracy média com peso igual por participante foi 57,62% (IC95% bootstrap 55,48–59,89%), e acurácia 57,48% (55,33–59,72%). A variante `classify_motor_imagery_loso.py` reamostra cada run a 128 Hz antes do filtro/épocas, incluiu 109 participantes (4.918 épocas), balanced accuracy 57,69% (55,74–59,70%) e acurácia 57,54% (55,57–59,57%). Cada pessoa foi teste uma vez e nenhuma época da pessoa de teste entrou no ajuste. Protocolos: `eeg_phase2/LOSO_PROTOCOL.md` e `eeg_phase2/LOSO_PROTOCOL_RESAMPLED_128HZ.md`.

Os JSONs completos permanecem fora do Git em `/workspace/diwt-v37-eegbci-loso-results/`. A variante reamostrada é secundária e pós-hoc; compara simultaneamente cobertura diferente (109 versus 106) e processamento diferente (128 Hz comum versus frequências nativas), portanto a diferença entre os resultados não isola causalmente nenhum fator. Os ICs por participante não capturam toda a dependência entre folds LOSO.

## Validação executada

```bash
PYTHONDONTWRITEBYTECODE=1 /tmp/diwt-eegbci-loso-venv/bin/python -m pytest -q -p no:cacheprovider
# 57 passed

PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider
# 56 passed, 1 skipped (MNE is not installed in the base environment)

PYTHONPYCACHEPREFIX=/tmp/diwt-audit-pycache python3 -m py_compile \
  eeg_phase2/classify_motor_imagery.py \
  eeg_phase2/download_eeg_data.py \
  eeg_phase2/convergence_plot.py \
  src/diwt_v37_experiment.py src/visualizer_etico.py \
  v4.0-closed-loop/record_first_session.py \
  v4.0-closed-loop/replay_session.py \
  eeg_phase2/classify_motor_imagery_loso.py \
  eeg_phase2/classify_motor_imagery_loso_strict.py \
  tests/test_eeg_motor_imagery.py \
  tests/test_eeg_loso.py \
  tests/test_eeg_provenance.py \
  tests/test_v37_simulation_outputs.py

git diff --check
```

Os resultados atuais da suíte estão acima: 57 testes passaram no ambiente com MNE, e 56 passaram com um teste dependente de MNE pulado no ambiente base. Compilação, ajuda dos dois CLIs LOSO e `git diff --check` passaram. Foram conferidos os hashes byte a byte do log v3.7, sessão v4.0, PDF/TeX históricos arquivados e cinco PNGs contra backup anterior; os artefatos antigos permanecem inalterados. O novo PDF técnico de 2 páginas foi gerado a partir de Markdown por `scripts/render_eeg_baseline.py`; a execução repetida no mesmo caminho foi recusada como esperado. Nenhum EDF, FIF, NPY ou BDF está no clone. O baseline real foi executado separadamente com Python 3.12.3, MNE 1.13.2, NumPy 2.5.5, SciPy 1.18.1 e scikit-learn 1.9.1; EDFs públicos e JSON ficaram fora do repositório.

## Limites e pendências

- Uma pessoa, três runs e 45 épocas são evidência limitada; o fold do run 8 teve balanced accuracy 0,4732. Não se estima desempenho em novas pessoas, dias ou equipamentos.
- Não há hipótese nem medida de IIT Φ operacionalizada neste código; classificação de imagética motora não mede consciência, ética ou associação com a simulação DIWT.
- `eeg_phase2/download_eeg_data.py` busca o run 1, uma linha de base de olhos abertos segundo a documentação EEGBCI, não uma tarefa de imagética motora. Não é o caminho usado no baseline runs 4/8/12.
- O classificador guarda hashes EDF, mas não baixa dados brutos para Git. A análise pode requerer internet no primeiro uso.
- `MockDIWT`, `neural_state_mapper.py` (`train_mock_model`), o replay e curvas sintéticas permanecem protótipos; foram rotulados, não “convertidos” em fenômenos observados.
- Os arquivos em `v4.0-closed-loop/archive/unverified_legacy/` ainda contêm as afirmações não verificadas; eles foram preservados para histórico e não devem ser distribuídos como evidência. A nota nova é um relatório técnico limitado, não artigo revisado por pares.
- Na redação inicial deste relatório, nenhum commit havia sido criado e não havia mudança remota; veja o status atual abaixo.


## Revalidação delimitada dos quatro achados — 2026-11-25

Base revalidada: `master`, `aab70b638f7b86cbda203032f5dc48fd6fc12702`; `origin/master` continua nesse SHA. O checkout já tinha alterações locais antes desta etapa; elas foram preservadas. A PR pública aberta observada foi a #1, draft, base `master` nesse SHA e head `59aeca2bfedf8444e351e37fd8fbc3a5e872f29e`. Ela altera workflow, dependências e testes da Tríade, sem tocar os arquivos de implementação aqui corrigidos; seu único check-run observado no head foi `pytest: success`, enquanto o status combinado da API estava `pending`. A PR adiciona `tests/conftest.py`, ausente deste checkout, portanto esse contexto de testes não foi validado aqui.

1. **P2 — CONFIRMADO → CORRIGIDO (alta confiança):** `download_eeg_data.py` gravava por padrão em `~/.cache/diwt-v3.7-real-eeg/raw_eeg.npy`, enquanto `record_first_session.py` procurava `eeg_phase2/eeg_data/raw_eeg.npy`; assim, a sequência documentada sem `--input` falhava mesmo após a ingestão padrão. Os dois defaults agora apontam ao mesmo caminho, coberto por `tests/test_targeted_audit_fixes.py`.

2. **P2 — CONFIRMADO → CORRIGIDO (alta confiança):** `render_eeg_baseline.py` fazia uma checagem de existência antes de `write_pdf(output)`, deixando uma janela TOCTOU que permitia substituir um arquivo criado entre as operações. O PDF agora é renderizado em temporário no diretório de destino e publicado por `os.link`; uma criação concorrente causa `FileExistsError` e mantém o arquivo concorrente intacto. O teste reproduz essa corrida. A alternativa de gravar diretamente com modo exclusivo evita clobber, mas pode expor um arquivo parcial; staging mais link oferece publicação atômica completa. O [manual oficial do Python para `os.link`](https://docs.python.org/3/library/os.html#os.link) documenta a criação de hard link; o [manual Linux `link(2)`](https://man7.org/linux/man-pages/man2/link.2.html) especifica que o destino existente não é sobrescrito e que a operação retorna `EEXIST`. Filesystems sem suporte a hard links falharão sem fallback; o código usa temporário no mesmo diretório/filesystem.
3. **P2 — CONFIRMADO → CORRIGIDO (alta confiança):** `neural_state_mapper.py` descrevia a saída como medida de consciência, treinava com `torch.randn`/`torch.rand` e salvava em `neural_state_mapper.pth`. A documentação do código agora chama a saída de escalar arbitrário não validado e o treino de demonstração sintética, não EEG real, consciência ou IIT Φ. O checkpoint default é `~/.cache/diwt-v3.7-mock/neural_state_mapper.mock.generated.pth`; é publicado sem sobrescrita. O teste de publicação usa stub do serializador, não demonstra treinamento/modelo real.
4. **P3 — CONFIRMADO → DOCUMENTADO, JSONs preservados (alta confiança):** ambos os resultados LOSO históricos registram `execution.repository.branch` como `""`, impossibilitando identificar a branch a partir do JSON. O `eeg_phase2/README.md` agora explicita essa limitação. Nenhum resultado foi regenerado ou editado. Os SHA-256 observados antes das mudanças foram `e5938da1c2d90a4fe7c56d0994cb2b2d9f6887a31d577a389112cb779c5b5d90` (estrito) e `096e7a93dac39cfd5206bbd624d7d71c1919e32b281c6302136c9d7f40aa8aa6` (128 Hz); a verificação final deve mantê-los iguais.

**Validação desta etapa:** os três testes novos falharam antes das correções e passaram depois. `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider` passou com 59 testes e 1 skip; o skip é o teste que exige MNE, não instalado no Python base. `py_compile` passou para os quatro arquivos novos/alterados de código e teste. A renderização real de `v4.0-closed-loop/diwt_v40_eegbci_baseline.md` produziu um PDF de 2 páginas A4, versão 1.7, em `/tmp`, que foi removido após a verificação. A execução real do treino do mapper não foi testada porque PyTorch não está instalado; não foi baixado EEG nem reexecutado baseline/LOSO. Nenhum commit, push, merge ou publicação foi feito.

## Estado atual após publicação — 2026-11-26

O commit de atribuição `073b897075635ececfd98c8f378b1098ba294250` está publicado em `master`; `HEAD` e `origin/master` coincidem nesse SHA e a árvore de trabalho está limpa. Esse registro substitui qualquer status de “sem commit/publicação” nas seções históricas anteriores.
