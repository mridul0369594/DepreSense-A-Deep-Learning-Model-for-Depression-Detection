"""
preprocessing_ec.py

Reusable EEG preprocessing utilities for DepreSense (EC-only deployment focus).

Exports:
- process_channels(raw)
- bandpass_filter(raw, l_freq, h_freq, notch_freq)
- preprocess_ICA(epochs, n_components, method)
- preprocess_eeg(raw, ...) -> data_4d (n_epochs, 19, 1280, 1)
- to_model_input(data_4d) -> X (n_epochs, 1280, 19) float32
- infer_one_edf(edf_path, ...) -> X (n_epochs, 1280, 19) float32
"""

from __future__ import annotations

import os
import numpy as np
import mne
from mne.preprocessing import ICA

# -----------------------------
# Constants
# -----------------------------
CHANNELS_19 = [
    "Fp1", "Fp2", "F7", "F8", "F3", "F4", "T3", "T4",
    "C3", "C4", "Fz", "Cz", "Pz", "P3", "P4", "T5",
    "T6", "O1", "O2",
]

# Channels to remove from the EDFs
DROP_MARKERS = ["23A-23R", "24A-24R", "A2-A1"]

# More likely to contain frontal artifacts
ICA_CHANNELS = ["Fp1", "Fp2", "F7", "F8"]


# -----------------------------
# Core helpers
# -----------------------------
def read_data(edf_file_path: str, preload: bool = True) -> mne.io.BaseRaw:
    """
    Read EDF and set EEG reference
    """
    raw = mne.io.read_raw_edf(edf_file_path, preload=preload, verbose="ERROR")
    raw.set_eeg_reference(verbose="ERROR")
    return raw


def process_channels(raw_data: mne.io.BaseRaw, verbose: bool = True) -> mne.io.BaseRaw:
    """
    Standardize EEG channel names to match training and keep exactly the 19 channels.

    - Drops channels containing DROP_MARKERS (e.g., A2-A1, 23A-23R, 24A-24R)
    - Renames: 'EEG Fp1-LE' -> 'Fp1'
    - Keeps only CHANNELS_19 in the exact order defined above
    """
    raw = raw_data.copy()

    if verbose:
        print(f"Initial channels: {raw.ch_names}")

    # Build rename map + channels to drop
    rename_map = {}
    channels_to_drop = []

    for name in raw.ch_names:
        if any(x in name for x in DROP_MARKERS):
            channels_to_drop.append(name)
        else:
            new_name = name.replace("EEG ", "").replace("-LE", "")
            rename_map[name] = new_name

    if channels_to_drop:
        if verbose:
            print(f"Dropping channels: {channels_to_drop}")
        raw.drop_channels(channels_to_drop)

    raw.rename_channels(rename_map)

    # Keep EEG only (in case EDF has non-EEG channels)
    raw.pick_types(eeg=True)

    # Now enforce exact channel list + order
    present = set(raw.ch_names)
    missing = [ch for ch in CHANNELS_19 if ch not in present]
    if missing:
        raise ValueError(f"Missing required channels: {missing}. Present: {raw.ch_names}")

    # pick_channels(..., ordered=True) enforces the exact order
    raw.pick_channels(CHANNELS_19, ordered=True)

    if verbose:
        print(f"Final channels: {raw.ch_names} (n={len(raw.ch_names)})")

    return raw


def bandpass_filter(
    raw: mne.io.BaseRaw,
    l_freq: float,
    h_freq: float,
    notch_freq: float | None = None,
    verbose: bool = True,
) -> mne.io.BaseRaw:
    """
    Apply bandpass filter and optional notch filter.
    """
    filtered = raw.copy()

    if verbose:
        print(f"Filtering: bandpass {l_freq}-{h_freq} Hz")

    filtered.filter(l_freq=l_freq, h_freq=h_freq, fir_design="firwin", phase="zero", verbose="ERROR")

    if notch_freq is not None:
        if verbose:
            print(f"Filtering: notch {notch_freq} Hz")
        filtered.notch_filter(freqs=notch_freq, notch_widths=2.0, verbose="ERROR")

    return filtered


def preprocess_ICA(
    epochs: mne.Epochs,
    n_components: int,
    method: str = "fastica",
    random_state: int = 42,
    verbose: bool = True,
) -> ICA:
    """
    Fit ICA on selected channels (frontal channels by default) then return ICA object.
    """
    if verbose:
        print(f"Fitting ICA on {len(epochs)} epochs... (n_components={n_components})")

    ica = ICA(n_components=n_components, method=method, random_state=random_state, max_iter="auto")

    # Fit ICA only on ICA_CHANNELS if present
    pick = [ch for ch in ICA_CHANNELS if ch in epochs.ch_names]
    if len(pick) == 0:
        raise ValueError(f"None of ICA_CHANNELS found in epochs. Epoch channels: {epochs.ch_names}")

    ica.fit(epochs.copy().pick_channels(pick), verbose="ERROR")
    return ica

def create_epochs(
    raw: mne.io.BaseRaw,
    duration: float = 5.0,
    overlap: float = 0.5,
    verbose: bool = True,
) -> mne.Epochs:
    """
    Create fixed-length epochs from continuous EEG.
    """
    epochs = mne.make_fixed_length_epochs(
        raw,
        duration=duration,
        overlap=overlap,
        preload=True,
        verbose="ERROR",
    )
    epochs.drop_bad()
    if verbose:
        print(f"Epoching completed: {len(epochs)} epochs")
    return epochs


# -----------------------------
# Full preprocessing pipeline
# -----------------------------
def preprocess_eeg(
    raw_data: mne.io.BaseRaw,
    l_freq: float = 0.5,
    h_freq: float = 70.0,
    notch_freq: float = 50.0,
    n_components: int = 4,
    epoch_duration: float = 5.0,
    epoch_overlap: float = 0.5,
    ica_method: str = "fastica",
    seed: int = 42,
    verbose: bool = True,
) -> np.ndarray | None:
    """
    Complete pipeline:
      filter -> channel standardization -> epoching -> ICA -> baseline -> per-epoch z-score

    Returns:
      data_4d: (n_epochs, 19, 1280, 1) float32
      or None if something fails.
    """
    try:
        # 1) Filter
        if verbose:
            print("1. Applying bandpass+notch filter...")
        processed = bandpass_filter(raw_data, l_freq, h_freq, notch_freq, verbose=verbose)

        # 2) Channels
        if verbose:
            print("2. Standardizing + selecting channels...")
        processed = process_channels(processed, verbose=verbose)

        # 3) Epoching
        if verbose:
            print("3. Creating epochs...")
        epochs = create_epochs(processed, duration=epoch_duration, overlap=epoch_overlap, verbose=verbose)

        # Sanity check timepoints
        expected_tp = int(epoch_duration * processed.info["sfreq"])
        # epochs.get_data() is (n_epochs, n_channels, n_times)
        if epochs.get_data().shape[2] != expected_tp:
            raise ValueError(
                f"Unexpected epoch length: got {epochs.get_data().shape[2]} samples, expected {expected_tp}"
            )

        # 4) ICA
        if verbose:
            print("4. Applying ICA...")
        ica = preprocess_ICA(epochs, n_components, method=ica_method, random_state=seed, verbose=verbose)
        ica.apply(epochs, verbose="ERROR")

        # 5) Baseline
        if verbose:
            print("5. Baseline correction...")
        epochs.apply_baseline((None, None))

        # 6) Extract data AFTER ICA + baseline
        if verbose:
            print("6. Extracting final epoch array...")
        d = epochs.get_data()  # (n_epochs, 19, 1280)

        # per-epoch z-score normalization over time (axis=2)
        mean = d.mean(axis=2, keepdims=True)
        std = d.std(axis=2, keepdims=True) + 1e-6
        d = (d - mean) / std

        data_4d = d[..., np.newaxis].astype(np.float32)  # (n_epochs, 19, 1280, 1)

        if verbose:
            print(f"Final data shape returned: {data_4d.shape}")

        return data_4d

    except Exception as e:
        if verbose:
            print(f"Preprocessing error: {e}")
        return None


# -----------------------------
# Model input adapter + single-file inference helper
# -----------------------------
def to_model_input(data_4d: np.ndarray) -> np.ndarray:
    """
    Convert pipeline output (n_epochs, 19, 1280, 1)
    -> Conv1D input (n_epochs, 1280, 19) float32
    """
    X = data_4d.squeeze(-1)          # (n_epochs, 19, 1280)
    X = X.transpose(0, 2, 1)         # (n_epochs, 1280, 19)
    return X.astype(np.float32)


def infer_one_edf(
    edf_path: str,
    l_freq: float = 0.5,
    h_freq: float = 70.0,
    notch_freq: float = 50.0,
    n_components: int = 4,
    epoch_duration: float = 5.0,
    epoch_overlap: float = 0.5,
    ica_method: str = "fastica",
    seed: int = 42,
    verbose: bool = False,
) -> np.ndarray:
    """
    End-to-end: EDF -> Raw -> preprocess_eeg -> to_model_input

    Returns:
      X_subject: (n_epochs, 1280, 19) float32
    """
    raw = read_data(edf_path, preload=True)
    data_4d = preprocess_eeg(
        raw,
        l_freq=l_freq,
        h_freq=h_freq,
        notch_freq=notch_freq,
        n_components=n_components,
        epoch_duration=epoch_duration,
        epoch_overlap=epoch_overlap,
        ica_method=ica_method,
        seed=seed,
        verbose=verbose,
    )
    if data_4d is None:
        raise RuntimeError(f"Preprocessing failed for: {os.path.basename(edf_path)}")

    return to_model_input(data_4d)