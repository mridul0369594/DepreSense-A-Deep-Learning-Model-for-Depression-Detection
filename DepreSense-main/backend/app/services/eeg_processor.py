"""
EEG preprocessing service.

Provides functions for validating, reading, preprocessing, and
feature-extracting from .edf EEG recordings.
"""

from __future__ import annotations

import logging
import time

import mne

from app.utils.logger import log_database_operation

logger = logging.getLogger(__name__)


def validate_edf_file(file_path: str) -> bool:
    """Check whether *file_path* points to a readable .edf file.

    Uses MNE to attempt a lightweight read of the file header.
    Returns ``True`` if the file can be parsed, ``False`` otherwise.
    """
    start = time.perf_counter()
    try:
        mne.io.read_raw_edf(file_path, preload=False, verbose=False)
        elapsed = (time.perf_counter() - start) * 1000
        logger.info(
            "EDF validation passed for %s (%.1f ms)", file_path, elapsed
        )
        return True
    except Exception as exc:
        elapsed = (time.perf_counter() - start) * 1000
        logger.warning(
            "EDF validation FAILED for %s (%.1f ms): %s",
            file_path, elapsed, exc,
        )
        return False


def read_edf_file(file_path: str) -> dict:
    """Read a .edf file and return its raw data as a dictionary.

    Returns a dict with keys:
        - ``raw``: the MNE Raw object
        - ``info``: recording metadata (channels, sfreq, etc.)
    """
    start = time.perf_counter()
    try:
        raw = mne.io.read_raw_edf(file_path, preload=True, verbose=False)
        elapsed = (time.perf_counter() - start) * 1000
        logger.info(
            "Read EDF file %s — %d channels, %.1f s duration (%.1f ms)",
            file_path,
            len(raw.ch_names),
            raw.n_times / raw.info["sfreq"],
            elapsed,
        )
        return {
            "raw": raw,
            "info": {
                "channels": raw.ch_names,
                "n_channels": len(raw.ch_names),
                "sfreq": raw.info["sfreq"],
                "duration_sec": raw.n_times / raw.info["sfreq"],
                "n_samples": raw.n_times,
            },
        }
    except Exception as exc:
        logger.error("Failed to read EDF file %s: %s", file_path, exc)
        raise ValueError(f"Cannot read EDF file: {exc}") from exc


def preprocess_eeg_data(raw_data: dict) -> dict:
    """Apply preprocessing to raw EEG data.

    TODO: Implement actual preprocessing pipeline:
        - Band-pass filtering
        - Notch filtering (50/60 Hz)
        - Re-referencing
        - ICA-based artifact removal
        - Epoch segmentation

    For now, returns the raw data unchanged.
    """
    logger.info("preprocess_eeg_data called — returning raw data as-is (TODO)")
    return raw_data


def extract_features(processed_data: dict) -> dict:
    """Extract features from preprocessed EEG data.

    TODO: Implement feature extraction:
        - Power spectral density per band (delta, theta, alpha, beta, gamma)
        - Statistical features
        - Connectivity metrics

    For now, returns an empty dict.
    """
    logger.info("extract_features called — returning empty dict (TODO)")
    return {}
