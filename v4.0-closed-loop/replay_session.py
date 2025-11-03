"""
DIWT v4.0: Replay Closed-Loop Session
Loads the session recording and generates the results visualization.
"""
import json
import matplotlib.pyplot as plt
import numpy as np
import os

def load_session_data(file_path='session_recording.json'):
    """Loads the session data from a JSON file."""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Session recording file not found at {file_path}")
        print("Please run record_first_session.py first.")
        return None

def generate_results_plot(data):
    """Generates the closed-loop simulation results plot."""
    log = data.get('log', [])
    if not log:
        print("Error: No log data found in the session recording.")
        return

    cycles = [item['cycle'] for item in log]
    phi_eeg = [item['phi_eeg'] for item in log]
    phi_diwt = [item['phi_diwt'] for item in log]
    interventions = [item['intervened'] for item in log]

    interventions_x = [cycles[i] for i, val in enumerate(interventions) if val]
    interventions_y = [phi_diwt[i] for i, val in enumerate(interventions) if val]

    plt.figure(figsize=(12, 6))
    plt.plot(cycles, phi_eeg, label='Neural Φ (EEG-derived)', color='#2E86AB', linestyle='--')
    plt.plot(cycles, phi_diwt, label='DIWT Φ (Ethically Regulated)', color='#06A77D', linewidth=2)
    plt.scatter(interventions_x, interventions_y, color='red', marker='o', s=50, label='Ethical Intervention')

    plt.title('DIWT v4.0 Closed-Loop Simulation Results', fontsize=16, fontweight='bold')
    plt.xlabel('Cycle (Time)', fontsize=12)
    plt.ylabel('Integrated Information (Φ)', fontsize=12)
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()

    output_path = 'closed_loop_simulation_results.png'
    plt.savefig(output_path, dpi=200)
    plt.close()
    print(f"\n✓ Results plot generated: {output_path}")

def replay_session():
    """Main function to replay the session."""
    data = load_session_data()
    if data:
        print(f"Replaying session from {data['metadata']['date']}...")
        print(f"Total cycles: {data['metadata']['cycles']}")
        print(f"Total ethical interventions: {data['metadata']['total_interventions']}")
        generate_results_plot(data)

if __name__ == "__main__":
    replay_session()
