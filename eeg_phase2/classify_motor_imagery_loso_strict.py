"""Leave-one-subject-out evaluation for PhysioNet EEGBCI motor imagery.

This additive experiment reuses the single-subject baseline's fixed labels,
metrics, preprocessing constants, and safe-output helpers. It is offline
classification only; it does not measure consciousness, IIT Phi, clinical
utility, online BCI performance, or general intelligence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

try:  # Support both ``python eeg_phase2/script.py`` and package-style imports.
    from . import classify_motor_imagery as baseline
except ImportError:  # pragma: no cover - exercised by the command-line entry point
    import classify_motor_imagery as baseline


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[1]
SUBJECT_IDS = tuple(range(1, 110))
RUNS = baseline.RUNS
CLASS_LABELS = baseline.CLASS_LABELS
DATASET_URL = baseline.DATASET_URL
DEFAULT_DATA_DIR = Path.home() / ".cache" / "diwt-v37-eegbci-loso" / "eegbci"
DEFAULT_OUTPUT = Path.home() / ".cache" / "diwt-v37-eegbci-loso" / "loso-runs-04-08-12.json"
BOOTSTRAP_SEED = 20261120
BOOTSTRAP_RESAMPLES = 10_000
SUBJECT_FILENAME = re.compile(r"S(\d+)R(\d+)\.edf$", flags=re.IGNORECASE)

INCLUSION_RULE = (
    "Attempt all EEGMMIDB subject IDs 1..109 in ascending order; include a subject only if "
    "all runs 4, 8, and 12 are present/readable, each run retains both T1 and T2 classes, and the "
    "standardized EEG channel names and sampling frequency match the first eligible participant. "
    "Channel order is canonicalized by sorted channel name. Exclude only for explicitly recognized "
    "retrieval, file-integrity, preprocessing/data-quality, channel-schema, or class/run completeness "
    "failure; never exclude based on classification performance. Unexpected exceptions abort the run."
)
LIMITATIONS = [
    "This is offline decoding of experimental motor-imagery labels, not online BCI or clinical validation.",
    "The evaluation estimates transfer to held-out participants only within EEGMMIDB, this run/task definition, and the fixed pipeline.",
    "Participant-level bootstrap intervals quantify between-participant variability in this dataset; they are not a guarantee of performance on a new population or device.",
    "The results do not measure IIT Phi (Φ), consciousness, ethical efficacy, or any DIWT/Nexus simulation claim.",
]


class SubjectEligibilityError(Exception):
    """A predeclared, subject-specific data issue that can be reported as an exclusion."""

    def __init__(self, reason_code: str, message: str):
        super().__init__(message)
        self.reason_code = reason_code


def _is_pooch_checksum_mismatch(error: ValueError) -> bool:
    """Recognize only Pooch's explicit downloaded-file checksum failure message."""
    message = str(error).lower()
    return "hash of downloaded file" in message and "does not match the known hash" in message


def _integer_vector(values: Sequence[int] | np.ndarray, name: str) -> np.ndarray:
    array = np.asarray(values)
    if array.ndim != 1 or array.size == 0 or not np.issubdtype(array.dtype, np.integer):
        raise ValueError(f"{name} must be a non-empty one-dimensional integer sequence.")
    if np.issubdtype(array.dtype, np.bool_) or np.any(array <= 0):
        raise ValueError(f"{name} must contain positive participant IDs, not booleans or non-positive values.")
    return array.astype(np.int64, copy=False)


def leave_one_subject_out_splits(
    subject_ids: Sequence[int] | np.ndarray,
    *,
    expected_subjects: Sequence[int] | np.ndarray | None = None,
) -> list[tuple[int, np.ndarray, np.ndarray]]:
    """Return whole-participant holdouts as (held-out ID, train indices, test indices).

    Every epoch belonging to a participant is assigned to exactly one test fold;
    that participant is absent from that fold's training set.
    """
    ids = _integer_vector(subject_ids, "subject_ids")
    present = set(int(value) for value in np.unique(ids))
    if expected_subjects is None:
        ordered = tuple(sorted(present))
    else:
        expected_array = _integer_vector(expected_subjects, "expected_subjects")
        ordered = tuple(int(value) for value in expected_array)
        if len(set(ordered)) != len(ordered):
            raise ValueError("expected_subjects must not contain duplicate IDs.")
        if present != set(ordered):
            raise ValueError(
                "subject_ids must contain each expected participant exactly as a group; "
                f"expected {tuple(sorted(ordered))}, found {tuple(sorted(present))}."
            )
    if len(ordered) < 2:
        raise ValueError("leave-one-subject-out requires at least two distinct participants.")

    splits: list[tuple[int, np.ndarray, np.ndarray]] = []
    for held_out in ordered:
        test_idx = np.flatnonzero(ids == held_out)
        train_idx = np.flatnonzero(ids != held_out)
        if not test_idx.size or not train_idx.size:
            raise ValueError(f"participant {held_out} has no test or training epochs.")
        splits.append((held_out, train_idx, test_idx))
    validate_loso_integrity(ids, splits, expected_subjects=ordered)
    return splits


def validate_loso_integrity(
    subject_ids: Sequence[int] | np.ndarray,
    splits: Sequence[tuple[int, Sequence[int] | np.ndarray, Sequence[int] | np.ndarray]],
    *,
    expected_subjects: Sequence[int] | np.ndarray | None = None,
) -> None:
    """Fail closed unless folds partition epochs and hold out each participant intact."""
    ids = _integer_vector(subject_ids, "subject_ids")
    present = set(int(value) for value in np.unique(ids))
    expected = tuple(sorted(present)) if expected_subjects is None else tuple(
        int(value) for value in _integer_vector(expected_subjects, "expected_subjects")
    )
    if len(set(expected)) != len(expected) or set(expected) != present:
        raise ValueError("expected_subjects must be a unique, exact match for participants in subject_ids.")
    if len(expected) < 2 or len(splits) != len(expected):
        raise ValueError("there must be exactly one LOSO fold per participant and at least two participants.")

    seen_holdouts: list[int] = []
    all_indices = np.arange(ids.size, dtype=np.int64)
    for held_out, train_values, test_values in splits:
        if isinstance(held_out, (bool, np.bool_)) or not isinstance(held_out, (int, np.integer)):
            raise ValueError("each held-out participant ID must be an integer.")
        held_out = int(held_out)
        if held_out not in present or held_out in seen_holdouts:
            raise ValueError("each present participant must be held out exactly once.")
        train_idx = _integer_indices(train_values, ids.size, "train indices")
        test_idx = _integer_indices(test_values, ids.size, "test indices")
        if not train_idx.size or not test_idx.size:
            raise ValueError(f"participant {held_out} has an empty train or test partition.")
        if np.intersect1d(train_idx, test_idx).size:
            raise ValueError(f"epoch-index leakage detected for held-out participant {held_out}.")
        combined = np.sort(np.concatenate((train_idx, test_idx)))
        if not np.array_equal(combined, all_indices):
            raise ValueError(f"fold for participant {held_out} does not partition every epoch exactly once.")
        train_subjects = set(int(value) for value in np.unique(ids[train_idx]))
        test_subjects = set(int(value) for value in np.unique(ids[test_idx]))
        if test_subjects != {held_out}:
            raise ValueError(f"test fold for participant {held_out} contains another participant or is incomplete.")
        if train_subjects != (present - {held_out}):
            raise ValueError(f"training fold for participant {held_out} leaks the test person or omits a person.")
        seen_holdouts.append(held_out)
    if set(seen_holdouts) != present:
        raise ValueError("LOSO folds do not cover every participant exactly once.")


def _integer_indices(values: Sequence[int] | np.ndarray, size: int, name: str) -> np.ndarray:
    indices = np.asarray(values)
    if indices.ndim != 1 or not np.issubdtype(indices.dtype, np.integer) or np.issubdtype(indices.dtype, np.bool_):
        raise ValueError(f"{name} must be a one-dimensional integer sequence.")
    if np.any(indices < 0) or np.any(indices >= size) or np.unique(indices).size != indices.size:
        raise ValueError(f"{name} contain out-of-range or duplicate positions.")
    return indices.astype(np.int64, copy=False)


def canonicalize_channel_order(
    epoch_data: np.ndarray,
    channel_names: Sequence[str],
) -> tuple[np.ndarray, list[str]]:
    """Sort epoch channels by name so equal feature indices denote equal sensors."""
    data = np.asarray(epoch_data)
    names = list(channel_names)
    if data.ndim != 3 or data.shape[1] != len(names) or not names:
        raise ValueError("epoch_data must have one channel axis entry for every channel name.")
    if any(not isinstance(name, str) or not name for name in names) or len(set(names)) != len(names):
        raise ValueError("channel_names must be unique, non-empty strings.")
    order = sorted(range(len(names)), key=lambda index: names[index])
    return data[:, order, :], [names[index] for index in order]


def fit_predict_loso_fold(
    model: Any,
    X: np.ndarray,
    y: Sequence[str] | np.ndarray,
    subject_ids: Sequence[int] | np.ndarray,
    held_out_subject: int,
    train_idx: Sequence[int] | np.ndarray,
    test_idx: Sequence[int] | np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Validate the fold boundary immediately before fitting, then return truth and predictions."""
    ids = _integer_vector(subject_ids, "subject_ids")
    features = np.asarray(X)
    labels = np.asarray(y, dtype=str)
    if features.ndim != 3 or features.shape[0] != ids.size or labels.shape != ids.shape:
        raise ValueError("X, y, and subject_ids must align as epochs x channels x samples.")
    train = _integer_indices(train_idx, ids.size, "train indices")
    test = _integer_indices(test_idx, ids.size, "test indices")
    if np.intersect1d(train, test).size:
        raise ValueError("epoch-index leakage detected between train and test.")
    if not train.size or not test.size:
        raise ValueError("train and test partitions must both be non-empty.")
    if np.any(ids[train] == held_out_subject) or set(int(value) for value in np.unique(ids[test])) != {int(held_out_subject)}:
        raise ValueError("held-out participant must be absent from train and be the only participant in test.")
    model.fit(features[train], labels[train])
    predicted = np.asarray(model.predict(features[test]), dtype=str)
    truth = labels[test]
    if predicted.shape != truth.shape:
        raise ValueError("model predictions must contain exactly one label per held-out epoch.")
    return truth, predicted


def participant_bootstrap_interval(
    scores: Sequence[float] | np.ndarray,
    *,
    seed: int = BOOTSTRAP_SEED,
    resamples: int = BOOTSTRAP_RESAMPLES,
) -> dict[str, Any]:
    """Percentile CI for the equal-participant mean, resampling participants as units."""
    values = np.asarray(scores, dtype=np.float64)
    if values.ndim != 1 or values.size < 2 or not np.isfinite(values).all():
        raise ValueError("scores must be a finite one-dimensional vector for at least two participants.")
    if np.any(values < 0.0) or np.any(values > 1.0):
        raise ValueError("participant scores must be within [0, 1].")
    if isinstance(seed, bool) or not isinstance(seed, (int, np.integer)) or seed < 0:
        raise ValueError("seed must be a non-negative integer.")
    if isinstance(resamples, bool) or not isinstance(resamples, (int, np.integer)) or resamples < 1:
        raise ValueError("resamples must be a positive integer.")
    rng = np.random.default_rng(int(seed))
    sampled = rng.integers(0, values.size, size=(int(resamples), values.size))
    bootstrap_means = values[sampled].mean(axis=1)
    low, high = np.quantile(bootstrap_means, [0.025, 0.975], method="linear")
    return {
        "estimate_equal_participant_mean": float(values.mean()),
        "confidence_level": 0.95,
        "lower_percentile": float(low),
        "upper_percentile": float(high),
        "method": "percentile bootstrap over participants; one participant score per resampled unit",
        "resamples": int(resamples),
        "seed": int(seed),
        "participant_count": int(values.size),
    }


def aggregate_participant_metrics(
    participant_results: Sequence[Mapping[str, Any]],
    y_true: Sequence[str] | np.ndarray,
    y_pred: Sequence[str] | np.ndarray,
    *,
    seed: int = BOOTSTRAP_SEED,
    resamples: int = BOOTSTRAP_RESAMPLES,
) -> dict[str, Any]:
    """Summarize equal-weight participant scores, cluster intervals, and descriptive confusion counts."""
    if len(participant_results) < 2:
        raise ValueError("aggregate metrics require at least two included participants.")
    matrices = np.asarray([entry["confusion_matrix"] for entry in participant_results], dtype=np.int64)
    if matrices.shape != (len(participant_results), 2, 2) or np.any(matrices < 0):
        raise ValueError("participant confusion matrices must be non-negative 2x2 matrices.")
    row_support = matrices.sum(axis=2)
    if np.any(row_support == 0):
        raise ValueError("each participant must have both classes in its test truth.")
    row_normalized = matrices / row_support[:, :, np.newaxis]
    per_subject_accuracy = [float(entry["accuracy"]) for entry in participant_results]
    per_subject_ba = [float(entry["balanced_accuracy"]) for entry in participant_results]
    epoch_weighted = baseline.calculate_metrics(y_true, y_pred)
    return {
        "participant_count": len(participant_results),
        "accuracy_equal_participant_mean": float(np.mean(per_subject_accuracy)),
        "accuracy_participant_bootstrap_95ci": participant_bootstrap_interval(
            per_subject_accuracy, seed=seed, resamples=resamples
        ),
        "balanced_accuracy_equal_participant_mean": float(np.mean(per_subject_ba)),
        "balanced_accuracy_participant_bootstrap_95ci": participant_bootstrap_interval(
            per_subject_ba, seed=seed, resamples=resamples
        ),
        "confusion_matrix_sum_counts": matrices.sum(axis=0).tolist(),
        "mean_participant_row_normalized_confusion_matrix": row_normalized.mean(axis=0).tolist(),
        "confusion_matrix_note": (
            "sum_counts is descriptive and pools epoch counts; the equal-participant metrics and bootstrap "
            "intervals are the primary aggregate and use participants, not epochs, as units."
        ),
        "epoch_weighted_descriptive_only": epoch_weighted,
    }


def _filename_subject_run(path: Path) -> tuple[int, int]:
    match = SUBJECT_FILENAME.search(path.name)
    if match is None:
        raise ValueError(f"Cannot identify EEGBCI participant/run from returned filename {path.name!r}.")
    return int(match.group(1)), int(match.group(2))


def _sha256_file(path: Path) -> str:
    return baseline._sha256_file(path)


def _load_subject_epochs(
    mne: Any,
    eegbci: Any,
    subject: int,
    dataset_dir: Path,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[dict[str, Any]]]:
    """Load and validate all three runs for one person before making them eligible."""
    from requests.exceptions import RequestException

    try:
        returned_paths = eegbci.load_data(
            subjects=int(subject),
            runs=list(RUNS),
            path=str(dataset_dir),
            update_path=False,
            verbose=False,
        )
    except RequestException as exc:
        raise SubjectEligibilityError(
            "retrieval_or_file_integrity_failure",
            f"EEGBCI retrieval/cache failed after MNE retries: {type(exc).__name__}: {exc}",
        ) from exc
    except ValueError as exc:
        if not _is_pooch_checksum_mismatch(exc):
            raise
        raise SubjectEligibilityError(
            "retrieval_or_file_integrity_failure",
            f"EEGBCI downloaded-file checksum failed after MNE retries: {exc}",
        ) from exc
    if len(returned_paths) != len(RUNS):
        raise SubjectEligibilityError(
            "incomplete_run_set", f"expected {len(RUNS)} EDF paths, received {len(returned_paths)}"
        )
    paths_by_run: dict[int, Path] = {}
    for item in returned_paths:
        path = Path(item).expanduser().resolve()
        baseline._ensure_outside_repository(path, "EEGBCI EDF")
        try:
            file_subject, run = _filename_subject_run(path)
        except ValueError as exc:
            raise SubjectEligibilityError("invalid_edf_filename", str(exc)) from exc
        if file_subject != subject:
            raise SubjectEligibilityError(
                "participant_id_mismatch",
                f"MNE returned participant {file_subject} for requested participant {subject}",
            )
        if run not in RUNS or run in paths_by_run:
            raise SubjectEligibilityError("unexpected_or_duplicate_run", f"unexpected or duplicate run {run}")
        if not path.is_file() or path.stat().st_size == 0:
            raise SubjectEligibilityError("missing_or_empty_edf", f"EDF is missing or empty: {path.name}")
        paths_by_run[run] = path
    if set(paths_by_run) != set(RUNS):
        raise SubjectEligibilityError(
            "incomplete_run_set", f"MNE returned runs {tuple(sorted(paths_by_run))}, expected {RUNS}"
        )

    montage = mne.channels.make_standard_montage("colin27_1005")
    epoch_blocks: list[np.ndarray] = []
    label_blocks: list[np.ndarray] = []
    run_blocks: list[np.ndarray] = []
    file_records: list[dict[str, Any]] = []
    subject_channel_names: list[str] | None = None
    subject_sampling_frequency: float | None = None
    for run in RUNS:
        path = paths_by_run[run]
        source_hash = _sha256_file(path)
        source_size = path.stat().st_size
        try:
            raw = mne.io.read_raw_edf(str(path), preload=True, verbose="ERROR")
        except (FileNotFoundError, EOFError) as exc:
            raise SubjectEligibilityError(
                "unreadable_edf", f"cannot read {path.name}: {type(exc).__name__}: {exc}"
            ) from exc
        except ValueError as exc:
            if not str(exc).startswith("Bad EDF file provided."):
                raise
            raise SubjectEligibilityError(
                "unreadable_edf", f"cannot read {path.name}: invalid EDF header: {exc}"
            ) from exc
        try:
            eegbci.standardize(raw)
            raw.set_montage(montage, on_missing="ignore", verbose="ERROR")
            raw.set_eeg_reference("average", projection=True, verbose="ERROR")
            picks = mne.pick_types(raw.info, meg=False, eeg=True, stim=False, eog=False, exclude="bads")
            if len(picks) == 0:
                raise SubjectEligibilityError("no_usable_eeg_channels", f"no usable EEG channels in run {run}")
            run_channel_names = [raw.ch_names[index] for index in picks]
            sampling_frequency = float(raw.info["sfreq"])
            if len(set(run_channel_names)) != len(run_channel_names):
                raise SubjectEligibilityError(
                    "duplicate_channel_names", f"run {run} has duplicate standardized EEG channel names"
                )
            if subject_channel_names is None:
                subject_channel_names = sorted(run_channel_names)
                subject_sampling_frequency = sampling_frequency
            elif set(run_channel_names) != set(subject_channel_names):
                raise SubjectEligibilityError(
                    "within_subject_channel_schema_mismatch",
                    f"run {run} channel names differ from other runs for participant {subject}",
                )
            elif not np.isclose(sampling_frequency, subject_sampling_frequency, rtol=0.0, atol=1e-9):
                raise SubjectEligibilityError(
                    "within_subject_sampling_frequency_mismatch",
                    f"run {run} sampling frequency differs for participant {subject}",
                )
            raw.filter(
                l_freq=baseline.FILTER_LOW_HZ,
                h_freq=baseline.FILTER_HIGH_HZ,
                picks=picks,
                fir_design="firwin",
                skip_by_annotation="edge",
                verbose="ERROR",
            )
            events, event_id = mne.events_from_annotations(
                raw, event_id=baseline.EVENT_ID, verbose="ERROR"
            )
            if not len(events):
                raise SubjectEligibilityError("no_task_events", f"no T1/T2 events in run {run}")
            epochs = mne.Epochs(
                raw,
                events,
                event_id=event_id,
                tmin=baseline.EPOCH_TMIN_SECONDS,
                tmax=baseline.EPOCH_TMAX_SECONDS,
                baseline=None,
                picks=picks,
                proj=True,
                preload=True,
                reject_by_annotation=True,
                verbose="ERROR",
            )
            labels = baseline.map_event_codes(epochs.events[:, -1], run=run, event_id=event_id)
            data = epochs.get_data()
            if data.ndim != 3 or data.shape[0] != labels.size or not np.isfinite(data).all():
                raise SubjectEligibilityError(
                    "invalid_epochs", f"invalid or non-finite epochs for participant {subject}, run {run}"
                )
            if set(labels.tolist()) != set(CLASS_LABELS):
                raise SubjectEligibilityError(
                    "missing_task_class", f"run {run} does not retain both T1/T2 classes"
                )
            data, canonical_names = canonicalize_channel_order(data, run_channel_names)
            if canonical_names != subject_channel_names:
                raise SubjectEligibilityError(
                    "within_subject_channel_order_mismatch",
                    f"run {run} cannot be aligned to participant {subject}'s channel schema",
                )
            after_hash = _sha256_file(path)
            if after_hash != source_hash:
                raise SubjectEligibilityError(
                    "source_edf_changed", f"source EDF changed while reading participant {subject}, run {run}"
                )
            epoch_blocks.append(data)
            label_blocks.append(labels)
            run_blocks.append(np.full(labels.size, run, dtype=np.int16))
            file_records.append(
                {
                    "subject": int(subject),
                    "run": int(run),
                    "filename": path.name,
                    "size_bytes": int(source_size),
                    "sha256": source_hash,
                    "epochs_retained": int(labels.size),
                    "class_support": {
                        label: int(np.count_nonzero(labels == label)) for label in CLASS_LABELS
                    },
                    "eeg_channels": canonical_names,
                    "sampling_frequency_hz": sampling_frequency,
                }
            )
            del epochs
        finally:
            raw.close()

    return (
        np.concatenate(epoch_blocks, axis=0),
        np.concatenate(label_blocks),
        np.concatenate(run_blocks),
        file_records,
    )


def _repository_provenance() -> dict[str, Any]:
    return {
        "commit": baseline._repository_provenance()["commit"],
        "branch": baseline._repository_provenance()["branch"],
        "working_tree_dirty": baseline._repository_provenance()["working_tree_dirty"],
        "loso_script_sha256": _sha256_file(SCRIPT_PATH),
        "baseline_helper_sha256": _sha256_file(Path(baseline.__file__).resolve()),
    }


def run_analysis(
    dataset_dir: str | Path = DEFAULT_DATA_DIR,
    *,
    subjects: Sequence[int] = SUBJECT_IDS,
    bootstrap_seed: int = BOOTSTRAP_SEED,
    bootstrap_resamples: int = BOOTSTRAP_RESAMPLES,
) -> dict[str, Any]:
    """Run fixed-pipeline LOSO across the requested EEGMMIDB participant IDs."""
    try:
        import mne
        import scipy
        import sklearn
        from mne.datasets import eegbci
        from mne.decoding import CSP
        from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
        from sklearn.pipeline import make_pipeline
    except ImportError as exc:
        raise RuntimeError("MNE-Python, SciPy, and scikit-learn are required; no synthetic fallback is used.") from exc

    requested = _integer_vector(subjects, "subjects")
    if len(np.unique(requested)) != requested.size:
        raise ValueError("subjects must not contain duplicate participant IDs.")
    if np.any(requested < 1) or np.any(requested > 109):
        raise ValueError("EEGBCI participant IDs must be in the documented range 1..109.")
    requested = np.sort(requested)
    cache = baseline._ensure_outside_repository(dataset_dir, "EEGBCI dataset cache")

    included_data: dict[int, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
    source_files: list[dict[str, Any]] = []
    exclusions: list[dict[str, Any]] = []
    reference_channel_names: list[str] | None = None
    reference_sampling_frequency: float | None = None
    for position, subject in enumerate(requested, start=1):
        try:
            X_sub, y_sub, runs_sub, files_sub = _load_subject_epochs(mne, eegbci, int(subject), cache)
            if set(y_sub.tolist()) != set(CLASS_LABELS) or set(runs_sub.tolist()) != set(RUNS):
                raise SubjectEligibilityError(
                    "incomplete_run_or_class_support", "participant lacks both classes or one or more required runs"
                )
            if not files_sub:
                raise SubjectEligibilityError("missing_file_provenance", "participant has no EDF provenance records")
            participant_channels = files_sub[0]["eeg_channels"]
            participant_sfreq = float(files_sub[0]["sampling_frequency_hz"])
            if any(record["eeg_channels"] != participant_channels for record in files_sub):
                raise SubjectEligibilityError(
                    "within_subject_channel_schema_mismatch", "channel schemas differ across this participant's runs"
                )
            if any(
                not np.isclose(record["sampling_frequency_hz"], participant_sfreq, rtol=0.0, atol=1e-9)
                for record in files_sub
            ):
                raise SubjectEligibilityError(
                    "within_subject_sampling_frequency_mismatch",
                    "sampling frequencies differ across this participant's runs",
                )
            if reference_channel_names is None:
                reference_channel_names = list(participant_channels)
                reference_sampling_frequency = participant_sfreq
            elif participant_channels != reference_channel_names:
                raise SubjectEligibilityError(
                    "between_subject_channel_schema_mismatch",
                    "standardized channel names differ from the first eligible participant",
                )
            elif not np.isclose(
                participant_sfreq, reference_sampling_frequency, rtol=0.0, atol=1e-9
            ):
                raise SubjectEligibilityError(
                    "between_subject_sampling_frequency_mismatch",
                    "sampling frequency differs from the first eligible participant",
                )
            included_data[int(subject)] = (X_sub, y_sub, runs_sub)
            source_files.extend(files_sub)
            print(
                f"eligible participant {int(subject):03d}: epochs={len(y_sub)} "
                f"({position}/{len(requested)})",
                flush=True,
            )
        except SubjectEligibilityError as exc:
            exclusions.append(
                {
                    "subject": int(subject),
                    "reason_code": exc.reason_code,
                    "exception_type": type(exc).__name__,
                    "reason": str(exc)[:1000],
                }
            )
            print(
                f"excluded participant {int(subject):03d} [{exc.reason_code}]: {str(exc)[:240]}",
                flush=True,
            )

    if len(included_data) < 2:
        raise RuntimeError(f"LOSO needs at least two eligible participants; found {len(included_data)}")

    eligible_ids = sorted(included_data)
    X = np.concatenate([included_data[subject][0] for subject in eligible_ids], axis=0)
    y = np.concatenate([included_data[subject][1] for subject in eligible_ids])
    run_ids = np.concatenate([included_data[subject][2] for subject in eligible_ids])
    epoch_subject_ids = np.concatenate(
        [np.full(included_data[subject][1].size, subject, dtype=np.int64) for subject in eligible_ids]
    )
    splits = leave_one_subject_out_splits(epoch_subject_ids, expected_subjects=eligible_ids)
    all_predictions: list[np.ndarray] = []
    all_truths: list[np.ndarray] = []
    participant_results: list[dict[str, Any]] = []
    folds: list[dict[str, Any]] = []

    for held_out, train_idx, test_idx in splits:
        if set(y[train_idx].tolist()) != set(CLASS_LABELS):
            raise ValueError(f"training participants for test participant {held_out} lack a class")
        model = make_pipeline(
            CSP(
                n_components=baseline.CSP_COMPONENTS,
                reg=None,
                log=True,
                norm_trace=False,
            ),
            LinearDiscriminantAnalysis(solver="svd"),
        )
        truth, predicted = fit_predict_loso_fold(
            model, X, y, epoch_subject_ids, held_out, train_idx, test_idx
        )
        metrics = baseline.calculate_metrics(truth, predicted)
        subject_runs = run_ids[test_idx]
        per_participant = {
            "subject": int(held_out),
            "test_epoch_count": int(test_idx.size),
            "test_run_counts": {str(run): int(np.count_nonzero(subject_runs == run)) for run in RUNS},
            **metrics,
        }
        participant_results.append(per_participant)
        folds.append(
            {
                "test_subject": int(held_out),
                "train_subject_ids": [subject for subject in eligible_ids if subject != held_out],
                "train_subject_count": len(eligible_ids) - 1,
                "train_epoch_count": int(train_idx.size),
                "test_epoch_count": int(test_idx.size),
                "train_subject_overlap_with_test": False,
                **metrics,
            }
        )
        all_truths.append(truth)
        all_predictions.append(predicted)
        print(
            f"LOSO test {held_out:03d}/{eligible_ids[-1]:03d}: "
            f"balanced_accuracy={metrics['balanced_accuracy']:.4f}, "
            f"accuracy={metrics['accuracy']:.4f}, n={test_idx.size}",
            flush=True,
        )

    aggregate = aggregate_participant_metrics(
        participant_results,
        np.concatenate(all_truths),
        np.concatenate(all_predictions),
        seed=bootstrap_seed,
        resamples=bootstrap_resamples,
    )
    source_files.sort(key=lambda record: (record["subject"], record["run"]))
    ordered_source_sha256 = hashlib.sha256(
        "\n".join(
            f"{record['subject']:03d}:{record['run']:02d}:{record['sha256']}" for record in source_files
        ).encode("utf-8")
    ).hexdigest()
    try:
        from importlib.metadata import version
        sklearn_version = version("scikit-learn")
    except Exception:
        sklearn_version = getattr(sklearn, "__version__", "unknown")

    return {
        "schema_version": 1,
        "task": {
            "name": "EEGBCI left-versus-right hand motor-imagery decoding",
            "runs": list(RUNS),
            "run_task": "Runs 4, 8, and 12: imagined unilateral left/right fist movement.",
            "event_mapping": {"T1": "left_hand", "T2": "right_hand"},
            "classes": list(CLASS_LABELS),
            "requested_subject_ids": [int(value) for value in requested],
            "included_subject_ids": eligible_ids,
            "excluded_subjects": exclusions,
            "inclusion_rule": INCLUSION_RULE,
            "selection": "all requested EEGMMIDB subjects; no outcome-based sampling or exclusion",
        },
        "source": {
            "dataset": "PhysioNet EEG Motor Movement/Imagery Database (EEGMMIDB), version 1.0.0",
            "dataset_url": DATASET_URL,
            "retrieval": "mne.datasets.eegbci.load_data(subjects=one_id, runs=[4, 8, 12]) per requested subject",
            "mne_api_url": "https://mne.tools/stable/generated/mne.datasets.eegbci.load_data.html",
            "files": source_files,
            "edf_file_count": len(source_files),
            "ordered_source_sha256": ordered_source_sha256,
            "canonical_channel_names": reference_channel_names,
            "sampling_frequency_hz": reference_sampling_frequency,
        },
        "execution": {
            "completed_at_utc": datetime.now(timezone.utc).isoformat(),
            "command": [sys.executable, *sys.argv],
            "repository": _repository_provenance(),
        },
        "dependencies": {
            "python": sys.version.split()[0],
            "mne": mne.__version__,
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "scikit_learn": sklearn_version,
        },
        "parameters": {
            "reference": "average reference projection (MNE)",
            "montage": "colin27_1005; unmatched channels ignored",
            "bandpass_hz": [baseline.FILTER_LOW_HZ, baseline.FILTER_HIGH_HZ],
            "filter_design": "FIR, firwin; EEG channels only; skip annotations marked edge",
            "epoch_seconds_relative_to_cue": [
                baseline.EPOCH_TMIN_SECONDS,
                baseline.EPOCH_TMAX_SECONDS,
            ],
            "baseline_correction": None,
            "epoch_rejection": "MNE reject_by_annotation=True; no amplitude-threshold rejection",
            "channel_alignment": (
                "standardized channel names sorted lexicographically; exact same channel list and sampling "
                "frequency required within and across included participants"
            ),
            "csp": {
                "n_components": baseline.CSP_COMPONENTS,
                "reg": None,
                "log": True,
                "norm_trace": False,
            },
            "classifier": {"name": "LinearDiscriminantAnalysis", "solver": "svd"},
            "cross_validation": (
                "leave-one-subject-out; all epochs and all three runs from a test participant are held out; "
                "CSP and LDA are fit only on epochs from other included participants"
            ),
            "hyperparameter_search": "none; fixed settings inherited from the existing single-subject baseline",
            "class_order_for_metrics": list(CLASS_LABELS),
            "participant_bootstrap": {
                "seed": int(bootstrap_seed),
                "resamples": int(bootstrap_resamples),
                "interval": "95% percentile CI over participants, not epochs",
            },
        },
        "validation": {
            "method": "leave-one-subject-out",
            "participant_results": participant_results,
            "folds": folds,
            "aggregate": aggregate,
            "included_participant_count": len(eligible_ids),
            "excluded_participant_count": len(exclusions),
            "total_epochs": int(y.size),
            "epochs_by_participant": {
                str(subject): int(included_data[subject][1].size) for subject in eligible_ids
            },
            "interpretation": (
                "Primary aggregate estimates are equal-participant means with participant-level bootstrap CIs. "
                "Pooled epoch metrics and summed confusion counts are descriptive and do not treat epochs as "
                "independent inferential units."
            ),
        },
        "limitations": LIMITATIONS,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="EEGBCI EDF cache directory outside the repository.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="New JSON metrics/provenance path outside the repository; existing files are never overwritten.",
    )
    parser.add_argument(
        "--subjects",
        nargs="+",
        type=int,
        default=list(SUBJECT_IDS),
        help="EEGBCI IDs to attempt (default: all documented IDs 1..109, in ascending order).",
    )
    parser.add_argument("--bootstrap-seed", type=int, default=BOOTSTRAP_SEED)
    parser.add_argument("--bootstrap-resamples", type=int, default=BOOTSTRAP_RESAMPLES)
    args = parser.parse_args()
    output = baseline._ensure_outside_repository(args.output, "metrics/provenance output")
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"Refusing to overwrite {output}; choose a new --output path.")
    baseline._ensure_outside_repository(args.dataset_dir, "EEGBCI dataset cache")

    started = time.monotonic()
    result = run_analysis(
        args.dataset_dir,
        subjects=args.subjects,
        bootstrap_seed=args.bootstrap_seed,
        bootstrap_resamples=args.bootstrap_resamples,
    )
    saved = baseline.write_results_exclusive(result, output)
    aggregate = result["validation"]["aggregate"]
    print(f"Saved metrics/provenance JSON: {saved}")
    print(
        f"Included participants={result['validation']['included_participant_count']}; "
        f"excluded={result['validation']['excluded_participant_count']}; "
        f"epochs={result['validation']['total_epochs']}; elapsed_seconds={time.monotonic() - started:.1f}"
    )
    print(
        f"Equal-participant balanced accuracy={aggregate['balanced_accuracy_equal_participant_mean']:.4f} "
        f"(95% participant bootstrap CI "
        f"{aggregate['balanced_accuracy_participant_bootstrap_95ci']['lower_percentile']:.4f}–"
        f"{aggregate['balanced_accuracy_participant_bootstrap_95ci']['upper_percentile']:.4f}); "
        f"accuracy={aggregate['accuracy_equal_participant_mean']:.4f} "
        f"(95% participant bootstrap CI "
        f"{aggregate['accuracy_participant_bootstrap_95ci']['lower_percentile']:.4f}–"
        f"{aggregate['accuracy_participant_bootstrap_95ci']['upper_percentile']:.4f})"
    )
    print(f"Aggregate summed confusion counts: {aggregate['confusion_matrix_sum_counts']}")
    if result["task"]["excluded_subjects"]:
        print(f"Excluded subjects/reasons: {json.dumps(result['task']['excluded_subjects'], ensure_ascii=False)}")
    print("Limitations: EEGMMIDB offline LOSO only; no inference about IIT Phi or consciousness.")


if __name__ == "__main__":
    main()
