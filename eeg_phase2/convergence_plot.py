"""
DIWT v4.0 Phase 2: EEG-DIWT Convergence Visualization
Shows convergence between EEG-derived Φ and DIWT Φ
"""

import matplotlib.pyplot as plt
import numpy as np


def generate_convergence_plot():
    """Generate EEG ↔ DIWT convergence visualization"""
    
    cycles = 200
    
    # Simulate EEG-derived Φ (noisy, from neural data)
    phi_eeg = np.cumsum(np.random.normal(0, 0.05, cycles)) + 0.5
    phi_eeg = np.clip(phi_eeg, 0.2, 0.9)
    
    # Simulate DIWT Φ (converging to EEG)
    phi_diwt = [0.3]
    alpha = 0.025  # Convergence rate
    
    for i in range(1, cycles):
        # Convergence dynamics: DIWT adapts to EEG
        phi_diwt.append(phi_diwt[-1] + alpha * (phi_eeg[i] - phi_diwt[-1]))
    
    # Calculate convergence error
    error = np.abs(phi_eeg - np.array(phi_diwt))
    
    # Create figure with subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
    
    # Plot 1: Φ trajectories
    ax1.plot(phi_eeg, label='Φ EEG (Neural)', alpha=0.7, 
             linewidth=2, color='#E63946', linestyle='--')
    ax1.plot(phi_diwt, label='Φ DIWT (Model)', 
             linewidth=2.5, color='#2E86AB')
    ax1.set_title('EEG ↔ DIWT Convergence', fontsize=16, fontweight='bold')
    ax1.set_xlabel('Cycle', fontsize=12)
    ax1.set_ylabel('Φ Value', fontsize=12)
    ax1.legend(fontsize=11)
    ax1.grid(alpha=0.3)
    
    # Plot 2: Convergence error
    ax2.plot(error, linewidth=2, color='#06A77D')
    ax2.fill_between(range(cycles), 0, error, alpha=0.3, color='#06A77D')
    ax2.set_title('Convergence Error', fontsize=14, fontweight='bold')
    ax2.set_xlabel('Cycle', fontsize=12)
    ax2.set_ylabel('|Φ_EEG - Φ_DIWT|', fontsize=12)
    ax2.grid(alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('visualizations_v37/eeg_convergence.png', dpi=200)
    plt.close()
    
    print("✓ Generated: visualizations_v37/eeg_convergence.png")
    print(f"  Final error: {error[-1]:.4f}")
    print(f"  Mean error: {np.mean(error):.4f}")


if __name__ == "__main__":
    print("DIWT v4.0 Phase 2: Generating EEG Convergence Plot\n")
    generate_convergence_plot()
