# DIWT v4.0 — demonstração offline, não BCI fechado

Os scripts aqui implementam uma demo com dados EEGBCI públicos e um controlador de brinquedo. Eles não gravam EEG ao vivo nem demonstram um circuito BCI fechado.

## Arquivos e proveniência

- [`session_recording.json`](session_recording.json) — artefato legado preservado sem alterações. Não contém metadados de origem; os 100 registros têm `phi_eeg` igual a 2.0. Esse valor não é IIT Φ e o arquivo não comprova sessão humana ou correlação.
- [`record_first_session.py`](record_first_session.py) — exige um `.npy` EEGBCI com sidecar de proveniência gerado pelo downloader. Salva por padrão em `session_recording.generated.json`, sem substituir o arquivo legado.
- [`replay_session.py`](replay_session.py) — lê o JSON legado ou uma saída gerada; marca os campos legados como não verificados. A figura vai para um caminho novo e não é sobrescrita.
- [`diwt_v40_eegbci_baseline.pdf`](diwt_v40_eegbci_baseline.pdf) e o [Markdown-fonte](diwt_v40_eegbci_baseline.md) — nota técnica nova com o baseline offline CSP+LDA em dados públicos EEGBCI, incluindo métricas e limites; não é artigo revisado por pares.
- Para regenerar o PDF, instale `markdown` e `weasyprint` e rode `python3 scripts/render_eeg_baseline.py --output /tmp/diwt_v40_eegbci_baseline-preview.pdf`; o gerador parte do Markdown e nunca sobrescreve uma saída existente.
- `closed_loop_simulation_results.png` permanece sem validação de proveniência e não é evidência do baseline. O PDF/TeX legados foram movidos sem alteração para [`archive/unverified_legacy/`](archive/unverified_legacy/); eles contêm alegações não sustentadas e não devem ser distribuídos como resultado experimental.

## Reproduzir uma demo nova

A partir da raiz do repositório, a ingestão pode baixar o dataset EEGBCI do PhysioNet se ele não estiver em cache; instale MNE antes e use a rede apenas se desejar executar esse passo:

```bash
python eeg_phase2/download_eeg_data.py
python v4.0-closed-loop/record_first_session.py --seed 1
python v4.0-closed-loop/replay_session.py --session v4.0-closed-loop/session_recording.generated.json --no-delay
```

A demo rotula a contagem binária como um proxy simples, não como Φ de IIT. `phi_pred_simulated`, `phi_diwt_simulated` e `action_simulated` são gerados por simulação. Os scripts recusam substituir suas saídas já existentes; selecione novos caminhos via `--output` ou `--plot-output`. `--no-plot` evita criar figura.
