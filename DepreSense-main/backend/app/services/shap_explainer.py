"""
SHAP explainability service.

Generates channel-level SHAP explanations using ``GradientExplainer``
for the loaded Keras model, mirroring the methodology in
``data/predict_one_edf_shap.py``.
"""

from __future__ import annotations

import logging
import time

import numpy as np
import shap

from app.models.model_loader import get_model, get_shap_background

logger = logging.getLogger(__name__)

# The 19 standard EEG channels used by the model
CHANNELS_19 = [
    "Fp1", "Fp2", "F7", "F8", "F3", "F4", "T3", "T4",
    "C3", "C4", "Fz", "Cz", "Pz", "P3", "P4", "T5",
    "T6", "O1", "O2",
]


def generate_shap_explanation(
    processed_eeg_data: np.ndarray,
    prediction: dict,
    max_explain_epochs: int = 20,
) -> dict:
    """Generate SHAP channel-importance values for a prediction.

    Parameters
    ----------
    processed_eeg_data : np.ndarray
        Shape ``(n_epochs, 1280, 19)`` float32.
    prediction : dict
        Formatted prediction from ``model_inference.format_prediction``.
    max_explain_epochs : int
        Maximum number of epochs to feed to the SHAP explainer (for speed).

    Returns
    -------
    dict
        ``feature_importance``, ``top_features``, ``base_value``,
        ``explanation_summary``.
    """
    start = time.perf_counter()
    try:
        model = get_model()
        X_bg = get_shap_background()

        if X_bg is None:
            logger.warning("SHAP background not available — returning empty explanation.")
            return _empty_explanation("SHAP background data not available.")

        # Limit epochs for speed
        n_explain = min(max_explain_epochs, processed_eeg_data.shape[0])
        X_explain = processed_eeg_data[:n_explain].astype(np.float32)

        logger.info(
            "Generating SHAP explanation — %d epochs, bg shape=%s",
            n_explain, X_bg.shape,
        )

        # GradientExplainer (matches the original training script)
        explainer = shap.GradientExplainer(model, X_bg)
        shap_values = explainer.shap_values(X_explain)

        # Normalise shape
        if isinstance(shap_values, list):
            shap_values = shap_values[0]
        if shap_values.ndim == 4 and shap_values.shape[-1] == 1:
            shap_values = shap_values[..., 0]

        if shap_values.ndim != 3 or shap_values.shape[-1] != 19:
            raise ValueError(
                f"Unexpected SHAP shape: {shap_values.shape} "
                "(expected (E, 1280, 19))"
            )

        # Aggregate to channel-level importance (raw)
        channel_abs_raw = np.mean(np.abs(shap_values), axis=(0, 1))   # (19,)
        channel_signed_raw = np.mean(shap_values, axis=(0, 1))         # (19,)

        logger.info(
            "Raw SHAP stats — min_abs=%.8f  max_abs=%.8f  sum=%.8f",
            channel_abs_raw.min(), channel_abs_raw.max(), channel_abs_raw.sum(),
        )

        # ── Normalize to relative scale (0–1) ──
        # Raw GradientExplainer values are very small (~0.0003).
        # Normalize so the maximum channel = 1.0 for meaningful display.
        abs_max = channel_abs_raw.max()
        if abs_max > 0:
            channel_abs = channel_abs_raw / abs_max         # 0–1 scale
            channel_signed = channel_signed_raw / abs_max   # preserve sign, relative
        else:
            channel_abs = channel_abs_raw
            channel_signed = channel_signed_raw

        # Build feature importance dict
        feature_importance = {
            ch: {
                "abs_importance": round(float(channel_abs[i]), 6),
                "signed_importance": round(float(channel_signed[i]), 6),
            }
            for i, ch in enumerate(CHANNELS_19)
        }

        # Top 5 channels by absolute importance
        order = np.argsort(channel_abs)[::-1]
        top_features = [CHANNELS_19[i] for i in order[:5]]

        # Base value (mean model output on background)
        base_value = float(prediction.get("depression_probability", 0.5))

        # Human-readable summary
        risk = prediction.get("risk_level", "unknown")
        summary = (
            f"The model predicts a {risk} risk of depression. "
            f"The most influential EEG channels are "
            f"{', '.join(top_features[:3])}, which contributed most "
            f"to the prediction."
        )

        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "SHAP explanation generated — top features: %s  values: %s  (%.1f ms)",
            top_features[:3],
            [round(float(channel_abs[i]), 4) for i in order[:3]],
            elapsed_ms,
        )

        return {
            "feature_importance": feature_importance,
            "top_features": top_features,
            "base_value": round(base_value, 4),
            "explanation_summary": summary,
        }

    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.error("SHAP explanation failed after %.1f ms: %s", elapsed_ms, exc)
        return _empty_explanation(f"SHAP generation error: {exc}")


def format_explanation(shap_data: dict) -> dict:
    """Ensure all SHAP output values are JSON-serialisable."""
    return {
        "feature_importance": {
            ch: {
                k: float(v) if isinstance(v, (np.floating, float)) else v
                for k, v in vals.items()
            }
            for ch, vals in shap_data.get("feature_importance", {}).items()
        },
        "top_features": list(shap_data.get("top_features", [])),
        "base_value": float(shap_data.get("base_value", 0.0)),
        "explanation_summary": str(
            shap_data.get("explanation_summary", "")
        ),
    }


def _empty_explanation(reason: str) -> dict:
    """Return a placeholder explanation when SHAP is unavailable."""
    return {
        "feature_importance": {},
        "top_features": [],
        "base_value": 0.0,
        "explanation_summary": reason,
    }
