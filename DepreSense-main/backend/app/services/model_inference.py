"""
Model inference service.

Runs the loaded Keras model on preprocessed EEG data and formats the
prediction output.
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone

import numpy as np

from app.models.model_loader import get_model, is_model_loaded
from app.utils.logger import log_model_inference

logger = logging.getLogger(__name__)


def determine_risk_level(probability: float) -> str:
    """Map a depression probability (0–1) to a risk category.

    - 0.00 – 0.33  →  ``"low"``
    - 0.33 – 0.67  →  ``"medium"``
    - 0.67 – 1.00  →  ``"high"``
    """
    if probability < 0.33:
        return "low"
    elif probability < 0.67:
        return "medium"
    return "high"


def run_inference(processed_eeg_data: np.ndarray) -> dict:
    """Run the model on preprocessed EEG data.

    Parameters
    ----------
    processed_eeg_data : np.ndarray
        Shape ``(n_epochs, 1280, 19)`` — float32, output of the
        preprocessing pipeline's ``to_model_input()``.

    Returns
    -------
    dict
        ``depression_probability`` (float), ``epoch_probabilities``
        (list[float]), ``n_epochs`` (int).
    """
    if not is_model_loaded():
        raise RuntimeError("Model is not loaded. Cannot run inference.")

    model = get_model()
    n_epochs = processed_eeg_data.shape[0]
    logger.info("Starting inference on %d epochs …", n_epochs)

    start = time.perf_counter()
    try:
        # Model outputs sigmoid probability per epoch → shape (n_epochs, 1)
        epoch_probs = model.predict(processed_eeg_data, verbose=0).reshape(-1)
        subject_prob = float(np.mean(epoch_probs))
        elapsed_ms = (time.perf_counter() - start) * 1000

        result = {
            "depression_probability": subject_prob,
            "epoch_probabilities": epoch_probs.tolist(),
            "n_epochs": len(epoch_probs),
        }

        logger.info(
            "Inference completed — prob=%.4f  risk=%s  epochs=%d  %.1f ms",
            subject_prob,
            determine_risk_level(subject_prob),
            n_epochs,
            elapsed_ms,
        )
        return result
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.error("Inference failed after %.1f ms: %s", elapsed_ms, exc)
        raise RuntimeError(f"Model inference error: {exc}") from exc


def format_prediction(raw_prediction: dict) -> dict:
    """Format a raw inference result into a structured API response.

    Parameters
    ----------
    raw_prediction : dict
        Output of :func:`run_inference`.

    Returns
    -------
    dict
        Structured prediction with ``prediction_id``,
        ``depression_probability``, ``risk_level``, ``confidence``, and
        ``timestamp``.
    """
    prob = raw_prediction["depression_probability"]
    risk = determine_risk_level(prob)
    # Confidence: distance from the decision boundary (0.5)
    confidence = round(abs(prob - 0.5) * 2, 4)

    formatted = {
        "prediction_id": uuid.uuid4().hex,
        "depression_probability": round(prob, 4),
        "risk_level": risk,
        "confidence": round(confidence, 4),
        "timestamp": datetime.now(timezone.utc),
    }

    log_model_inference(
        file_id="<direct>",
        prediction_result=formatted,
    )

    return formatted
