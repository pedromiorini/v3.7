# CONTINUATION — DIWT v3.7 → v4.0

## Estado do checkout

Clone `/workspace/diwt-v3.7`, branch `master`, HEAD/base `aab70b638f7b86cbda203032f5dc48fd6fc12702`. A árvore local contém alterações não commitadas; nenhum stage, commit, push ou publicação foi feito. Backups fora do clone: pré-integração real EEG `/workspace/.diwt-v3.7-pre-real-eeg-integration-20261120.tar.gz` (SHA-256 `7f8ee5646029377fe4b0a32f27ddae5859220e48df196ee78024a6044ac22769`) e pré-integração LOSO `/workspace/.diwt-v3.7-pre-loso-integration-20261120.tar.gz` (SHA-256 `995894d86f6a958d98044b193b0f26d039dada8c9b1b3d321d950acdedb289f3`).

## Mudanças e evidência

- A simulação v3.7 aplica regras determinísticas a três escalares e grava a média aritmética; o nome `phi` não representa IIT Φ. Novas saídas vão para caminhos `.generated.json` exclusivos.
- O visualizador v3.7 lê somente a série registrada; não gera séries substitutas de valência ou intervenções, rejeita logs inválidos e grava novas imagens sem sobrescrita.
- O pipeline de ingestão EEGBCI não inventa EEG. Requer MNE, usa o caminho retornado pela API, registra proveniência local e hash do array, e impede gravar cache ou saída EEG dentro do repositório. Sidecar/hash não autenticam a origem independente do EDF.
- A sessão `v4.0-closed-loop/session_recording.json` não tem proveniência e mantém `phi_eeg=2.0` constante. O TeX/PDF legado alegavam correlação 0,91 e “traço de consciência”; dados atuais não sustentam essas frases. Foram preservados byte a byte em `v4.0-closed-loop/archive/unverified_legacy/`. A nota técnica atual baseada no baseline está em `v4.0-closed-loop/diwt_v40_eegbci_baseline.md` e `.pdf`.
- `scripts/render_eeg_baseline.py` regenera esse PDF a partir do Markdown e recusa sobrescrita. PDF final SHA-256: `9fbb278a4db8d0426ada1dbe92e558d1bf90e4c289336b74a8a577d94d4a2aec`.
- Adicionado `eeg_phase2/classify_motor_imagery.py`: EEGMMIDB/PhysioNet sujeito 1, runs 4/8/12, T1/T2 mão esquerda/direita, CSP+LDA e validação por run inteiro. Na execução real, 15 épocas/run (45 total); balanced accuracy por run: 0,7857, 0,4732, 0,6161; agregado 0,6196; acurácia agregada 0,6222. Limites: um sujeito, três runs, offline; não é IIT Φ, consciência, eficácia ética, generalização populacional nem BCI online.
- Métricas/proveniência reais em `/tmp/diwt-v37-eeg-baseline-verified-20261120.json`; SHA-256 `6fd52273d937300969010d5badfcbee61f3fa96a24d16db9615090034fb6a504`. EDFs/cache ficam fora do clone.
- Integrada a avaliação leave-one-subject-out com scripts separados: `eeg_phase2/classify_motor_imagery_loso_strict.py` (frequências nativas, 106 incluídos, 3 excluídos por frequência) e `eeg_phase2/classify_motor_imagery_loso.py` (128 Hz comum, 109 incluídos). Resultados estritos: 4.768 épocas, balanced accuracy média por participante 57,62% (IC95% 55,48–59,89%), acurácia 57,48% (55,33–59,72%). Variante secundária/pós-hoc: 4.918 épocas, balanced accuracy 57,69% (55,74–59,70%), acurácia 57,54% (55,57–59,57%). Em ambos, 109 tentativas de participante e nenhum vazamento entre treino/teste.
- Protocolos fixados em `eeg_phase2/LOSO_PROTOCOL.md` e `eeg_phase2/LOSO_PROTOCOL_RESAMPLED_128HZ.md`; suíte offline nova em `tests/test_eeg_loso.py`. Os dois JSONs completos ficam fora do Git em `/workspace/diwt-v37-eegbci-loso-results/`. Os SHA-256 dos scripts e do baseline helper registrados nos JSON coincidem com os arquivos integrados. A variante de 128 Hz foi criada após a análise estrita e muda processamento e cobertura ao mesmo tempo; não interprete a diferença de resultados como efeito isolado.
- Ver `AUDIT.md` para achados, fontes, prompt refinado e riscos residuais.

## Comandos e validação

```bash
PYTHONDONTWRITEBYTECODE=1 /tmp/diwt-eegbci-loso-venv/bin/python -m pytest -q -p no:cacheprovider
# 57 passed

PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider
# 56 passed, 1 skipped (teste temporal dependente de MNE)

python3 scripts/render_eeg_baseline.py --output /tmp/diwt-v40-baseline-preview.pdf
# PDF válido de 2 páginas; a segunda chamada ao mesmo caminho é recusada

git diff --check
```

Também passaram `py_compile` dos scripts e testes listados em `AUDIT.md`. Verificação do clone não encontrou EDF/FIF/NPY/BDF; os dados brutos de PhysioNet não foram guardados nele. O baseline single-subject e as duas análises LOSO foram executados em ambiente temporário com Python 3.12.3, MNE 1.13.2, NumPy 2.5.5, SciPy 1.18.1 e scikit-learn 1.9.1. A suíte offline não baixa dados nem depende desses resultados remotos.

## Pendências

- Não distribuir os arquivos em `archive/unverified_legacy/` como evidência; usar a nova nota técnica apenas para descrever o baseline offline, com as limitações nela registradas.
- A LOSO estima desempenho em participantes retidos dentro da EEGMMIDB e do pipeline fixo; os participantes observados não representam automaticamente outras populações, aparelhos, tarefas ou condições. Folds LOSO compartilham dados de treino, então bootstrap por participante não captura toda a incerteza do ajuste.
- A análise reamostrada a 128 Hz é secundária/pós-hoc e não independente da estrita. As duas variantes não isolam causalmente o efeito de frequência ou a inclusão de três participantes.
- `neural_state_mapper.py`/`train_mock_model`, controlador `MockDIWT`, demos e curvas sintéticas continuam sendo simulações explicitamente documentadas.
- Nenhum commit foi criado; revisar o diff inteiro antes de qualquer commit.


## Revalidação delimitada — 2026-11-25

Base `master`/`origin/master`: `aab70b638f7b86cbda203032f5dc48fd6fc12702`; a árvore já estava suja e os diffs preexistentes foram mantidos. Sem commit ou push.

- Alinhado o `--input` padrão de `record_first_session.py` a `download_eeg_data.py`, ambos em `~/.cache/diwt-v3.7-real-eeg/raw_eeg.npy`; o README agora mostra a sequência de comandos sem `--input`.

- `scripts/render_eeg_baseline.py` renderiza em arquivo temporário no destino e publica com `os.link`, que falha se outra execução criou o destino primeiro; a regressão manteve os bytes concorrentes e confirmou a limpeza do temporário.
- `neural_state_mapper.py` agora declara que os tensores e alvos são aleatórios, que seu escalar não mede EEG/consciência/IIT Φ e que o checkpoint é uma demo. Salva em `~/.cache/diwt-v3.7-mock/neural_state_mapper.mock.generated.pth`, sem sobrescrita.
- Ambos JSONs LOSO permanecem inalterados; o campo histórico `execution.repository.branch` é `""`, portanto não identifica a branch. SHA-256 observado: estrito `e5938da1c2d90a4fe7c56d0994cb2b2d9f6887a31d577a389112cb779c5b5d90`; 128 Hz `096e7a93dac39cfd5206bbd624d7d71c1919e32b281c6302136c9d7f40aa8aa6`.

### Verificação desta etapa

```bash
# Regressões antes da correção: 3 falharam como esperado
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider tests/test_targeted_audit_fixes.py
# depois da correção: 3 passed

PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider
# 59 passed, 1 skipped (teste temporal dependente de MNE)

python3 scripts/render_eeg_baseline.py --output /tmp/diwt-v37-render-check-bae6260dde0245c888ea4cf287c787b6.pdf
pdfinfo /tmp/diwt-v37-render-check-bae6260dde0245c888ea4cf287c787b6.pdf
# PDF válido: 2 páginas, A4, versão 1.7; arquivo de verificação removido

PYTHONPYCACHEPREFIX=/tmp/diwt-v37-pycache python3 -m py_compile \
  v4.0-closed-loop/record_first_session.py scripts/render_eeg_baseline.py \
  eeg_phase2/neural_state_mapper.py tests/test_targeted_audit_fixes.py
```

O teste do mapper usa stub apenas para validar a publicação exclusiva do checkpoint. PyTorch não está instalado, logo treino real não foi executado. MNE também não está instalado; não houve download nem repetição das análises EEG. A pesquisa da publicação atômica consultou a [documentação de `os.link` do Python](https://docs.python.org/3/library/os.html#os.link) e o [manual Linux `link(2)`](https://man7.org/linux/man-pages/man2/link.2.html); um filesystem sem hard links continuará falhando explicitamente, sem fallback com risco de sobrescrita.

## Correção delimitada — gravação de sessão — 2026-11-25

Base `master`/`origin/master`: `aab70b638f7b86cbda203032f5dc48fd6fc12702`. A árvore já continha alterações locais; a mudança desta etapa ficou limitada a `v4.0-closed-loop/record_first_session.py`, `tests/test_eeg_provenance.py` e este registro. `save_session()` agora serializa em temporário no mesmo diretório, faz `flush`/`fsync` e publica por hard link exclusivo. Falha durante a serialização deixa o destino ausente e remove o temporário; uma colisão concorrente gera `FileExistsError` e preserva os bytes concorrentes. Os testes novos foram observados falhando antes da correção (2 falhas reproduzidas). Nenhum JSON histórico LOSO foi editado; sem commit ou push.

### Verificação desta etapa

```bash
# Antes da implementação: as duas regressões falharam pelos defeitos esperados
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider tests/test_eeg_provenance.py -k 'write_failure_does_not_publish or racing_destination_collision'
# 2 failed, 13 deselected

PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider tests/test_eeg_provenance.py
# 15 passed

PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider
# 61 passed, 1 skipped

PYTHONPYCACHEPREFIX=/tmp/diwt-v37-save-session-pycache python3 -m py_compile \
  v4.0-closed-loop/record_first_session.py tests/test_eeg_provenance.py
git diff --check
```

Os testes são offline: injetam uma falha após escrita parcial e simulam um escritor concorrente criando o destino durante a serialização. A publicação exclusiva depende de hard links no filesystem; se indisponíveis, a operação falha explicitamente, sem fallback sujeito a sobrescrita. Não foram testadas falhas físicas de energia nem a durabilidade do diretório após reinicialização. O único teste ignorado na suíte completa continua sendo o que depende de MNE, indisponível no Python base.


## Correção dos bloqueios da revisão independente — 2026-11-25

Base `master`/`origin/master`: `aab70b638f7b86cbda203032f5dc48fd6fc12702`. As alterações locais preexistentes foram preservadas. Esta etapa não fez stage, commit ou push.

- Corrigido o limite inferior do IC95% da balanced accuracy LOSO estrita para 55,48% em `ARTICLE.md`, `README.md`, `AUDIT.md`, neste `CONTINUATION.md` e `eeg_phase2/README.md`; o limite superior continua 59,89%. O JSON externo foi lido, não alterado: limite inferior `0.5548256945406248`, superior `0.5989419835957726`, SHA-256 `e5938da1c2d90a4fe7c56d0994cb2b2d9f6887a31d577a389112cb779c5b5d90`.
- `v4.0-closed-loop/replay_session.py` agora valida ciclos e métricas EEG/predição/DIWT como números finitos antes de imprimir ou plotar. Texto inválido, booleanos, NaN, infinitos e frames malformados geram `ValueError` explícito. O gerador também valida antes de criar o diretório de saída; a criação do PNG continua exclusiva e os rótulos existentes foram preservados.
- Adicionadas regressões offline em `tests/test_eeg_provenance.py` para texto inválido e NaN em métricas/ciclos, ausência de impressão/arquivo/diretório em erro e validação direta do gerador. Antes da correção, os cinco novos casos falharam reproduzindo o defeito; depois, o arquivo de proveniência passou com 20 testes.

### Verificação desta correção

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider tests/test_eeg_provenance.py
# 20 passed

PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider
# 66 passed, 1 skipped (teste dependente de MNE no ambiente base)

PYTHONPYCACHEPREFIX=/tmp/diwt-v37-replay-pycache python3 -m py_compile \
  v4.0-closed-loop/replay_session.py tests/test_eeg_provenance.py
# passed

git diff --check
# passed
```

Não houve nova execução dos experimentos EEG nem edição dos JSONs históricos. O checkout permanece sem stage/commit/push; a árvore contém outras alterações locais anteriores, preservadas.
