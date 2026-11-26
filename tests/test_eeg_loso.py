from pathlib import Path
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eeg_phase2 import classify_motor_imagery_loso as loso


def test_loso_holds_out_every_epoch_of_one_participant_and_partitions_all_epochs():
    subject_ids = np.array([1, 1, 1, 2, 2, 3, 3, 3, 3], dtype=np.int64)

    splits = loso.leave_one_subject_out_splits(subject_ids)

    assert [held_out for held_out, _, _ in splits] == [1, 2, 3]
    loso.validate_loso_integrity(subject_ids, splits)
    for held_out, train_idx, test_idx in splits:
        assert set(subject_ids[test_idx]) == {held_out}
        assert held_out not in set(subject_ids[train_idx])
        assert set(subject_ids[train_idx]) == ({1, 2, 3} - {held_out})
        assert set(train_idx).isdisjoint(test_idx)
        assert sorted(np.concatenate((train_idx, test_idx)).tolist()) == list(range(subject_ids.size))


def test_fit_predict_loso_fold_never_fits_on_the_held_out_participant():
    class RecordingModel:
        def fit(self, X, y):
            self.fit_subjects = set(X[:, 0, 0].astype(int).tolist())
            return self

        def predict(self, X):
            self.predict_subjects = set(X[:, 0, 0].astype(int).tolist())
            return ["left_hand"] * X.shape[0]

    subject_ids = np.array([1, 1, 2, 2, 3, 3], dtype=np.int64)
    X = np.zeros((6, 2, 3), dtype=np.float64)
    X[:, 0, 0] = subject_ids
    y = np.array(["left_hand", "right_hand"] * 3)
    model = RecordingModel()

    truth, predicted = loso.fit_predict_loso_fold(
        model, X, y, subject_ids, 2, [0, 1, 4, 5], [2, 3]
    )

    assert model.fit_subjects == {1, 3}
    assert model.predict_subjects == {2}
    assert truth.tolist() == ["left_hand", "right_hand"]
    assert predicted.tolist() == ["left_hand", "left_hand"]


def test_fit_predict_loso_fold_rejects_leaked_train_before_model_fit():
    class RecordingModel:
        fit_called = False

        def fit(self, X, y):
            self.fit_called = True

    subject_ids = np.array([1, 1, 2, 2, 3, 3], dtype=np.int64)
    X = np.zeros((6, 2, 3), dtype=np.float64)
    y = np.array(["left_hand", "right_hand"] * 3)
    model = RecordingModel()

    with pytest.raises(ValueError, match="leakage|held-out participant"):
        loso.fit_predict_loso_fold(model, X, y, subject_ids, 2, [0, 2, 4], [2, 3])

    assert model.fit_called is False


def test_channel_order_is_canonicalized_by_name_and_duplicate_names_fail_closed():
    values = np.array([[[4], [3], [9]]], dtype=np.float64)

    sorted_values, sorted_names = loso.canonicalize_channel_order(values, ["C4", "C3", "Cz"])

    assert sorted_names == ["C3", "C4", "Cz"]
    assert sorted_values.tolist() == [[[3.0], [4.0], [9.0]]]
    with pytest.raises(ValueError, match="unique"):
        loso.canonicalize_channel_order(values, ["C3", "C3", "Cz"])


@pytest.mark.parametrize("target", [True, "128", 60, 0, -1, np.nan, np.inf])
def test_target_sampling_frequency_rejects_invalid_values(target):
    with pytest.raises(ValueError):
        loso._validated_target_sampling_frequency(target)


def test_target_sampling_frequency_and_resampling_preserve_event_times():
    mne = pytest.importorskip("mne")

    assert loso._validated_target_sampling_frequency(None) is None
    assert loso._validated_target_sampling_frequency(128) == 128.0

    raw = mne.io.RawArray(
        np.zeros((2, 1600), dtype=np.float64),
        mne.create_info(["C3", "C4"], sfreq=160.0, ch_types="eeg"),
        verbose="ERROR",
    )
    raw.set_annotations(
        mne.Annotations(onset=[1.0, 4.0], duration=[0.0, 0.0], description=["T1", "T2"])
    )
    native_sfreq, processed_sfreq = loso._resample_raw(raw, 128.0)
    events, event_id = mne.events_from_annotations(
        raw, event_id={"T1": 1, "T2": 2}, verbose="ERROR"
    )
    raw.close()

    assert native_sfreq == 160.0
    assert processed_sfreq == 128.0
    assert event_id == {"T1": 1, "T2": 2}
    assert events[:, 0].tolist() == [128, 512]


@pytest.mark.parametrize("event_id", [{"T1": 1}, {"T2": 2}])
def test_missing_task_event_class_is_a_subject_exclusion(event_id):
    with pytest.raises(loso.SubjectEligibilityError, match="lacks task event") as captured:
        loso._require_both_task_event_ids(event_id, run=4)
    assert captured.value.reason_code == "missing_task_class"


def test_harmonized_variant_defaults_to_128hz_and_has_distinct_output_path():
    import inspect

    from eeg_phase2 import classify_motor_imagery_loso_strict as strict

    assert loso.DEFAULT_TARGET_SFREQ_HZ == 128.0
    assert inspect.signature(loso.run_analysis).parameters["target_sfreq_hz"].default == 128.0
    assert loso.DEFAULT_OUTPUT != strict.DEFAULT_OUTPUT
    assert "resampled-128hz" in loso.DEFAULT_OUTPUT.name
    assert "resampled" not in strict.DEFAULT_OUTPUT.name


def test_only_recognized_retrieval_failures_become_subject_exclusions(tmp_path):
    from requests.exceptions import Timeout

    class TimedOutEEGBCI:
        def load_data(self, **kwargs):
            raise Timeout("temporary network timeout")

    class BadChecksumEEGBCI:
        def load_data(self, **kwargs):
            raise ValueError(
                "MD5 hash of downloaded file (S001R04.edf) does not match the known hash"
            )

    with pytest.raises(loso.SubjectEligibilityError, match="MNE retries") as captured:
        loso._load_subject_epochs(None, TimedOutEEGBCI(), 1, tmp_path)
    assert captured.value.reason_code == "retrieval_or_file_integrity_failure"
    with pytest.raises(loso.SubjectEligibilityError, match="checksum") as captured:
        loso._load_subject_epochs(None, BadChecksumEEGBCI(), 1, tmp_path)
    assert captured.value.reason_code == "retrieval_or_file_integrity_failure"

    for unexpected_error in (
        ValueError("unexpected loader ValueError"),
        RuntimeError("unexpected loader RuntimeError"),
        TypeError("unexpected programming/API error"),
    ):
        class UnexpectedEEGBCI:
            def load_data(self, **kwargs):
                raise unexpected_error

        with pytest.raises(type(unexpected_error), match=str(unexpected_error)):
            loso._load_subject_epochs(None, UnexpectedEEGBCI(), 1, tmp_path)


def test_edf_reader_only_excludes_known_bad_header_and_propagates_other_errors(tmp_path):
    paths = []
    for run in loso.RUNS:
        path = tmp_path / f"S001R{run:02d}.edf"
        path.write_bytes(b"non-empty fixture")
        paths.append(path)

    class FakeEEGBCI:
        def load_data(self, **kwargs):
            return paths

    class FakeChannels:
        def make_standard_montage(self, name):
            return object()

    class FakeIO:
        def __init__(self, error):
            self.error = error

        def read_raw_edf(self, *args, **kwargs):
            raise self.error

    class FakeMNE:
        def __init__(self, error):
            self.channels = FakeChannels()
            self.io = FakeIO(error)

    with pytest.raises(loso.SubjectEligibilityError, match="invalid EDF header") as captured:
        loso._load_subject_epochs(
            FakeMNE(ValueError("Bad EDF file provided.")), FakeEEGBCI(), 1, tmp_path
        )
    assert captured.value.reason_code == "unreadable_edf"

    for unexpected_error in (
        ValueError("unexpected parser ValueError"),
        RuntimeError("unexpected parser RuntimeError"),
    ):
        with pytest.raises(type(unexpected_error), match=str(unexpected_error)):
            loso._load_subject_epochs(
                FakeMNE(unexpected_error), FakeEEGBCI(), 1, tmp_path
            )


def test_loso_respects_explicit_subject_order_but_requires_exact_subject_set():
    subject_ids = np.array([9, 9, 4, 4, 7], dtype=np.int64)

    splits = loso.leave_one_subject_out_splits(subject_ids, expected_subjects=[7, 9, 4])

    assert [held_out for held_out, _, _ in splits] == [7, 9, 4]
    with pytest.raises(ValueError, match="each expected participant"):
        loso.leave_one_subject_out_splits(subject_ids, expected_subjects=[4, 7])
    with pytest.raises(ValueError, match="duplicate"):
        loso.leave_one_subject_out_splits(subject_ids, expected_subjects=[4, 7, 7, 9])


@pytest.mark.parametrize(
    "subject_ids",
    [
        [],
        [[1, 1], [2, 2]],
        [1.0, 1.0, 2.0, 2.0],
        [True, True, False],
        [0, 0, 1, 1],
        [-1, -1, 2, 2],
        [1, 1, 1],
    ],
)
def test_loso_rejects_invalid_or_single_subject_input(subject_ids):
    with pytest.raises(ValueError):
        loso.leave_one_subject_out_splits(subject_ids)


def test_loso_integrity_fails_closed_on_epoch_leakage_and_bad_partition():
    subject_ids = np.array([1, 1, 2, 2, 3, 3], dtype=np.int64)
    valid = loso.leave_one_subject_out_splits(subject_ids)
    held_out, train_idx, test_idx = valid[0]

    leaked_train = np.append(train_idx, test_idx[0])
    with pytest.raises(ValueError, match="duplicate positions|leakage"):
        loso.validate_loso_integrity(subject_ids, [(held_out, leaked_train, test_idx), *valid[1:]])

    incomplete = np.delete(test_idx, 0)
    with pytest.raises(ValueError, match="partition every epoch"):
        loso.validate_loso_integrity(subject_ids, [(held_out, train_idx, incomplete), *valid[1:]])


def test_loso_integrity_rejects_test_fold_with_two_people():
    subject_ids = np.array([1, 1, 2, 2, 3, 3], dtype=np.int64)
    valid = loso.leave_one_subject_out_splits(subject_ids)
    held_out, train_idx, test_idx = valid[0]
    altered_test = np.array([test_idx[0], np.flatnonzero(subject_ids == 2)[0]])
    altered_train = np.setdiff1d(np.arange(subject_ids.size), altered_test)
    with pytest.raises(ValueError, match="test fold"):
        loso.validate_loso_integrity(subject_ids, [(held_out, altered_train, altered_test), *valid[1:]])


def test_bootstrap_is_reproducible_and_resamples_participants_as_units():
    scores = [1.0, 0.0, 0.5]

    first = loso.participant_bootstrap_interval(scores, seed=31, resamples=500)
    second = loso.participant_bootstrap_interval(scores, seed=31, resamples=500)

    assert first == second
    assert first["estimate_equal_participant_mean"] == pytest.approx(0.5)
    assert first["participant_count"] == 3
    assert "participants" in first["method"]


def test_primary_aggregate_weights_people_equally_not_epoch_counts():
    people = [
        {"accuracy": 1.0, "balanced_accuracy": 1.0, "confusion_matrix": [[100, 0], [0, 100]]},
        {"accuracy": 0.0, "balanced_accuracy": 0.0, "confusion_matrix": [[0, 1], [1, 0]]},
    ]
    aggregate = loso.aggregate_participant_metrics(
        people,
        ["left_hand"] * 100 + ["right_hand"] * 100 + ["left_hand", "right_hand"],
        ["left_hand"] * 100 + ["right_hand"] * 100 + ["right_hand", "left_hand"],
        seed=1,
        resamples=100,
    )

    assert aggregate["accuracy_equal_participant_mean"] == pytest.approx(0.5)
    assert aggregate["balanced_accuracy_equal_participant_mean"] == pytest.approx(0.5)
    assert aggregate["epoch_weighted_descriptive_only"]["accuracy"] == pytest.approx(200 / 202)
    assert aggregate["confusion_matrix_sum_counts"] == [[100, 1], [1, 100]]
    assert "descriptive" in aggregate["confusion_matrix_note"]


def test_edf_manifest_digest_is_ordered_and_hashes_exact_file_bytes(tmp_path):
    path_a = tmp_path / "S001R04.edf"
    path_b = tmp_path / "S001R08.edf"
    path_a.write_bytes(b"edf fixture one")
    path_b.write_bytes(b"edf fixture two")

    digest = loso._sha256_file(path_a)

    import hashlib
    assert digest == hashlib.sha256(b"edf fixture one").hexdigest()
    rows = [(1, 8, loso._sha256_file(path_b)), (1, 4, digest)]
    canonical = "\n".join(f"{subject:03d}:{run:02d}:{sha}" for subject, run, sha in sorted(rows))
    assert len(hashlib.sha256(canonical.encode()).hexdigest()) == 64


def test_default_cache_and_metrics_are_outside_clone():
    assert not loso.DEFAULT_DATA_DIR.resolve().is_relative_to(ROOT.resolve())
    assert not loso.DEFAULT_OUTPUT.resolve().is_relative_to(ROOT.resolve())


def test_bootstrap_rejects_invalid_values():
    with pytest.raises(ValueError, match="at least two participants"):
        loso.participant_bootstrap_interval([0.5])
    with pytest.raises(ValueError, match="within \\[0, 1\\]"):
        loso.participant_bootstrap_interval([0.2, 1.2])
    with pytest.raises(ValueError, match="positive integer"):
        loso.participant_bootstrap_interval([0.2, 0.8], resamples=0)
