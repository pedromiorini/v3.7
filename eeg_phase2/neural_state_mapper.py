"""Unvalidated sequence-model prototype with a synthetic demonstration trainer.

The demo generates random features and random targets; it does not train on real
EEG, decode a clinical or motor-imagery label, estimate consciousness, or compute
IIT Phi. Its sigmoid output is only an arbitrary scalar score.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import torch
import torch.nn as nn

try:
    from mamba_ssm import Mamba
    MAMBA_AVAILABLE = True
except ImportError:
    MAMBA_AVAILABLE = False
    print("Warning: mamba-ssm not installed. Using mock architecture.")


DEFAULT_CHECKPOINT = (
    Path.home()
    / ".cache"
    / "diwt-v3.7-mock"
    / "neural_state_mapper.mock.generated.pth"
)


class NeuralStateMapper(nn.Module):
    """Map input sequences to an unvalidated scalar score in the range [0, 1]."""
    
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
            # Demonstration fallback only; this is not a validated EEG model.
            self.mamba = nn.LSTM(d_model, d_model, batch_first=True)
        
        self.fc = nn.Sequential(
            nn.Linear(d_model, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Sigmoid()
        )
    
    def forward(self, x):
        """Return an arbitrary scalar score for ``(batch, seq_len, d_model)`` input."""
        if MAMBA_AVAILABLE:
            hidden = self.mamba(x)
        else:
            hidden, _ = self.mamba(x)

        pooled = hidden.mean(dim=1)
        return self.fc(pooled)


def save_mock_checkpoint(state_dict, checkpoint_path: str | Path = DEFAULT_CHECKPOINT) -> Path:
    """Save synthetic demo weights to a new path; never overwrite existing data."""
    target = Path(checkpoint_path).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w+b",
            dir=target.parent,
            prefix=f".{target.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            torch.save(state_dict, stream)
            stream.flush()
            os.fsync(stream.fileno())
        # Staging beside the destination keeps publication on one filesystem.
        # link() creates the name only if no competing writer has created it.
        os.link(temporary, target)
    finally:
        if temporary is not None:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
    return target


def train_mock_model(checkpoint_path: str | Path = DEFAULT_CHECKPOINT) -> Path:
    """Train a toy demo on synthetic random targets, not on real EEG.

    This is not a validated EEG decoder, a consciousness model, or an IIT Phi
    measure. The resulting checkpoint contains demo weights only.
    """
    print("Training synthetic Neural State Mapper demo; inputs and targets are random...")
    model = NeuralStateMapper()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

    for epoch in range(10):
        x = torch.randn(8, 100, 64)
        y = torch.rand(8, 1)
        score = model(x)
        loss = nn.MSELoss()(score, y)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        if epoch % 3 == 0:
            print(f"Epoch {epoch}: synthetic-demo loss = {loss.item():.4f}")

    saved = save_mock_checkpoint(model.state_dict(), checkpoint_path)
    print(f"Saved explicitly synthetic demo checkpoint: {saved}")
    return saved


if __name__ == "__main__":
    train_mock_model()
