"""
DIWT v4.0 Phase 2: Neural State Mapper
Maps EEG signals to DIWT consciousness states using Mamba SSM
"""

import torch
import torch.nn as nn
import numpy as np

try:
    from mamba_ssm import Mamba
    MAMBA_AVAILABLE = True
except ImportError:
    MAMBA_AVAILABLE = False
    print("Warning: mamba-ssm not installed. Using mock architecture.")


class NeuralStateMapper(nn.Module):
    """Maps EEG signals to consciousness states using Mamba"""
    
    def __init__(self, d_model=64, d_state=16, d_conv=4, expand=2):
        super().__init__()
        
        if MAMBA_AVAILABLE:
            self.mamba = Mamba(
                d_model=d_model,
                d_state=d_state,
                d_conv=d_conv,
                expand=expand
            )
        else:
            # Fallback to LSTM
            self.mamba = nn.LSTM(d_model, d_model, batch_first=True)
        
        self.fc = nn.Sequential(
            nn.Linear(d_model, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Sigmoid()
        )
    
    def forward(self, x):
        """
        Args:
            x: (batch, seq_len, d_model) EEG features
        Returns:
            phi: (batch, 1) consciousness measure
        """
        if MAMBA_AVAILABLE:
            h = self.mamba(x)
        else:
            h, _ = self.mamba(x)
        
        # Pool over sequence dimension
        h_pooled = h.mean(dim=1)
        
        # Map to phi value
        phi = self.fc(h_pooled)
        return phi


def train_mock_model():
    """Train a mock model for demonstration"""
    print("Training Neural State Mapper (mock)...")
    
    model = NeuralStateMapper()
    
    # Mock training loop
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    
    for epoch in range(10):
        # Generate mock batch
        x = torch.randn(8, 100, 64)  # 8 samples, 100 timesteps, 64 features
        y = torch.rand(8, 1)  # Target phi values
        
        # Forward pass
        phi_pred = model(x)
        loss = nn.MSELoss()(phi_pred, y)
        
        # Backward pass
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        
        if epoch % 3 == 0:
            print(f"Epoch {epoch}: Loss = {loss.item():.4f}")
    
    # Save model
    torch.save(model.state_dict(), 'eeg_phase2/neural_state_mapper.pth')
    print("✓ Model saved to eeg_phase2/neural_state_mapper.pth")


if __name__ == "__main__":
    train_mock_model()
