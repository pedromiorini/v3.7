import json
from pathlib import Path

import pytest

from src.diwt_v37_experiment import DEFAULT_OUTPUT as SIMULATION_DEFAULT_OUTPUT
from src.diwt_v37_experiment import TriadeCognitiva
from src.visualizer_etico import load_results, plot_state_trajectory

ROOT = Path(__file__).resolve().parents[1]


def test_simulation_writes_labeled_log_to_new_path_and_refuses_overwrite(tmp_path):
    output = tmp_path / "triade.generated.json"
    saved = TriadeCognitiva().run_experiment(cycles=5, output_path=output)

    assert saved == output.resolve()
    result = json.loads(saved.read_text(encoding="utf-8"))
    assert result["record_type"] == "toy_simulation"
    assert result["simulation_status"] == "simulated"
    assert "not IIT Phi" in result["scalar_semantics"]
    assert result["cycles_total"] == 5
    assert len(result["phi_history"]) == 5
    assert result["threshold_interventions"] >= 0
    original = saved.read_bytes()

    another_simulation = TriadeCognitiva()
    another_simulation.phi_global_history = [0.5]
    with pytest.raises(FileExistsError):
        another_simulation.save_results(saved)
    assert saved.read_bytes() == original

    assert SIMULATION_DEFAULT_OUTPUT.name == "triade_log.generated.json"
    assert SIMULATION_DEFAULT_OUTPUT != ROOT / "data" / "triade_log.json"


def test_visualizer_plots_recorded_log_to_new_path_and_refuses_overwrite(tmp_path):
    archived_log = load_results(ROOT / "data" / "triade_log.json")
    output = tmp_path / "state.generated.png"

    saved = plot_state_trajectory(archived_log, output)
    assert saved == output.resolve()
    original = saved.read_bytes()
    assert original.startswith(b"\x89PNG\r\n\x1a\n")

    with pytest.raises(FileExistsError):
        plot_state_trajectory(archived_log, saved)
    assert saved.read_bytes() == original


def test_visualizer_rejects_missing_or_inconsistent_history_without_output(tmp_path):
    output = tmp_path / "must-not-be-created.png"
    with pytest.raises(ValueError, match="non-empty recorded phi_history"):
        plot_state_trajectory({"cycles_total": 200}, output)
    assert not output.exists()

    malformed = tmp_path / "malformed.json"
    malformed.write_text(json.dumps({"cycles_total": 3, "phi_history": [0.4, 0.5]}), encoding="utf-8")
    with pytest.raises(ValueError, match="cycles_total does not match"):
        load_results(malformed)
    assert not output.exists()
