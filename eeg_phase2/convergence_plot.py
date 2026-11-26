"""Create a synthetic illustration; no EEG is loaded or analyzed."""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / "visualizations_v37" / "eeg_convergence.synthetic.png"


def generate_convergence_plot(output_path: str | Path = DEFAULT_OUTPUT, seed: int | None = None) -> Path:
    """Write an illustrative synthetic plot to a new path, never over an existing file."""
    rng = np.random.default_rng(seed)
    cycles = 200
    signal_proxy = np.cumsum(rng.normal(0, 0.05, cycles)) + 0.5
    signal_proxy = np.clip(signal_proxy, 0.2, 0.9)
    diwt_simulated = [0.3]
    alpha = 0.025
    for index in range(1, cycles):
        diwt_simulated.append(diwt_simulated[-1] + alpha * (signal_proxy[index] - diwt_simulated[-1]))
    error = np.abs(signal_proxy - np.asarray(diwt_simulated))

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
    ax1.plot(signal_proxy, label="Synthetic signal proxy (not EEG or IIT Phi)", alpha=0.8, linewidth=2, color="#E63946", linestyle="--")
    ax1.plot(diwt_simulated, label="Simulated DIWT value", linewidth=2.5, color="#2E86AB")
    ax1.set_title("Synthetic illustration — not EEG evidence")
    ax1.set_xlabel("Cycle")
    ax1.set_ylabel("Illustrative value")
    ax1.legend()
    ax1.grid(alpha=0.3)
    ax2.plot(error, linewidth=2, color="#06A77D")
    ax2.fill_between(range(cycles), 0, error, alpha=0.3, color="#06A77D")
    ax2.set_title("Synthetic difference between generated curves")
    ax2.set_xlabel("Cycle")
    ax2.set_ylabel("Absolute difference")
    ax2.grid(alpha=0.3)
    fig.tight_layout()

    output = Path(output_path).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with output.open("xb") as stream:
            fig.savefig(stream, format="png", dpi=200)
    finally:
        plt.close(fig)
    print(f"Synthetic illustration saved without overwriting: {output}")
    print(f"Final difference: {error[-1]:.4f}; mean difference: {np.mean(error):.4f}")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="New PNG path (never overwritten).")
    parser.add_argument("--seed", type=int, default=None, help="Optional seed for reproducible synthetic illustration.")
    args = parser.parse_args()
    generate_convergence_plot(args.output, args.seed)


if __name__ == "__main__":
    main()
