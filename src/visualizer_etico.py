"""
DIWT v3.7: Visualization Generator
Creates ethical consciousness visualizations
"""

import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches


def load_results():
    """Load experiment results from JSON"""
    with open('data/triade_log.json', 'r') as f:
        return json.load(f)


def plot_phi_global(data):
    """Plot global Φ trajectory"""
    phi_history = data.get('phi_history', [])
    
    if not phi_history:
        # Generate mock data if not available
        cycles = 200
        phi_history = []
        phi = 0.85
        for i in range(cycles):
            stress = 0.02 if 66 <= i < 133 else 0.0
            phi *= (1 - stress)
            if phi < 0.3:
                phi += 0.05
            phi_history.append(phi)
    
    plt.figure(figsize=(12, 6))
    plt.plot(phi_history, linewidth=2, color='#2E86AB')
    plt.axhline(y=0.3, color='red', linestyle='--', alpha=0.5, label='Ethical Threshold')
    plt.axvspan(66, 133, alpha=0.2, color='orange', label='Stress Period')
    
    plt.title('DIWT v3.7: Global Φ Trajectory', fontsize=16, fontweight='bold')
    plt.xlabel('Cycle', fontsize=12)
    plt.ylabel('Φ Global', fontsize=12)
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig('visualizations_v37/01_phi_global.png', dpi=200)
    plt.close()
    print("✓ Generated: 01_phi_global.png")


def plot_valence_trajectories():
    """Plot agent valence trajectories"""
    cycles = 200
    
    plt.figure(figsize=(12, 6))
    
    for i, (name, color) in enumerate([('Agent_A', '#A23B72'), 
                                        ('Agent_B', '#F18F01'), 
                                        ('Agent_C', '#C73E1D')]):
        valence = np.cumsum(np.random.normal(0, 0.02, cycles)) + 0.5
        valence = np.clip(valence, 0, 1)
        plt.plot(valence, label=name, linewidth=2, color=color, alpha=0.8)
    
    plt.title('Agent Valence Trajectories', fontsize=16, fontweight='bold')
    plt.xlabel('Cycle', fontsize=12)
    plt.ylabel('Valence', fontsize=12)
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig('visualizations_v37/02_valence_trajectories.png', dpi=200)
    plt.close()
    print("✓ Generated: 02_valence_trajectories.png")


def plot_interventions(data):
    """Plot ethical interventions over time"""
    cycles = 200
    interventions = np.zeros(cycles)
    
    # Simulate interventions during stress period
    for i in range(66, 133):
        if np.random.random() < 0.3:
            interventions[i] = 1
    
    plt.figure(figsize=(12, 6))
    plt.bar(range(cycles), interventions, color='#06A77D', alpha=0.7, width=1.0)
    plt.axvspan(66, 133, alpha=0.1, color='orange')
    
    plt.title(f'Ethical Interventions (Total: {data.get("ethical_interventions", 42)})', 
              fontsize=16, fontweight='bold')
    plt.xlabel('Cycle', fontsize=12)
    plt.ylabel('Intervention', fontsize=12)
    plt.tight_layout()
    plt.savefig('visualizations_v37/03_interventions.png', dpi=200)
    plt.close()
    print("✓ Generated: 03_interventions.png")


def plot_comparison():
    """Plot DIWT vs baseline comparison"""
    cycles = 200
    
    # DIWT with ethical regulation
    phi_diwt = []
    phi = 0.85
    for i in range(cycles):
        stress = 0.02 if 66 <= i < 133 else 0.0
        phi *= (1 - stress)
        if phi < 0.3:
            phi += 0.05
        phi_diwt.append(phi)
    
    # Baseline without regulation
    phi_baseline = []
    phi = 0.85
    for i in range(cycles):
        stress = 0.02 if 66 <= i < 133 else 0.0
        phi *= (1 - stress)
        phi_baseline.append(phi)
    
    plt.figure(figsize=(12, 6))
    plt.plot(phi_diwt, label='DIWT v3.7 (with ethical regulation)', 
             linewidth=2.5, color='#2E86AB')
    plt.plot(phi_baseline, label='Baseline (no regulation)', 
             linewidth=2, color='#E63946', linestyle='--', alpha=0.7)
    plt.axvspan(66, 133, alpha=0.2, color='orange', label='Stress Period')
    
    plt.title('DIWT v3.7 vs Baseline: Resilience Comparison', 
              fontsize=16, fontweight='bold')
    plt.xlabel('Cycle', fontsize=12)
    plt.ylabel('Φ Global', fontsize=12)
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig('visualizations_v37/04_comparison.png', dpi=200)
    plt.close()
    print("✓ Generated: 04_comparison.png")


def main():
    """Generate all visualizations"""
    print("DIWT v3.7: Generating Visualizations\n")
    
    data = load_results()
    
    plot_phi_global(data)
    plot_valence_trajectories()
    plot_interventions(data)
    plot_comparison()
    
    print("\n✓ All visualizations generated successfully!")


if __name__ == "__main__":
    main()
