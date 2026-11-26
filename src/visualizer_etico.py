"""Plot the recorded DIWT v3.7 toy-simulation history without fabricating data.

The values named ``phi`` in the legacy log are arithmetic means of simulated
scalar states, not IIT Phi. This script reads only ``phi_history`` and writes a
new PNG; it does not recreate missing values or overwrite existing figures.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = REPO_ROOT / "data" / "triade_log.json"
DEFAULT_OUTPUT = REPO_ROOT / "visualizations_v37" / "01_state_trajectory.generated.png"


def load_results(input_path: str | Path = DEFAULT_INPUT) -> dict[str, Any]:
    """Load a recorded history, rejecting missing or malformed data."""
    path = Path(input_path).expanduser().resolve()
    with path.open(encoding="utf-8") as stream:
        results = json.load(stream)
    _history_from_results(results)
    return results


def _history_from_results(results: Any) -> list[float]:
    if not isinstance(results, dict):
        raise ValueError("Simulation log must be a JSON object containing phi_history.")
    history = results.get("phi_history")
    if not isinstance(history, list) or not history:
        raise ValueError("Simulation log must contain a non-empty recorded phi_history; no fallback is generated.")

    values: list[float] = []
    for index, value in enumerate(history):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"phi_history[{index}] must be a finite number.")
        values.append(float(value))

    cycles_total = results.get("cycles_total")
    if cycles_total is not None and cycles_total != len(values):
        raise ValueError("cycles_total does not match the recorded phi_history length.")
    return values


def plot_state_trajectory(
    results: dict[str, Any], output_path: str | Path = DEFAULT_OUTPUT
) -> Path:
    """Plot only the recorded scalar history and exclusively create a new PNG."""
    history = _history_from_results(results)
    output = Path(output_path).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(range(1, len(history) + 1), history, linewidth=2, color="#2E86AB")
    ax.set_title("Recorded toy simulation — not IIT Φ")
    ax.set_xlabel("Recorded update index (1-based)")
    ax.set_ylabel("Mean of simulated scalar states")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    try:
        with output.open("xb") as stream:
            fig.savefig(stream, format="png", dpi=200)
    finally:
        plt.close(fig)
    print(f"Recorded simulation plot saved without overwriting: {output}")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Recorded simulation JSON with phi_history.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="New PNG path (never overwritten).")
    args = parser.parse_args()
    results = load_results(args.input)
    plot_state_trajectory(results, args.output)


if __name__ == "__main__":
    main()
