[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Release v4.0](https://img.shields.io/github/v/release/pedromiorini/v3.7?label=Release)](https://github.com/pedromiorini/v3.7/releases/tag/v4.0.0)
[![Stars](https://img.shields.io/github/stars/pedromiorini/v3.7?style=social)](https://github.com/pedromiorini/v3.7)
# DIWT v3.7 → v4.0: simulações e protótipos

[Artigo e código v3.7](ARTICLE.md) · [Fase EEG e limitações](eeg_phase2/README.md) · [Demo offline](v4.0-closed-loop/README.md)

## Simulação v3.7 e visualização do log

`python src/diwt_v37_experiment.py` grava uma nova simulação em `data/triade_log.generated.json`; passe `--output` e `--cycles` para escolher caminho e duração. O script recusa substituir qualquer arquivo existente. `python src/visualizer_etico.py` lê o log versionado `data/triade_log.json` e grava `visualizations_v37/01_state_trajectory.generated.png`; use `--input` ou `--output` para outros caminhos. A figura mostra somente a média escalar registrada da simulação, não IIT Φ. O visualizador falha se o histórico estiver ausente/inconsistente e não recria as figuras históricas de valência, intervenções ou comparação, cujas séries não estão registradas no log.

## Análise real de EEG público

`eeg_phase2/classify_motor_imagery.py` faz decodificação offline de imagética de mão esquerda/direita em EEG humano público do [PhysioNet EEGMMIDB](https://physionet.org/content/eegmmidb/1.0.0/), usando CSP+LDA e leave-one-run-out para o sujeito 1 nos runs 4, 8 e 12. Na execução documentada foram 45 épocas, com balanced accuracy agregada de 0,6196 e acurácia de 0,6222. O resultado é de um sujeito e três runs; não demonstra desempenho em outras pessoas, BCI online, consciência, IIT Φ ou eficácia ética. Os parâmetros, matrizes por run, proveniência, comandos e limites estão em [eeg_phase2/README.md](eeg_phase2/README.md).

Também há uma avaliação leave-one-subject-out com os 109 participantes tentados: o protocolo estrito inclui 106 (balanced accuracy média por participante 57,62%; IC95% 55,48–59,89%), e uma variante secundária reamostra todos a 128 Hz e inclui 109 (57,69%; IC95% 55,74–59,70%). A variante de 128 Hz é pós-hoc e muda tanto o processamento quanto a cobertura; não atribua a diferença entre as estimativas a uma só dessas mudanças. [Protocolos e resultados detalhados](eeg_phase2/README.md).

Este repositório também contém simulações e protótipos. A sessão v4.0 versionada não documenta uma sessão humana: o JSON não tem proveniência e `phi_eeg` vale 2.0 em todos os registros. Esse valor não é IIT Φ nem sustenta uma correlação com EEG. O PDF/TeX v4.0 antigo foi preservado em `v4.0-closed-loop/archive/unverified_legacy/`, claramente marcado como não verificado; não o use como evidência experimental. O novo [relatório técnico EEGBCI](v4.0-closed-loop/diwt_v40_eegbci_baseline.pdf) descreve somente a classificação offline medida.

Para reproduzir apenas a visualização legada, execute:

```bash
python v4.0-closed-loop/replay_session.py --no-delay
```

A reprodução marca os campos legados como não verificados. Por padrão, cria um PNG de prévia em um caminho novo e recusa sobrescrever arquivos; use `--no-plot` para não gerar figura. A demo EEG e o controlador `MockDIWT` continuam sendo simulações offline, não uma gravação ao vivo.
