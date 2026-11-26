# DIWT v3.7: simulação de atualização de estados em três agentes

## O que o código representa

O código v3.7 é uma simulação determinística de três valores escalares, com redução programada durante um intervalo de estresse e um incremento fixo quando um valor cai abaixo do limiar. Embora o código use o nome `phi`, a variável global é apenas a média aritmética dos três valores dos agentes; não é uma implementação nem uma medida de IIT Φ. O resultado não demonstra consciência, resiliência emergente ou eficácia ética em pessoas.

## Log versionado

O `data/triade_log.json` versionado contém 200 ciclos: média inicial 0,850, mínimo 0,3123, valor final 0,3329 e oito intervenções registradas. Esses números descrevem a simulação e seu log, não uma observação empírica. O código aplica estresse nos ciclos 66–132 (índices iniciados em zero); o log não mostra retorno ao valor inicial.

O visualizador atual usa somente `phi_history` registrado, rejeita histórico ausente/inconsistente e grava `visualizations_v37/01_state_trajectory.generated.png` sem substituir figuras existentes. Ele não inventa séries de valência, intervenções ou comparação. Uma nova execução da simulação grava `data/triade_log.generated.json`, identificada como simulação, e também recusa sobrescrever arquivos. As figuras históricas foram preservadas; a proveniência de figuras antigas não foi verificada.

[Ver código da simulação](src/diwt_v37_experiment.py) · [Ver log versionado](data/triade_log.json)

## Análise real de imagética motora EEGBCI

Para adicionar uma análise baseada em sinal humano público, `eeg_phase2/classify_motor_imagery.py` usa a base [EEG Motor Movement/Imagery Database do PhysioNet](https://physionet.org/content/eegmmidb/1.0.0/) por meio da [API EEGBCI do MNE](https://mne.tools/stable/generated/mne.datasets.eegbci.load_data.html). O experimento usa o sujeito 1, runs 4/8/12 e, apenas nesse contexto de imagética unilateral, mapeia T1 para mão esquerda e T2 para mão direita. O pipeline CSP+LDA, o filtro, as épocas, a separação por run, as versões e hashes dos EDFs estão na documentação da [fase EEG](eeg_phase2/README.md).

Na execução de referência, cada fold manteve um run inteiro fora do treino: 15 épocas por run, 45 previsões no total. As linhas da matriz são a classe real e as colunas a prevista, na ordem `[left_hand, right_hand]`.

| Run inteiro de teste | Balanced accuracy | Acurácia | Matriz de confusão |
|---|---:|---:|---|
| 4 | 0,7857 | 0,8000 | `[[8, 0], [3, 4]]` |
| 8 | 0,4732 | 0,4667 | `[[3, 5], [3, 4]]` |
| 12 | 0,6161 | 0,6000 | `[[6, 1], [5, 3]]` |
| Agregado (45 previsões) | 0,6196 | 0,6222 | `[[17, 6], [11, 11]]` |

Este resultado descreve somente um sujeito em três runs. Não demonstra generalização populacional, desempenho de BCI online, IIT Φ, consciência, eficácia ética nem correlação entre atividade cerebral e a simulação DIWT. O JSON com métricas e proveniência foi salvo fora do repositório: `/tmp/diwt-v37-eeg-baseline-verified-20261120.json`.

## Avaliação entre participantes

Uma análise LOSO complementar manteve cada participante inteiro fora do treino e tentou todos os 109 IDs da EEGMMIDB. Sem reamostragem, 106 participantes foram elegíveis e 3 (88, 92 e 100) foram excluídos por frequência nativa diferente; balanced accuracy média por participante: 57,62% (IC95% bootstrap: 55,48–59,89%) em 4.768 épocas. A variante secundária, reamostrada a 128 Hz, incluiu 109 participantes e 4.918 épocas; balanced accuracy: 57,69% (55,74–59,70%). Acurácia e intervalos completos, matrizes, proveniência e comandos estão em [eeg_phase2/README.md](eeg_phase2/README.md), com protocolos em [LOSO estrito](eeg_phase2/LOSO_PROTOCOL.md) e [128 Hz](eeg_phase2/LOSO_PROTOCOL_RESAMPLED_128HZ.md).

A análise de 128 Hz é pós-hoc e altera processamento e participantes incluídos, por isso não é comparação causal nem independente. Os intervalos reamostram participantes, mas folds LOSO compartilham participantes de treino; a incerteza de ajuste/modelo não fica inteiramente representada. Os resultados continuam limitados a uma base pública, uma tarefa e um pipeline offline.

## Atribuição e referências

Este material contém informação da [EEG Motor Movement/Imagery Database (EEGMMIDB)](https://www.physionet.org/content/eegmmidb/1.0.0/), disponibilizada sob a [ODC Attribution License v1.0](https://www.physionet.org/content/eegmmidb/view-license/1.0.0/). O aviso identifica a fonte e a licença do banco de dados, mas não resolve eventuais direitos adicionais sobre conteúdos individuais, ressalvados pela própria licença.

Referências solicitadas pelo PhysioNet:

- Schalk, G. (2009). *EEG Motor Movement/Imagery Dataset* (version 1.0.0). PhysioNet. RRID:SCR_007345. [DOI: 10.13026/C28G6P](https://doi.org/10.13026/C28G6P).
- Schalk, G., McFarland, D.J., Hinterberger, T., Birbaumer, N., & Wolpaw, J.R. (2004). BCI2000: A General-Purpose Brain-Computer Interface (BCI) System. *IEEE Transactions on Biomedical Engineering, 51*(6), 1034–1043. [DOI: 10.1109/TBME.2004.827072](https://doi.org/10.1109/TBME.2004.827072).
- Pollard, T., Moody, B.E., Lehman, L., Gow, B., Fernandes, C., Xie, C., Johnson, A., Mark, R.G., & Heldt, T. (2026). PhysioNet as a global platform for biomedical research. *Nature Health*. [DOI: 10.1038/s44360-026-00096-z](https://doi.org/10.1038/s44360-026-00096-z).

## Limites das alegações v4.0

A sessão `v4.0-closed-loop/session_recording.json` não contém metadados de origem e registra `phi_eeg=2.0` em todos os 100 ciclos. Uma série constante não sustenta uma correlação de 0,91. O PDF e o TeX legados, agora em `v4.0-closed-loop/archive/unverified_legacy/`, alegam correlação com EEG humano e “traço de consciência”; esses enunciados não são verificados pelos dados do checkout e não devem ser tratados como resultados experimentais. Uma nota técnica nova, baseada somente no baseline público de imagética motora, está em [PDF](v4.0-closed-loop/diwt_v40_eegbci_baseline.pdf) e [Markdown](v4.0-closed-loop/diwt_v40_eegbci_baseline.md).

O pipeline opcional em `eeg_phase2/` pode baixar dados EEGBCI públicos para uma tarefa de classificação offline. O gravador/reprodutor de demonstração, `MockDIWT`, o neural-state mapper e as figuras históricas de origem não verificada continuam sendo simulações ou artefatos não validados; consulte [eeg_phase2/README.md](eeg_phase2/README.md) para a proveniência e as limitações.
