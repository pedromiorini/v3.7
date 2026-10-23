# Evidência PR1 — endurecimento mínimo (DIWT v3.7)

Critérios pré-registrados **antes** da implementação de requirements, CI, testes e `.gitignore`.
Fonte: brief `CRITERIOS_PR1` (2026-10-23, America/Sao_Paulo). Este arquivo não autoriza alterar `ARTICLE.md` nem o PDF.

Os critérios das seções 1–4 ficam congelados. A seção 5 só recebe comandos e saídas depois da execução; não reescreve o que foi pré-registrado para encaixar o resultado.

## 0. Estado no momento do registro

| Item | Valor |
| --- | --- |
| Repositório | https://github.com/pedromiorini/v3.7 |
| Branch base | `master` |
| HEAD da auditoria e deste clone | `aab70b638f7b86cbda203032f5dc48fd6fc12702` |
| Workflows em `.github/workflows` | nenhum (`list_workflows = 0`) |
| PRs abertos | nenhum (`gh pr list --state open` → `[]`) |
| `requirements.txt` / `pyproject.toml` / `tests/` | ausentes |
| Código do experimento | `src/diwt_v37_experiment.py` (`TriadeCognitiva`, `DIWTAgent`) |

## 1. Objetivo único

PR **draft** (sem merge) de endurecimento mínimo reprodutível:

1. `requirements.txt` com as dependências do experimento Tríade e dos testes (`numpy`, `pytest`). `matplotlib` só entra se algum teste importar `src/visualizer_etico.py`.
2. `.github/workflows/ci.yml`: em `push` e `pull_request` para `master`, instalar as deps e rodar `pytest`.
3. Testes de contrato em `tests/` para `TriadeCognitiva` / `DIWTAgent`, contra o comportamento real de `src/diwt_v37_experiment.py`, não contra os números do `ARTICLE.md`:
   - sob stress no terço médio, Φ_global mínimo &lt; Φ_global inicial;
   - intervenção ética ocorre quando `phi < ethical_threshold`;
   - trajetória salva/retornada tem `cycles` coerente com o pedido.
   - determinismo/seed só se o código usar aleatoriedade. Se não houver gerador, o contrato é a igualdade da trajetória entre corridas (sem exigir semente).
4. Ampliar `.gitignore` para artefatos LaTeX (`*.aux`, `*.log`, `*.blg`, `*.out`, `*.bbl`, `*.toc` e afins). Não apagar PDF, `.tex` nem JSON já versionados. Não remover os `.aux/.log/.blg/.out/.bbl` já commitados em `v4.0-closed-loop/`.
5. Este arquivo, com os critérios, os comandos rodados e o modo de falsificar.

## 2. Fora de escopo

- Mudar claims de `ARTICLE.md` ou do PDF NeurIPS.
- Refatorar `eeg_phase2/`, Mamba ou OpenBCI.
- Apagar artefatos LaTeX já commitados (gitignore não os tira do índice).
- Publicar no X.
- Merge.

Nenhum outro arquivo deve entrar no PR.

## 3. Contratos que os testes codificam

Leitura do código vigente (não é correção):

- `DIWTAgent.update_state` multiplica `phi` por `(1 - stress_factor)` e devolve `True` somente quando, depois disso, `phi < ethical_threshold` (limiar default `0.3`). Nesse caso soma `0.05` antes de retornar.
- `TriadeCognitiva.run_experiment` aplica `stress = 0.02` só na janela literal `66 <= cycle < 133`. Essa janela é o terço médio de uma corrida de 200 ciclos (0–65, 66–132, 133–199). Para outros `cycles`, a janela **não** é recalculada.
- Cada ciclo acrescenta um ponto a `phi_global_history`. `save_results` grava `data/triade_log.json` com `cycles_total == len(phi_history)`. O método não retorna a trajetória; o contrato “salva/retornada” cobre a lista em memória e o JSON.
- Não há `seed` nem `np.random` nesse módulo. Duas instâncias com o mesmo `cycles` produzem a mesma `phi_history`. O campo `date` muda porque usa `datetime.now()`.

Os testes devem falhar se esse comportamento quebrar: stress que não reduz Φ, intervenção que não dispara abaixo do limiar (ou dispara em `phi >= limiar` sem o stress cruzar o limiar), ou `cycles_total` / tamanho da trajetória diferente do `cycles` pedido.

Proibido no teste: assertar Φ → 0.612 ou recuperação → 0.838.

## 4. Fato a investigar depois (não corrigir neste PR)

`ARTICLE.md` (seção Results) afirma:

> Φ global drops to 0.612 under stress, recovers to 0.838 in 78 cycles.

`data/triade_log.json` (commit `aab70b6`, campo `date` = `2025-11-03T00:54:06.463006`) registra:

| Campo | Valor no arquivo |
| --- | --- |
| `phi_global_initial` | 0.85 |
| `phi_global_min` | 0.31231248896941505 |
| `phi_global_final` | 0.33294491440622626 |
| `cycles_total` | 200 |
| `ethical_interventions` | 8 |

Divergência: o artigo descreve queda até 0.612 e recuperação até 0.838; o log versionado tem mínimo ≈ 0.312 e final ≈ 0.333. Este PR não altera `ARTICLE.md`, o PDF nem o JSON. A divergência fica registrada para um PR posterior, com teste que falhe primeiro se alguém for “corrigir” o número.

Artefatos LaTeX já rastreados e que permanecem no índice: `v4.0-closed-loop/diwt_v40_neurips.{aux,log,blg,out,bbl}`. O `.gitignore` novo só evita que cópias futuras entrem no stage.

## 5. Comandos e resultados

Preenchido depois da execução. As seções 1–4 não foram reescritas.

Ambiente local: Python 3.12.3, numpy 1.26.4 já presente no sistema, pytest 9.1.1 instalado com `python3 -m pip install --user 'pytest>=8.3.0'`. `python3 -m venv` falhou (`ensurepip` ausente); não houve venv limpo nesta máquina. O CI (abaixo) instala `requirements.txt` do zero.

```bash
python3 -m pytest -v
```

```text
platform linux -- Python 3.12.3, pytest-9.1.1, pluggy-1.7.0
collected 7 items

tests/test_triade_contract.py::test_ethical_intervention_only_when_phi_below_threshold PASSED
tests/test_triade_contract.py::test_phi_global_min_drops_under_middle_third_stress PASSED
tests/test_triade_contract.py::test_saved_trajectory_cycles_match_request[1] PASSED
tests/test_triade_contract.py::test_saved_trajectory_cycles_match_request[50] PASSED
tests/test_triade_contract.py::test_saved_trajectory_cycles_match_request[200] PASSED
tests/test_triade_contract.py::test_trajectory_is_deterministic_without_rng PASSED
tests/test_triade_contract.py::test_committed_log_matches_fresh_run_except_date PASSED

7 passed in 0.08s
```

`git status --short` depois do pytest: vazio. `data/triade_log.json` não mudou (os testes gravam o JSON num diretório temporário). `.pytest_cache/` está ignorado.

CI no commit de testes `631b3282677b1ef5533df0c1f4bd2f0ee9816d72` (anterior a este registro):

- Run: https://github.com/pedromiorini/v3.7/actions/runs/39905823992
- Job `pytest`: success em 2026-10-23T05:27:24Z
- Runner: `ubuntu-latest` (imagem Ubuntu 26.04), Python 3.12.15
- `pip install -r requirements.txt` resolveu numpy 2.5.4 e pytest 9.1.1
- Saída: `7 passed in 0.10s`

Este commit só acrescenta a seção 5. O workflow dispara de novo no head da PR; o check desse head é o que fecha o critério de CI, não o run 39905823992.

Arquivos no diff contra `origin/master` até o commit de testes:

```text
.github/workflows/ci.yml
.gitignore
docs/EVIDENCIA_PR1.md
requirements.txt
tests/conftest.py
tests/test_triade_contract.py
```

`ARTICLE.md`, o PDF e os `.aux/.log/.blg/.out/.bbl` de `v4.0-closed-loop/` continuam rastreados e fora do diff.

### Como falsificar este PR

- Um teste da seção 3 falha no head do PR → o contrato não se sustenta; o PR não está aceito.
- `pytest` passa mas o teste cita 0.612 ou 0.838 como valor esperado → o teste não é o contrato pré-registrado.
- O diff toca `ARTICLE.md`, o PDF, `eeg_phase2/` ou apaga `.aux/.log/.blg/.out/.bbl` já commitados → fora de escopo.
- CI do head não fica verde e não há saída local de `pytest` nesta seção → critério de aceite aberto.
- O merge foi feito → viola o brief.
