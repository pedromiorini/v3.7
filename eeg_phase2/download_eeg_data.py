"""
DIWT v4.0 Phase 2: EEG Data Downloader
Downloads and preprocesses EEG data from MNE-Python datasets
"""

import os
import numpy as np

try:
    import mne
    from mne.datasets import eegbci
    
    # Create data directory
    os.makedirs('eeg_phase2/eeg_data', exist_ok=True)
    
    # Download EEG data (subject 1, run 1)
    print("Downloading EEG data from EEGBCI dataset...")
    eegbci.load_data(1, 1, 'eeg_phase2/eeg_data')
    
    # Load and preprocess
    print("Loading and preprocessing EEG data...")
    raw = mne.io.read_raw_edf('eeg_phase2/eeg_data/S001/S001R01.edf', preload=True)
    raw.filter(1, 45)  # Bandpass filter
    
    # Extract data
    data = raw.get_data()
    
    # Save preprocessed data
    np.save('eeg_phase2/eeg_data/raw_eeg.npy', data)
    print(f"✓ EEG data saved: {data.shape}")
    
except ImportError:
    print("MNE-Python not installed. Install with: pip install mne")
    print("Generating mock EEG data instead...")
    
    # Generate mock EEG data
    os.makedirs('eeg_phase2/eeg_data', exist_ok=True)
    mock_data = np.random.randn(64, 16000) * 1e-5  # 64 channels, 16000 samples
    np.save('eeg_phase2/eeg_data/raw_eeg.npy', mock_data)
    print(f"✓ Mock EEG data generated: {mock_data.shape}")
