"""Deterministic toy simulation of three scalar states and fixed update rules.

The variable named ``phi`` is not an IIT measure; the global value is the
arithmetic mean of the three simulated agent values. New runs are saved to a
separate, exclusively-created JSON file by default.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / "data" / "triade_log.generated.json"


class DIWTAgent:
    """One simulated scalar state with a threshold-based increment rule."""

    def __init__(self, name: str, phi_initial: float = 0.8) -> None:
        self.name = name
        self.phi = phi_initial
        self.valence = 0.5
        self.ethical_threshold = 0.3

    def update_state(self, stress_factor: float = 0.0) -> bool:
        """Apply the programmed decrement and threshold-based increment."""
        self.phi *= 1 - stress_factor
        if self.phi < self.ethical_threshold:
            self.phi += 0.05
            return True
        return False

    def get_state(self) -> dict[str, float | str]:
        return {"name": self.name, "phi": self.phi, "valence": self.valence}


class TriadeCognitiva:
    """Three simulated scalar states; not a model of measured consciousness."""

    def __init__(self) -> None:
        self.agents = [
            DIWTAgent("Agent_A", 0.85),
            DIWTAgent("Agent_B", 0.82),
            DIWTAgent("Agent_C", 0.88),
        ]
        self.phi_global_history: list[float] = []
        self.interventions = 0

    def compute_phi_global(self) -> float:
        """Return the arithmetic mean of agent values, not IIT Phi."""
        return float(np.mean([agent.phi for agent in self.agents]))

    def run_experiment(self, cycles: int = 200, output_path: str | Path = DEFAULT_OUTPUT) -> Path:
        """Run the fixed toy simulation and save a new JSON log."""
        if isinstance(cycles, bool) or not isinstance(cycles, int) or cycles < 1:
            raise ValueError("cycles must be a positive integer.")

        print(f"Starting DIWT v3.7 toy simulation: {cycles} cycles")
        for cycle in range(cycles):
            stress = 0.02 if 66 <= cycle < 133 else 0.0
            for agent in self.agents:
                if agent.update_state(stress):
                    self.interventions += 1

            phi_global = self.compute_phi_global()
            self.phi_global_history.append(phi_global)
            if cycle % 50 == 0:
                print(f"Cycle {cycle}: simulated scalar mean = {phi_global:.3f}")

        return self.save_results(output_path)

    def save_results(self, output_path: str | Path = DEFAULT_OUTPUT) -> Path:
        """Save this simulation to a new path; refuse to replace any existing file."""
        if not self.phi_global_history:
            raise ValueError("Cannot save a simulation log before at least one cycle has been recorded.")

        results = {
            "record_type": "toy_simulation",
            "simulation_status": "simulated",
            "scalar_semantics": "Arithmetic mean of three simulated scalar states; not IIT Phi.",
            "experiment": "Triade Cognitiva",
            "version": "3.7",
            "date_utc": datetime.now(timezone.utc).isoformat(),
            "agents": [agent.name for agent in self.agents],
            "phi_global_initial": self.phi_global_history[0],
            "phi_global_min": min(self.phi_global_history),
            "phi_global_final": self.phi_global_history[-1],
            "cycles_total": len(self.phi_global_history),
            "threshold_interventions": self.interventions,
            "phi_history": self.phi_global_history,
        }

        output = Path(output_path).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8") as stream:
            json.dump(results, stream, indent=2)
            stream.write("\n")

        print(f"Simulation log saved without overwriting: {output}")
        print(f"Threshold interventions in this simulation: {self.interventions}")
        print(
            "Simulated scalar trajectory: "
            f"{results['phi_global_initial']:.3f} → "
            f"{results['phi_global_min']:.3f} → "
            f"{results['phi_global_final']:.3f}"
        )
        return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cycles", type=int, default=200, help="Number of simulation cycles (default: 200).")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="New JSON path (never overwritten).")
    args = parser.parse_args()
    TriadeCognitiva().run_experiment(cycles=args.cycles, output_path=args.output)


if __name__ == "__main__":
    main()
