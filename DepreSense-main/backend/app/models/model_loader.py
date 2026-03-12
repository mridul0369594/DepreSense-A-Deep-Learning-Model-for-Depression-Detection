"""
Model loader — singleton-cached TensorFlow/Keras model.

Loads the trained ``.keras`` model from disk once and caches it in
memory.  Also supports ``.h5``, ``.pkl``, and ``.joblib`` formats as
fallbacks.
"""

from __future__ import annotations

import logging
import os
import pickle
from pathlib import Path

import joblib
import numpy as np
import tensorflow as tf

from app.config import settings

logger = logging.getLogger(__name__)

# ── Module-level cache ─────────────────────────────────────
_model: tf.keras.Model | None = None
_shap_background: np.ndarray | None = None


def load_model(model_path: str) -> tf.keras.Model:
    """Load a trained model from *model_path*.

    Supported extensions: ``.keras``, ``.h5``, ``.pkl``, ``.joblib``.
    """
    path = Path(model_path)

    if not path.exists():
        raise FileNotFoundError(f"Model file not found: {model_path}")

    ext = path.suffix.lower()

    if ext in (".keras", ".h5"):
        model = tf.keras.models.load_model(str(path), compile=False)
        logger.info("Loaded Keras model from %s", model_path)
    elif ext == ".pkl":
        with open(path, "rb") as f:
            model = pickle.load(f)  # noqa: S301
        logger.info("Loaded pickle model from %s", model_path)
    elif ext == ".joblib":
        model = joblib.load(str(path))
        logger.info("Loaded joblib model from %s", model_path)
    else:
        raise ValueError(f"Unsupported model format: {ext}")

    return model


def _resolve_model_file() -> str:
    """Find the actual model file inside ``settings.MODEL_PATH``.

    If MODEL_PATH points to a directory, look for the primary soup model
    (``soup_model_EC.keras``) first, then any ``.keras`` / ``.h5`` file.
    """
    p = Path(settings.MODEL_PATH)

    if p.is_file():
        return str(p)

    # Directory — try known filename first
    preferred = p / "soup_model_EC.keras"
    if preferred.exists():
        return str(preferred)

    # Fall back to first model file found
    for ext in ("*.keras", "*.h5", "*.pkl", "*.joblib"):
        files = list(p.glob(ext))
        if files:
            return str(files[0])

    raise FileNotFoundError(
        f"No model file found in {settings.MODEL_PATH}"
    )


def _load_shap_background() -> np.ndarray | None:
    """Load the SHAP background data if available."""
    bg_path = Path(settings.SHAP_BG_PATH)
    if bg_path.exists():
        bg = np.load(str(bg_path)).astype(np.float32)
        logger.info("Loaded SHAP background from %s  shape=%s", bg_path, bg.shape)
        return bg
    logger.warning("SHAP background file not found: %s", bg_path)
    return None


def get_model() -> tf.keras.Model:
    """Return the cached model, loading it on first call (singleton)."""
    global _model
    if _model is None:
        model_file = _resolve_model_file()
        _model = load_model(model_file)
    return _model


def get_shap_background() -> np.ndarray | None:
    """Return the cached SHAP background data."""
    global _shap_background
    if _shap_background is None:
        _shap_background = _load_shap_background()
    return _shap_background


def is_model_loaded() -> bool:
    """Return ``True`` if the model is currently cached in memory."""
    return _model is not None


def unload_model() -> None:
    """Clear the cached model from memory."""
    global _model, _shap_background
    _model = None
    _shap_background = None
    logger.info("Model unloaded from memory.")
