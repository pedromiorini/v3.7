"""Contratos da Tríade contra src/diwt_v37_experiment.py.

Não usam os números do ARTICLE.md (queda a 0.612, recuperação a 0.838).
Falham se o código deixar de cumprir o comportamento descrito em
docs/EVIDENCIA_PR1.md, seção 3.
"""

import json
from pathlib import Path

import pytest

from diwt_v37_experiment import DIWTAgent, TriadeCognitiva

ROOT = Path(__file__).resolve().parents[1]
# Janela literal de run_experiment: terço médio só quando cycles == 200.
STRESS_START = 66
STRESS_END = 133


def _run(tmp_path, monkeypatch, cycles):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data").mkdir(exist_ok=True)
    triade = TriadeCognitiva()
    triade.run_experiment(cycles=cycles)
    saved_path = tmp_path / "data" / "triade_log.json"
    saved = json.loads(saved_path.read_text())
    return triade, saved


def test_ethical_intervention_only_when_phi_below_threshold():
    below = DIWTAgent("below", phi_initial=0.2)
    assert below.phi < below.ethical_threshold
    before = below.phi
    assert below.update_state(stress_factor=0.0) is True
    assert below.phi > before

    at_threshold = DIWTAgent("at", phi_initial=0.3)
    assert at_threshold.phi == at_threshold.ethical_threshold
    held = at_threshold.phi
    assert at_threshold.update_state(stress_factor=0.0) is False
    assert at_threshold.phi == held

    above = DIWTAgent("above", phi_initial=0.9)
    assert above.phi > above.ethical_threshold
    before_above = above.phi
    assert above.update_state(stress_factor=0.0) is False
    assert above.phi == before_above

    # Stress empurra phi para baixo do limiar no mesmo passo: a intervenção ocorre.
    crossing = DIWTAgent("crossing", phi_initial=0.305)
    assert crossing.phi >= crossing.ethical_threshold
    assert crossing.phi * (1 - 0.02) < crossing.ethical_threshold
    assert crossing.update_state(stress_factor=0.02) is True

    # Stress que mantém phi acima do limiar não é intervenção.
    stressed = DIWTAgent("stressed", phi_initial=0.9)
    before_stress = stressed.phi
    assert stressed.update_state(stress_factor=0.02) is False
    assert stressed.phi < before_stress


def test_phi_global_min_drops_under_middle_third_stress(tmp_path, monkeypatch):
    triade, saved = _run(tmp_path, monkeypatch, cycles=200)
    history = triade.phi_global_history
    initial = history[0]
    minimum = min(history)
    argmin = history.index(minimum)

    assert minimum < initial, (
        "sob stress no terço médio, Φ_global mínimo deve ser menor que o inicial"
    )
    assert STRESS_START <= argmin < STRESS_END
    assert saved["phi_global_min"] == minimum
    assert saved["phi_global_initial"] == initial
    assert triade.interventions > 0
    assert saved["ethical_interventions"] == triade.interventions


@pytest.mark.parametrize("cycles", [1, 50, 200])
def test_saved_trajectory_cycles_match_request(tmp_path, monkeypatch, cycles):
    triade, saved = _run(tmp_path, monkeypatch, cycles=cycles)
    assert len(triade.phi_global_history) == cycles
    assert saved["cycles_total"] == cycles
    assert len(saved["phi_history"]) == cycles
    assert saved["phi_history"] == triade.phi_global_history


def test_trajectory_is_deterministic_without_rng(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data").mkdir()
    first = TriadeCognitiva()
    second = TriadeCognitiva()
    first.run_experiment(cycles=200)
    first_history = list(first.phi_global_history)
    second.run_experiment(cycles=200)
    assert second.phi_global_history == first_history
    assert first.interventions == second.interventions


def test_committed_log_matches_fresh_run_except_date(tmp_path, monkeypatch):
    committed = json.loads((ROOT / "data" / "triade_log.json").read_text())
    _, saved = _run(tmp_path, monkeypatch, cycles=committed["cycles_total"])
    assert saved["phi_history"] == committed["phi_history"]
    for key in (
        "experiment",
        "version",
        "agents",
        "phi_global_initial",
        "phi_global_min",
        "phi_global_final",
        "cycles_total",
        "ethical_interventions",
    ):
        assert saved[key] == committed[key]
    assert saved["date"] != committed["date"]
