"""Create an explicitly labeled offline demo from EEGBCI data.

The signal must have a provenance sidecar created by download_eeg_data.py.
The controller and its prediction are simulations; this is not a live BCI or
an IIT Phi calculation. Output is exclusive-created and never overwrites files.
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

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_INPUT = Path.home() / ".cache" / "diwt-v3.7-real-eeg" / "raw_eeg.npy"
DEFAULT_OUTPUT = SCRIPT_DIR / "session_recording.generated.json"


class MockDIWT:
    """Small simulated controller retained for the offline demo only."""

    def __init__(self) -> None:
        self.phi = 0.5
        self.valence = 0.0

    def update(self, phi: float) -> None:
        self.phi = 0.7 * self.phi + 0.3 * phi
        self.valence += 0.1 * (phi - 0.5)

    def act(self) -> str:
        return "BROADCAST" if self.phi > 0.5 else "REST"


def provenance_path_for(input_path: Path) -> Path:
    return input_path.with_suffix(".provenance.json")


def load_verified_eeg(input_path: str | Path) -> tuple[np.ndarray, dict[str, Any]]:
    """Load EEG only when the downloader's EEGBCI provenance is present."""
    source = Path(input_path).expanduser().resolve()
    metadata_path = provenance_path_for(source)
    if not source.is_file():
        raise FileNotFoundError(f"EEG input not found: {source}; no synthetic fallback is used.")
    if not metadata_path.is_file():
        raise ValueError(f"Missing provenance sidecar {metadata_path}; refusing to treat this array as EEG.")

    with metadata_path.open(encoding="utf-8") as stream:
        provenance = json.load(stream)
    if (
        provenance.get("schema_version") != 1
        or provenance.get("source_type") != "EEGBCI"
        or provenance.get("synthetic") is not False
    ):
        raise ValueError(f"Unsupported or synthetic EEG provenance in {metadata_path}.")

    data = np.load(source, allow_pickle=False)
    if data.ndim != 2 or not data.size or not np.issubdtype(data.dtype, np.number) or not np.isfinite(data).all():
        raise ValueError(f"Expected finite numeric channels-by-samples array, got shape {data.shape}.")
    array_metadata = provenance.get("array", {})
    expected_shape = array_metadata.get("shape")
    if expected_shape != list(data.shape):
        raise ValueError(f"EEG array shape {list(data.shape)} does not match provenance {expected_shape}.")
    if array_metadata.get("dtype") != str(data.dtype):
        raise ValueError(f"EEG array dtype {data.dtype} does not match provenance {array_metadata.get('dtype')}.")
    expected_digest = array_metadata.get("sha256")
    actual_digest = hashlib.sha256(np.ascontiguousarray(data).tobytes(order="C")).hexdigest()
    if not isinstance(expected_digest, str) or actual_digest != expected_digest:
        raise ValueError("EEG array SHA-256 does not match its provenance sidecar.")
    try:
        sampling_frequency = float(provenance["sampling_frequency_hz"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Provenance must contain a positive sampling_frequency_hz.") from exc
    if not np.isfinite(sampling_frequency) or sampling_frequency <= 0:
        raise ValueError("Provenance must contain a positive sampling_frequency_hz.")
    return data, provenance


def binary_symbol_count(chunk: np.ndarray) -> float:
    """Count binary symbols after per-channel median thresholding (not IIT Phi)."""
    counts = [np.unique(channel > np.median(channel)).size for channel in chunk]
    return float(np.mean(counts))


def create_session(
    eeg_data: np.ndarray,
    provenance: dict[str, Any],
    *,
    rng: np.random.Generator | None = None,
    seed: int | None = None,
) -> dict[str, Any]:
    rng = rng or np.random.default_rng(seed)
    try:
        sampling_frequency = float(provenance["sampling_frequency_hz"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Provenance must contain a positive sampling_frequency_hz.") from exc
    if not np.isfinite(sampling_frequency) or sampling_frequency <= 0:
        raise ValueError("Provenance must contain a positive sampling_frequency_hz.")
    chunk_size = max(1, round(sampling_frequency))
    controller = MockDIWT()
    frames = []

    for index, start in enumerate(range(0, eeg_data.shape[1] - chunk_size + 1, chunk_size)):
        if index >= 100:
            break
        chunk = eeg_data[:, start : start + chunk_size]
        eeg_count = binary_symbol_count(chunk)
        phi_pred = 0.5 + 0.4 * float(rng.random())
        if 30 <= index < 70:
            phi_pred -= 0.15 * np.sin((index - 30) / 40 * np.pi)
        controller.update(phi_pred)
        frames.append(
            {
                "cycle": index + 1,
                "eeg_binary_symbol_count": round(eeg_count, 3),
                "phi_pred_simulated": round(phi_pred, 3),
                "phi_diwt_simulated": round(controller.phi, 3),
                "action_simulated": controller.act(),
            }
        )

    if not frames:
        raise ValueError(f"EEG input has fewer than one second of samples ({eeg_data.shape[1]} samples).")

    return {
        "metadata": {
            "schema_version": 1,
            "record_type": "offline_demo_simulation",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "input_source_type": provenance["source_type"],
            "input_dataset": provenance.get("source_dataset"),
            "input_source_file": provenance.get("source_file"),
            "input_preprocessing": provenance.get("preprocessing"),
            "sampling_frequency_hz": sampling_frequency,
            "eeg_feature": {
                "field": "eeg_binary_symbol_count",
                "definition": "Mean number of distinct binary values per channel after median thresholding in a one-second chunk.",
                "is_iit_phi": False,
            },
            "simulated_components": {
                "phi_pred_simulated": "randomized demo value with an illustrative mid-session modulation",
                "phi_diwt_simulated": "output of MockDIWT, not a measured neural quantity",
                "action_simulated": "output of MockDIWT, not a real BCI command",
            },
            "random_seed": seed,
        },
        "frames": frames,
    }


def save_session(session: dict[str, Any], output_path: str | Path) -> Path:
    output = Path(output_path).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=output.parent,
            prefix=f".{output.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            json.dump(session, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        # Same-directory hard-link publication is atomic and does not replace
        # a destination created by another writer while serialization ran.
        os.link(temporary, output)
    finally:
        if temporary is not None:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="EEG .npy file with EEGBCI provenance sidecar.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="New JSON output path (never overwritten).")
    parser.add_argument("--seed", type=int, default=None, help="Optional seed for the simulated prediction component.")
    args = parser.parse_args()

    output = args.output.expanduser().resolve()
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite {output}; choose a new --output path.")
    eeg_data, provenance = load_verified_eeg(args.input)
    session = create_session(eeg_data, provenance, seed=args.seed)
    saved = save_session(session, output)
    print(f"Saved explicitly simulated demo: {saved} ({len(session['frames'])} cycles)")


if __name__ == "__main__":
    main()
