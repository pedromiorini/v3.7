from pathlib import Path
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eeg_phase2 import classify_motor_imagery as decoder


def test_event_codes_map_to_left_and_right_hand_for_each_imagery_run():
    event_id = {"T1": 5, "T2": 11}

    for run in (4, 8, 12):
        labels = decoder.map_event_codes([5, 11, 5], run=run, event_id=event_id)
        assert labels.tolist() == ["left_hand", "right_hand", "left_hand"]


def test_event_mapping_rejects_execution_or_unknown_events():
    with pytest.raises(ValueError, match="motor-imagery runs"):
        decoder.map_event_codes([1], run=3, event_id={"T1": 1, "T2": 2})
    with pytest.raises(ValueError, match="unmapped event"):
        decoder.map_event_codes([0], run=4, event_id={"T1": 1, "T2": 2})


def test_leave_one_run_out_holds_out_entire_run_without_overlap():
    run_ids = np.array([4, 4, 4, 8, 8, 12, 12, 12])

    splits = decoder.leave_one_run_out_splits(run_ids)

    assert [held_out for held_out, _, _ in splits] == [4, 8, 12]
    for held_out, train_idx, test_idx in splits:
        train_runs = set(run_ids[train_idx])
        test_runs = set(run_ids[test_idx])
        assert test_runs == {held_out}
        assert train_runs == ({4, 8, 12} - {held_out})
        assert set(train_idx).isdisjoint(test_idx)


def test_leave_one_run_out_requires_each_expected_run():
    with pytest.raises(ValueError, match="each expected run"):
        decoder.leave_one_run_out_splits(np.array([4, 4, 8, 8]))


def test_binary_metrics_include_balanced_accuracy_accuracy_and_fixed_order_matrix():
    metrics = decoder.calculate_metrics(
        ["left_hand", "left_hand", "right_hand", "right_hand"],
        ["left_hand", "right_hand", "right_hand", "right_hand"],
    )

    assert metrics["accuracy"] == pytest.approx(0.75)
    assert metrics["balanced_accuracy"] == pytest.approx(0.75)
    assert metrics["confusion_matrix"] == [[1, 1], [0, 2]]
    assert metrics["labels"] == ["left_hand", "right_hand"]
    assert metrics["support"] == {"left_hand": 2, "right_hand": 2}


def test_metrics_fail_closed_when_a_test_class_is_missing():
    with pytest.raises(ValueError, match="both classes"):
        decoder.calculate_metrics(["left_hand", "left_hand"], ["left_hand", "right_hand"])


def test_results_writer_refuses_to_overwrite_existing_file(tmp_path):
    output = tmp_path / "metrics.json"
    output.write_text("preserve this\n", encoding="utf-8")

    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        decoder.write_results_exclusive({"accuracy": 0.5}, output)

    assert output.read_text(encoding="utf-8") == "preserve this\n"


def test_default_results_and_dataset_cache_are_outside_repository():
    assert not decoder.DEFAULT_OUTPUT.resolve().is_relative_to(ROOT.resolve())
    assert not decoder.DEFAULT_DATA_DIR.resolve().is_relative_to(ROOT.resolve())


def test_dataset_cache_inside_repository_is_rejected():
    with pytest.raises(ValueError, match="must be outside the repository"):
        decoder._ensure_outside_repository(ROOT / "eeg_phase2" / "eeg_data", "EEGBCI dataset cache")
