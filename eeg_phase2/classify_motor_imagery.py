"""Decode left/right hand motor imagery from public PhysioNet EEGBCI data.

This is an offline, single-subject research example. It does not estimate IIT Phi,
consciousness, ethical efficacy, population generalization, or online BCI performance.
Raw EEG is cached outside this repository; only metrics/provenance JSON is written.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[1]
DEFAULT_DATA_DIR = Path.home() / ".cache" / "diwt-v3.7-real-eeg" / "eegbci"
DEFAULT_OUTPUT = Path.home() / ".cache" / "diwt-v3.7-real-eeg" / "subject-01-runs-04-08-12.json"
SUBJECT = 1
RUNS = (4, 8, 12)
EVENT_ID = {"T1": 1, "T2": 2}
CLASS_LABELS = ("left_hand", "right_hand")

# Fixed, documented settings based on the official MNE CSP tutorial.
FILTER_LOW_HZ = 7.0
FILTER_HIGH_HZ = 30.0
EPOCH_TMIN_SECONDS = 1.0
EPOCH_TMAX_SECONDS = 2.0
CSP_COMPONENTS = 4

DATASET_URL = "https://physionet.org/content/eegmmidb/1.0.0/"
MNE_TUTORIAL_URL = "https://mne.tools/stable/auto_examples/decoding/decoding_csp_eeg.html"
MNE_LOAD_DATA_URL = "https://mne.tools/stable/generated/mne.datasets.eegbci.load_data.html"
LIMITATIONS = [
    "Um único sujeito (sujeito 1) e três runs do EEGMMIDB público não demonstram generalização populacional.",
    "Decodificação offline de imagética motora não demonstra desempenho de BCI online.",
    "As métricas não medem IIT Phi (Φ), consciência ou eficácia ética.",
]


def map_event_codes(
    event_codes: Sequence[int] | np.ndarray,
    *,
    run: int,
    event_id: Mapping[str, int],
) -> np.ndarray:
    """Map MNE event integers to hand labels using the run-specific task context.

    EEGMMIDB runs 4, 8, and 12 are unilateral hand motor imagery. In those runs,
    PhysioNet documents T1 as left-fist imagery and T2 as right-fist imagery.
    """
    if isinstance(run, bool) or run not in RUNS:
        raise ValueError(f"run must be one of the motor-imagery runs {RUNS}; got {run!r}.")
    if not isinstance(event_id, Mapping) or not all(name in event_id for name in ("T1", "T2")):
        raise ValueError("event_id must map both T1 and T2 to MNE event integers.")
    t1_code, t2_code = event_id["T1"], event_id["T2"]
    if (
        isinstance(t1_code, bool)
        or isinstance(t2_code, bool)
        or not isinstance(t1_code, (int, np.integer))
        or not isinstance(t2_code, (int, np.integer))
        or t1_code == t2_code
    ):
        raise ValueError("T1 and T2 must have distinct integer event codes.")

    codes = np.asarray(event_codes)
    if codes.ndim != 1 or not np.issubdtype(codes.dtype, np.integer):
        raise ValueError("event_codes must be a one-dimensional sequence of integer MNE codes.")
    code_to_label = {int(t1_code): CLASS_LABELS[0], int(t2_code): CLASS_LABELS[1]}
    unknown = sorted(set(int(code) for code in codes) - set(code_to_label))
    if unknown:
        raise ValueError(f"unmapped event code(s) for run {run}: {unknown}.")
    return np.asarray([code_to_label[int(code)] for code in codes], dtype=str)


def leave_one_run_out_splits(
    run_ids: Sequence[int] | np.ndarray,
    *,
    runs: Sequence[int] = RUNS,
) -> list[tuple[int, np.ndarray, np.ndarray]]:
    """Return whole-run holdouts as (held-out run, train indices, test indices)."""
    run_values = np.asarray(run_ids)
    if run_values.ndim != 1 or run_values.size == 0 or not np.issubdtype(run_values.dtype, np.integer):
        raise ValueError("run_ids must be a non-empty one-dimensional sequence of integers.")
    expected = tuple(runs)
    if len(expected) < 2 or len(set(expected)) != len(expected):
        raise ValueError("runs must contain at least two distinct run numbers.")
    present = set(int(value) for value in run_values)
    if present != set(expected):
        raise ValueError(f"run_ids must contain each expected run {expected}; found {tuple(sorted(present))}.")

    splits: list[tuple[int, np.ndarray, np.ndarray]] = []
    for held_out in expected:
        test_idx = np.flatnonzero(run_values == held_out)
        train_idx = np.flatnonzero(run_values != held_out)
        if not test_idx.size or not train_idx.size:
            raise ValueError(f"run {held_out} has no test or training samples.")
        if set(int(value) for value in run_values[train_idx]) & set(int(value) for value in run_values[test_idx]):
            raise RuntimeError("run-level leakage detected in leave-one-run-out split.")
        splits.append((int(held_out), train_idx, test_idx))
    return splits


def calculate_metrics(y_true: Sequence[str] | np.ndarray, y_pred: Sequence[str] | np.ndarray) -> dict[str, Any]:
    """Calculate binary accuracy, macro recall (balanced accuracy), and confusion counts."""
    actual = np.asarray(y_true, dtype=str)
    predicted = np.asarray(y_pred, dtype=str)
    if actual.ndim != 1 or predicted.ndim != 1 or actual.size == 0 or actual.size != predicted.size:
        raise ValueError("y_true and y_pred must be non-empty one-dimensional arrays of equal length.")
    supported = set(CLASS_LABELS)
    if not set(actual).issubset(supported) or not set(predicted).issubset(supported):
        raise ValueError(f"labels must be from {CLASS_LABELS}.")
    support = {label: int(np.count_nonzero(actual == label)) for label in CLASS_LABELS}
    if any(count == 0 for count in support.values()):
        raise ValueError("both classes must occur in y_true to calculate balanced accuracy.")

    matrix = [
        [int(np.count_nonzero((actual == true_label) & (predicted == predicted_label))) for predicted_label in CLASS_LABELS]
        for true_label in CLASS_LABELS
    ]
    recalls = [matrix[index][index] / support[label] for index, label in enumerate(CLASS_LABELS)]
    correct = sum(matrix[index][index] for index in range(len(CLASS_LABELS)))
    total = int(actual.size)
    return {
        "labels": list(CLASS_LABELS),
        "support": support,
        "accuracy": correct / total,
        "balanced_accuracy": float(np.mean(recalls)),
        "confusion_matrix": matrix,
    }


def write_results_exclusive(result: Mapping[str, Any], output_path: str | Path) -> Path:
    """Atomically publish JSON under a new name, refusing to overwrite existing files."""
    output = Path(output_path).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=output.parent, prefix=f".{output.name}.", suffix=".tmp", delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write(serialized)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, output)
        except FileExistsError as exc:
            raise FileExistsError(f"Refusing to overwrite {output}; choose a new --output path.") from exc
    finally:
        if temporary is not None:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
    return output


def _ensure_outside_repository(path: str | Path, description: str) -> Path:
    resolved = Path(path).expanduser().resolve()
    try:
        resolved.relative_to(REPO_ROOT)
    except ValueError:
        return resolved
    raise ValueError(f"{description} must be outside the repository to keep raw EEG out of Git: {resolved}")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _run_from_filename(path: Path) -> int:
    match = re.search(r"R(\d+)\.edf$", path.name, flags=re.IGNORECASE)
    if match is None:
        raise ValueError(f"Cannot identify an EEGBCI run from returned filename {path.name!r}.")
    return int(match.group(1))


def _repository_provenance() -> dict[str, Any]:
    def git(*args: str) -> str | None:
        completed = subprocess.run(
            ["git", "-C", str(REPO_ROOT), *args], capture_output=True, text=True, check=False
        )
        return completed.stdout.strip() if completed.returncode == 0 else None

    return {
        "commit": git("rev-parse", "HEAD"),
        "branch": git("branch", "--show-current"),
        "working_tree_dirty": bool(git("status", "--porcelain")),
        "script_sha256": _sha256_file(SCRIPT_PATH),
    }


def _load_run_epochs(mne: Any, eegbci: Any, dataset_dir: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[dict[str, Any]]]:
    dataset_dir = _ensure_outside_repository(dataset_dir, "EEGBCI dataset cache")
    returned_paths = eegbci.load_data(
        subjects=SUBJECT,
        runs=list(RUNS),
        path=str(dataset_dir),
        update_path=False,
        verbose=False,
    )
    if len(returned_paths) != len(RUNS):
        raise RuntimeError(f"Expected {len(RUNS)} EEGBCI EDF paths, received {len(returned_paths)}.")
    paths_by_run: dict[int, Path] = {}
    for returned_path in returned_paths:
        path = Path(returned_path).expanduser().resolve()
        run = _run_from_filename(path)
        if run not in RUNS or run in paths_by_run:
            raise RuntimeError(f"Unexpected or duplicate EEGBCI run {run} at {path}.")
        paths_by_run[run] = path
    if set(paths_by_run) != set(RUNS):
        raise RuntimeError(f"MNE returned runs {tuple(sorted(paths_by_run))}, expected {RUNS}.")

    all_epochs: list[np.ndarray] = []
    all_labels: list[np.ndarray] = []
    all_run_ids: list[np.ndarray] = []
    source_files: list[dict[str, Any]] = []
    montage = mne.channels.make_standard_montage("colin27_1005")

    for run in RUNS:
        source_path = paths_by_run[run]
        raw = mne.io.read_raw_edf(str(source_path), preload=True, verbose="ERROR")
        eegbci.standardize(raw)
        raw.set_montage(montage, on_missing="ignore", verbose="ERROR")
        raw.set_eeg_reference("average", projection=True, verbose="ERROR")
        picks = mne.pick_types(
            raw.info, meg=False, eeg=True, stim=False, eog=False, exclude="bads"
        )
        if len(picks) == 0:
            raise RuntimeError(f"No usable EEG channels found in run {run}.")
        raw.filter(
            l_freq=FILTER_LOW_HZ,
            h_freq=FILTER_HIGH_HZ,
            picks=picks,
            fir_design="firwin",
            skip_by_annotation="edge",
            verbose="ERROR",
        )
        events, event_id = mne.events_from_annotations(raw, event_id=EVENT_ID, verbose="ERROR")
        if not len(events):
            raise RuntimeError(f"No T1/T2 events found in run {run}.")
        epochs = mne.Epochs(
            raw,
            events,
            event_id=event_id,
            tmin=EPOCH_TMIN_SECONDS,
            tmax=EPOCH_TMAX_SECONDS,
            baseline=None,
            picks=picks,
            proj=True,
            preload=True,
            reject_by_annotation=True,
            verbose="ERROR",
        )
        labels = map_event_codes(epochs.events[:, -1], run=run, event_id=event_id)
        data = epochs.get_data()
        if data.ndim != 3 or data.shape[0] != labels.size or not np.isfinite(data).all():
            raise ValueError(f"Invalid or non-finite epochs in run {run}: shape={data.shape}.")
        if set(labels.tolist()) != set(CLASS_LABELS):
            raise ValueError(f"Run {run} must contain both hand classes after epoch rejection.")

        all_epochs.append(data)
        all_labels.append(labels)
        all_run_ids.append(np.full(labels.size, run, dtype=np.int64))
        source_files.append(
            {
                "run": run,
                "filename": source_path.name,
                "sha256": _sha256_file(source_path),
                "epochs_retained": int(labels.size),
                "class_support": {label: int(np.count_nonzero(labels == label)) for label in CLASS_LABELS},
                "eeg_channels": [raw.ch_names[index] for index in picks],
                "sampling_frequency_hz": float(raw.info["sfreq"]),
            }
        )
        del raw, epochs

    return (
        np.concatenate(all_epochs, axis=0),
        np.concatenate(all_labels),
        np.concatenate(all_run_ids),
        source_files,
    )


def run_analysis(dataset_dir: str | Path = DEFAULT_DATA_DIR) -> dict[str, Any]:
    """Download/load real EEGBCI runs and evaluate grouped CSP+LDA decoding."""
    try:
        import mne
        import scipy
        import sklearn
        from mne.datasets import eegbci
        from mne.decoding import CSP
        from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
        from sklearn.pipeline import make_pipeline
    except ImportError as exc:
        raise RuntimeError(
            "MNE-Python and scikit-learn are required. Install them in an isolated environment; "
            "the script does not generate synthetic EEG as a fallback."
        ) from exc

    X, y, run_ids, source_files = _load_run_epochs(mne, eegbci, Path(dataset_dir))
    predictions: list[np.ndarray] = []
    truths: list[np.ndarray] = []
    per_run: list[dict[str, Any]] = []

    for held_out_run, train_idx, test_idx in leave_one_run_out_splits(run_ids):
        if set(run_ids[train_idx]) & set(run_ids[test_idx]):
            raise RuntimeError(f"Run leakage detected for held-out run {held_out_run}.")
        if set(y[train_idx].tolist()) != set(CLASS_LABELS):
            raise ValueError(f"Training data for held-out run {held_out_run} lacks a class.")
        model = make_pipeline(
            CSP(n_components=CSP_COMPONENTS, reg=None, log=True, norm_trace=False),
            LinearDiscriminantAnalysis(solver="svd"),
        )
        model.fit(X[train_idx], y[train_idx])
        y_pred = model.predict(X[test_idx])
        run_metrics = calculate_metrics(y[test_idx], y_pred)
        training_runs = sorted(int(run) for run in set(run_ids[train_idx]))
        per_run.append(
            {
                "test_run": held_out_run,
                "training_runs": training_runs,
                "train_epoch_count": int(train_idx.size),
                "test_epoch_count": int(test_idx.size),
                "train_run_ids": training_runs,
                "test_run_ids": [held_out_run],
                **run_metrics,
            }
        )
        truths.append(y[test_idx])
        predictions.append(np.asarray(y_pred, dtype=str))

    aggregate = calculate_metrics(np.concatenate(truths), np.concatenate(predictions))
    source_files.sort(key=lambda item: item["run"])
    source_hash = hashlib.sha256(
        "\n".join(f"{item['run']}:{item['sha256']}" for item in source_files).encode("utf-8")
    ).hexdigest()
    try:
        from importlib.metadata import version

        sklearn_version = version("scikit-learn")
    except Exception:
        sklearn_version = getattr(sklearn, "__version__", "unknown")

    return {
        "schema_version": 1,
        "task": {
            "name": "EEGBCI unilateral hand motor-imagery decoding",
            "subject": SUBJECT,
            "runs": list(RUNS),
            "run_task": "Runs 4, 8, and 12: imagined left-versus-right fist movement.",
            "event_mapping": {"T1": "left_hand", "T2": "right_hand"},
            "event_mapping_context": "For these unilateral hand-imagery runs only; T1/T2 meanings differ in other EEGMMIDB task runs.",
            "classes": list(CLASS_LABELS),
        },
        "source": {
            "dataset": "PhysioNet EEG Motor Movement/Imagery Database (EEGMMIDB), version 1.0.0",
            "dataset_url": DATASET_URL,
            "retrieval": "mne.datasets.eegbci.load_data(subjects=1, runs=[4, 8, 12])",
            "mne_api_url": MNE_LOAD_DATA_URL,
            "files": source_files,
            "ordered_source_sha256": source_hash,
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
            "bandpass_hz": [FILTER_LOW_HZ, FILTER_HIGH_HZ],
            "filter_design": "FIR, firwin; EEG channels only; skip annotations marked edge",
            "epoch_seconds_relative_to_cue": [EPOCH_TMIN_SECONDS, EPOCH_TMAX_SECONDS],
            "baseline_correction": None,
            "epoch_rejection": "MNE reject_by_annotation=True; no amplitude-threshold rejection",
            "csp": {"n_components": CSP_COMPONENTS, "reg": None, "log": True, "norm_trace": False},
            "classifier": {"name": "LinearDiscriminantAnalysis", "solver": "svd"},
            "cross_validation": "leave-one-run-out; each full run held out; CSP and LDA fitted only on the other runs",
            "class_order_for_metrics": list(CLASS_LABELS),
        },
        "tutorial_reference": MNE_TUTORIAL_URL,
        "validation": {
            "method": "leave-one-run-out",
            "folds": per_run,
            "aggregate": aggregate,
            "total_epochs": int(y.size),
            "interpretation": "Aggregate metrics pool the three held-out runs; balanced accuracy is macro recall from the pooled confusion matrix, not the mean of fold scores.",
        },
        "limitations": LIMITATIONS,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="MNE EEGBCI download/cache directory; must be outside this repository.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="New metrics JSON path (default is outside the repository; never overwritten).",
    )
    args = parser.parse_args()

    output = args.output.expanduser().resolve()
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"Refusing to overwrite {output}; choose a new --output path.")
    _ensure_outside_repository(args.dataset_dir, "EEGBCI dataset cache")
    result = run_analysis(args.dataset_dir)
    saved = write_results_exclusive(result, output)

    aggregate = result["validation"]["aggregate"]
    print(f"Saved metrics/provenance JSON: {saved}")
    print(f"Subject {SUBJECT}; runs {','.join(map(str, RUNS))}; epochs {result['validation']['total_epochs']}")
    for fold in result["validation"]["folds"]:
        print(
            f"Held-out run {fold['test_run']}: balanced_accuracy={fold['balanced_accuracy']:.4f}, "
            f"accuracy={fold['accuracy']:.4f}, n={fold['test_epoch_count']}, "
            f"confusion_matrix={fold['confusion_matrix']}"
        )
    print(
        f"Aggregate pooled: balanced_accuracy={aggregate['balanced_accuracy']:.4f}, "
        f"accuracy={aggregate['accuracy']:.4f}, confusion_matrix={aggregate['confusion_matrix']}"
    )
    print("Limitations: single public subject, offline decoding only; no inference about IIT Phi or consciousness.")


if __name__ == "__main__":
    main()
