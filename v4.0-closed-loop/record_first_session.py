"""
DIWT v4.0: Record First Closed-Loop Session (Mock)
Simulates the recording of the first human-AI closed-loop session.
"""
import json
import time
import random
import numpy as np

# Mock dependencies
try:
    import torch
    from mamba_ssm import Mamba
    MAMBA_AVAILABLE = True
except ImportError:
    MAMBA_AVAILABLE = False

# --- Mock DIWT System Components ---

class MockEEGMapper:
    """Simulates the Mamba SSM mapping EEG to Phi."""
    def map_eeg_to_phi(self, eeg_signal):
        # Simulate a base Phi with random fluctuations
        base_phi = 0.8 + random.uniform(-0.05, 0.05)
        # Simulate a drop in Phi during the stress period (cycles 30-70)
        if 30 <= self.cycle < 70:
            base_phi -= 0.2 * np.sin((self.cycle - 30) / 40 * np.pi)
        return max(0.3, min(0.9, base_phi))

class MockEthicalRegulator:
    """Simulates the ethical intervention mechanism."""
    def __init__(self):
        self.interventions = 0
        
    def check_and_intervene(self, phi):
        if phi < 0.5:
            self.interventions += 1
            return True, 0.1  # Intervention provides a Phi boost
        return False, 0.0

# --- Recording Logic ---

def record_session(cycles=100):
    print("Starting DIWT v4.0 Closed-Loop Session Recording...")
    
    mapper = MockEEGMapper()
    regulator = MockEthicalRegulator()
    
    session_data = {
        "metadata": {
            "version": "v4.0",
            "date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "cycles": cycles,
            "description": "First closed-loop session with simulated human EEG."
        },
        "log": []
    }
    
    for cycle in range(cycles):
        mapper.cycle = cycle
        
        # 1. Simulate EEG signal (mock)
        eeg_signal = random.uniform(-100, 100)
        
        # 2. Map EEG to DIWT Phi
        phi_eeg = mapper.map_eeg_to_phi(eeg_signal)
        
        # 3. Ethical Regulation
        intervened, phi_boost = regulator.check_and_intervene(phi_eeg)
        phi_diwt = phi_eeg + phi_boost
        
        # 4. Log the cycle
        session_data["log"].append({
            "cycle": cycle,
            "eeg_signal": round(eeg_signal, 3),
            "phi_eeg": round(phi_eeg, 4),
            "phi_diwt": round(phi_diwt, 4),
            "intervened": intervened
        })
        
        if cycle % 10 == 0:
            print(f"Cycle {cycle}: Φ_EEG={phi_eeg:.4f}, Φ_DIWT={phi_diwt:.4f}, Intervened={intervened}")
            
    session_data["metadata"]["total_interventions"] = regulator.interventions
    
    # Save the recording
    with open('session_recording.json', 'w') as f:
        json.dump(session_data, f, indent=2)
        
    print(f"\nRecording complete. Total interventions: {regulator.interventions}")
    print("Data saved to session_recording.json")

if __name__ == "__main__":
    record_session()
