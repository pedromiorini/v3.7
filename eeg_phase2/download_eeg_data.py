"""Download EEGBCI with MNE and save the returned data with provenance.

This script may download EEGBCI from PhysioNet when the dataset is not cached.
It never substitutes random data for EEG and never overwrites existing outputs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
USER_CACHE_DIR = Path.home() / ".cache" / "diwt-v3.7-real-eeg"
DEFAULT_DATA_DIR = USER_CACHE_DIR / "eegbci"
DEFAULT_OUTPUT = USER_CACHE_DIR / "raw_eeg.npy"


def _require_path_outside_repository(path: str | Path, description: str) -> Path:
    """Resolve a path and refuse EEG storage anywhere inside this repository."""
    resolved = Path(path).expanduser().resolve()
    try:
        resolved.relative_to(REPO_ROOT)
    except ValueError:
        return resolved
    raise ValueError(
        f"{description} must be outside the repository to keep EEG out of Git: {resolved}"
    )


def provenance_path_for(output_path: Path) -> Path:
    return output_path.with_suffix(".provenance.json")


def _load_mne_components() -> tuple[Any, Any]:
    try:
        import mne
        from mne.datasets import eegbci
    except ImportError as exc:
        raise RuntimeError(
            "MNE-Python is required to download EEGBCI. No synthetic EEG is generated. "
            "Install MNE or provide an existing EEGBCI dataset."
        ) from exc
    return mne, eegbci


def _write_pair_exclusive(output: Path, metadata_path: Path, data: np.ndarray, metadata: dict[str, Any]) -> None:
    """Stage both files, then create both final names without replacing anything."""
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() or metadata_path.exists():
        raise FileExistsError(f"Refusing to overwrite {output} or {metadata_path}.")

    temporary: list[Path] = []
    linked: list[tuple[Path, Path]] = []
    try:
        with tempfile.NamedTemporaryFile("wb", dir=output.parent, prefix=f".{output.name}.", suffix=".tmp", delete=False) as stream:
            data_temp = Path(stream.name)
            temporary.append(data_temp)
            np.save(stream, data, allow_pickle=False)
            stream.flush()
            os.fsync(stream.fileno())
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=output.parent, prefix=f".{metadata_path.name}.", suffix=".tmp", delete=False) as stream:
            metadata_temp = Path(stream.name)
            temporary.append(metadata_temp)
            json.dump(metadata, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())

        # Hard links are exclusive and atomic on the same filesystem. If either
        # creation fails, remove only targets that this attempt linked itself.
        for staged, target in ((data_temp, output), (metadata_temp, metadata_path)):
            os.link(staged, target)
            linked.append((staged, target))
    except BaseException:
        for staged, target in reversed(linked):
            try:
                if os.path.samefile(staged, target):
                    target.unlink()
            except FileNotFoundError:
                pass
        raise
    finally:
        for path in temporary:
            try:
                path.unlink()
            except FileNotFoundError:
                pass


def download_and_preprocess(
    output_path: str | Path = DEFAULT_OUTPUT,
    dataset_dir: str | Path | None = None,
    *,
    mne_api: Any | None = None,
    eegbci_api: Any | None = None,
) -> tuple[Path, Path]:
    """Fetch EEGBCI run 1, preprocess it, and save data plus provenance.

    ``eegbci.load_data`` can download files when they are not cached. Tests may
    inject API-compatible fakes; this function itself does not create mock EEG.
    """
    output = _require_path_outside_repository(output_path, "EEG output")
    provenance_file = provenance_path_for(output)
    requested_dataset = DEFAULT_DATA_DIR if dataset_dir is None else dataset_dir
    dataset = _require_path_outside_repository(requested_dataset, "EEGBCI dataset cache")

    if output.exists() or provenance_file.exists():
        raise FileExistsError(
            f"Refusing to overwrite {output} or {provenance_file}; choose a new --output path."
        )

    if mne_api is None or eegbci_api is None:
        mne_api, eegbci_api = _load_mne_components()

    dataset.mkdir(parents=True, exist_ok=True)
    print("Fetching EEGBCI subject 1, run 1 via MNE (may download from PhysioNet)...")
    local_paths = eegbci_api.load_data(subjects=1, runs=[1], path=str(dataset))
    if not local_paths:
        raise RuntimeError("MNE returned no local EEGBCI file paths.")

    # MNE's API returns the local file paths; do not reconstruct a machine-specific path.
    source_file = Path(local_paths[0]).expanduser().resolve()
    print(f"Loading and filtering {source_file.name}...")
    raw = mne_api.io.read_raw_edf(str(source_file), preload=True)
    raw.filter(l_freq=1.0, h_freq=45.0)
    data = np.asarray(raw.get_data())
    if data.ndim != 2 or not data.size or not np.isfinite(data).all():
        raise ValueError(f"Expected finite channels-by-samples EEG data, got shape {data.shape}.")

    contiguous_data = np.ascontiguousarray(data)
    provenance = {
        "schema_version": 1,
        "source_type": "EEGBCI",
        "source_dataset": "EEGBCI (PhysioNet) via mne.datasets.eegbci.load_data",
        "source_file": source_file.name,
        "subject": 1,
        "runs": [1],
        "synthetic": False,
        "preprocessing": {"filter_hz": [1.0, 45.0]},
        "array": {
            "shape": list(data.shape),
            "dtype": str(data.dtype),
            "unit": "V",
            "sha256": hashlib.sha256(contiguous_data.tobytes(order="C")).hexdigest(),
        },
        "sampling_frequency_hz": float(raw.info["sfreq"]),
        "channel_names": list(raw.ch_names),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    _write_pair_exclusive(output, provenance_file, data, provenance)

    print(f"Saved EEG data: {output} {data.shape}")
    print(f"Saved provenance: {provenance_file}")
    return output, provenance_file


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="New .npy output path outside this repository (never overwritten).",
    )
    parser.add_argument(
        "--dataset-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="MNE EEGBCI cache/download directory outside this repository.",
    )
    args = parser.parse_args()
    download_and_preprocess(args.output, args.dataset_dir)


if __name__ == "__main__":
    main()
