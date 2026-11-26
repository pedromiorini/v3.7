"""Replay a legacy recording or an explicitly labeled offline demo."""
from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_SESSION = SCRIPT_DIR / "session_recording.json"
DEFAULT_PLOT = SCRIPT_DIR / "closed_loop_simulation_results.preview.png"


def load_session(path: str | Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    with Path(path).expanduser().resolve().open(encoding="utf-8") as stream:
        payload = json.load(stream)
    if isinstance(payload, list):
        # Keep the versioned artifact readable without asserting undocumented origin.
        return {"record_type": "legacy_unverified", "warning": "Legacy list format; provenance is not recorded."}, payload
    if isinstance(payload, dict) and isinstance(payload.get("frames"), list):
        return payload.get("metadata", {}), payload["frames"]
    raise ValueError("Unrecognized session JSON format.")


def _finite_number(value: Any, field: str, frame_number: int) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"Invalid {field} in frame {frame_number}: expected a finite number.")
    try:
        number = float(value)
    except OverflowError as exc:
        raise ValueError(f"Invalid {field} in frame {frame_number}: expected a finite number.") from exc
    if not math.isfinite(number):
        raise ValueError(f"Invalid {field} in frame {frame_number}: expected a finite number.")
    return number


def _metric(frame: dict[str, Any], new_key: str, legacy_key: str, frame_number: int) -> float:
    key = new_key if new_key in frame else legacy_key
    return _finite_number(frame.get(new_key, frame.get(legacy_key)), key, frame_number)


def _validated_plot_data(
    metadata: dict[str, Any], frames: list[dict[str, Any]]
) -> tuple[list[int], list[float], list[float]]:
    if not isinstance(metadata, dict):
        raise ValueError("Invalid session metadata: expected an object.")
    if not isinstance(frames, list):
        raise ValueError("Invalid session frames: expected a list.")

    new_schema = metadata.get("record_type") == "offline_demo_simulation"
    eeg_key = "eeg_binary_symbol_count" if new_schema else "phi_eeg"
    cycles: list[int] = []
    eeg_values: list[float] = []
    diwt_values: list[float] = []
    for index, frame in enumerate(frames):
        frame_number = index + 1
        if not isinstance(frame, dict):
            raise ValueError(f"Invalid frame {frame_number}: expected an object.")
        cycle = _finite_number(frame.get("cycle", frame_number), "cycle", frame_number)
        cycles.append(int(cycle))
        eeg_values.append(_metric(frame, eeg_key, "phi_eeg", frame_number))
        _finite_number(
            frame.get("phi_pred_simulated", frame.get("phi_pred")),
            "prediction metric",
            frame_number,
        )
        diwt_values.append(_metric(frame, "phi_diwt_simulated", "phi_diwt", frame_number))
    return cycles, eeg_values, diwt_values


def generate_plot(metadata: dict[str, Any], frames: list[dict[str, Any]], plot_path: str | Path) -> Path:
    cycles, eeg_values, diwt_values = _validated_plot_data(metadata, frames)
    output = Path(plot_path).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    new_schema = metadata.get("record_type") == "offline_demo_simulation"
    eeg_label = "EEG binary-symbol proxy (not IIT Phi)" if new_schema else "Legacy phi_eeg field (unverified)"

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(cycles, eeg_values, label=eeg_label, linestyle="--")
    ax.plot(cycles, diwt_values, label="DIWT demo value (not neural measurement)", linewidth=2)
    ax.set_title("Offline DIWT demo replay")
    ax.set_xlabel("Cycle")
    ax.set_ylabel("Value (legacy scale; not IIT Phi)")
    ax.legend()
    ax.grid(alpha=0.25)
    fig.tight_layout()
    try:
        with output.open("xb") as stream:
            fig.savefig(stream, format="png", dpi=200)
    finally:
        plt.close(fig)
    return output


def replay(session_path: Path, plot_path: Path | None, show_delay: bool) -> None:
    metadata, frames = load_session(session_path)
    _validated_plot_data(metadata, frames)
    print(f"--- DIWT offline replay: {metadata.get('record_type', 'unknown format')} ---")
    if metadata.get("warning"):
        print(f"Warning: {metadata['warning']}")
    if metadata.get("record_type") == "offline_demo_simulation":
        print("EEG feature is a thresholded symbol count; controller/prediction values are simulated.")

    for frame in frames:
        print(
            f"Cycle {frame.get('cycle', '?')}: "
            f"EEG feature={frame.get('eeg_binary_symbol_count', frame.get('phi_eeg', '—'))}; "
            f"predicted={frame.get('phi_pred_simulated', frame.get('phi_pred', '—'))}; "
            f"DIWT={frame.get('phi_diwt_simulated', frame.get('phi_diwt', '—'))}; "
            f"action={frame.get('action_simulated', frame.get('action', '—'))}"
        )
        if show_delay:
            time.sleep(0.05)

    if plot_path is not None:
        saved = generate_plot(metadata, frames, plot_path)
        print(f"Plot saved without overwriting existing files: {saved}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", type=Path, default=DEFAULT_SESSION, help="Session JSON (default: archived legacy file).")
    parser.add_argument("--plot-output", type=Path, default=DEFAULT_PLOT, help="New plot path; an existing file is never overwritten.")
    parser.add_argument("--no-plot", action="store_true", help="Replay without creating a plot.")
    parser.add_argument("--no-delay", action="store_true", help="Do not pause between frames.")
    args = parser.parse_args()
    replay(args.session, None if args.no_plot else args.plot_output, show_delay=not args.no_delay)


if __name__ == "__main__":
    main()
