"""
DIWT v3.7: Triade Cognitiva Experiment
Integrates IIT, GWT, and FEP with ethical self-regulation
"""

import json
import numpy as np
from datetime import datetime


class DIWTAgent:
    """Multi-agent system with ethical self-regulation"""
    
    def __init__(self, name, phi_initial=0.8):
        self.name = name
        self.phi = phi_initial
        self.valence = 0.5
        self.ethical_threshold = 0.3
        
    def update_state(self, stress_factor=0.0):
        """Update agent state based on stress and ethical regulation"""
        # Apply stress
        self.phi *= (1 - stress_factor)
        
        # Ethical intervention if below threshold
        if self.phi < self.ethical_threshold:
            self.phi += 0.05  # Recovery boost
            return True  # Intervention occurred
        return False
        
    def get_state(self):
        return {"name": self.name, "phi": self.phi, "valence": self.valence}


class TriadeCognitiva:
    """Three-agent collective consciousness system"""
    
    def __init__(self):
        self.agents = [
            DIWTAgent("Agent_A", 0.85),
            DIWTAgent("Agent_B", 0.82),
            DIWTAgent("Agent_C", 0.88)
        ]
        self.phi_global_history = []
        self.interventions = 0
        
    def compute_phi_global(self):
        """Compute global integrated information"""
        phi_values = [agent.phi for agent in self.agents]
        return np.mean(phi_values)
        
    def run_experiment(self, cycles=200):
        """Run the Triade Cognitiva experiment"""
        print(f"Starting DIWT v3.7 Experiment: {cycles} cycles")
        
        for cycle in range(cycles):
            # Apply stress in middle third
            stress = 0.02 if 66 <= cycle < 133 else 0.0
            
            # Update all agents
            for agent in self.agents:
                if agent.update_state(stress):
                    self.interventions += 1
                    
            # Record global phi
            phi_global = self.compute_phi_global()
            self.phi_global_history.append(phi_global)
            
            if cycle % 50 == 0:
                print(f"Cycle {cycle}: Φ_global = {phi_global:.3f}")
                
        self.save_results()
        
    def save_results(self):
        """Save experiment results to JSON"""
        results = {
            "experiment": "Triade Cognitiva",
            "version": "3.7",
            "date": datetime.now().isoformat(),
            "agents": [agent.name for agent in self.agents],
            "phi_global_initial": self.phi_global_history[0],
            "phi_global_min": min(self.phi_global_history),
            "phi_global_final": self.phi_global_history[-1],
            "cycles_total": len(self.phi_global_history),
            "ethical_interventions": self.interventions,
            "phi_history": self.phi_global_history
        }
        
        with open('data/triade_log.json', 'w') as f:
            json.dump(results, f, indent=2)
            
        print(f"\nResults saved to data/triade_log.json")
        print(f"Ethical interventions: {self.interventions}")
        print(f"Φ trajectory: {results['phi_global_initial']:.3f} → {results['phi_global_min']:.3f} → {results['phi_global_final']:.3f}")


if __name__ == "__main__":
    triade = TriadeCognitiva()
    triade.run_experiment(cycles=200)
