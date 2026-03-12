"""
Prediction endpoints — run inference and SHAP on uploaded EEG files.

All endpoints require authentication.
Results are persisted to Firestore.
"""

from __future__ import annotations

import logging
import os
import sys

from fastapi import APIRouter, Depends, HTTPException, status

from app.config import settings
from app.middleware.auth_middleware import get_current_user
from app.models.model_loader import is_model_loaded
from app.schemas.prediction import (
    PredictionRequest,
    PredictionResponse,
    PredictionResult,
    ShapExplanation,
)
from app.services import firestore_service
from app.services.model_inference import format_prediction, run_inference
from app.services.shap_explainer import format_explanation, generate_shap_explanation

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/predictions", tags=["Predictions"])


def _preprocess_edf(file_path: str):
    """Run the full preprocessing pipeline on a .edf file.

    Imports the original ``infer_one_edf`` from the data/ directory so
    we reuse the exact same pipeline that was used during training.
    """
    # Add the data/ directory to sys.path so we can import preprocessing_ec
    # From backend/app/routes → go up 3 levels to DepreSense-main, then into data/
    data_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "data")
    )
    if data_dir not in sys.path:
        sys.path.insert(0, data_dir)

    from preprocessing_ec import infer_one_edf  # type: ignore[import-untyped]

    return infer_one_edf(file_path, verbose=False)


# ── POST /predictions/predict ─────────────────────────────


@router.post(
    "/predict",
    response_model=PredictionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def predict(
    body: PredictionRequest,
    user: dict = Depends(get_current_user),
):
    """Run depression prediction on an uploaded EEG file.

    Pipeline: validate file → preprocess → inference → SHAP → persist → respond.
    """
    uid = user["uid"]

    # 1. Check model is loaded
    if not is_model_loaded():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "MODEL_NOT_LOADED",
                "message": "The ML model is not loaded. Please try again later.",
            },
        )

    # 2. Retrieve file metadata from Firestore
    file_meta = firestore_service.get_eeg_file(uid, body.file_id)

    # Fallback: if Firestore is unavailable / metadata missing, check disk
    if file_meta is None:
        from app.utils.file_handler import get_file_path as _get_file_path

        disk_path = _get_file_path(body.file_id, settings.UPLOAD_DIR)
        if os.path.exists(disk_path):
            logger.warning(
                "Firestore metadata missing for %s — falling back to disk at %s",
                body.file_id,
                disk_path,
            )
            file_meta = {"file_path": disk_path, "file_id": body.file_id}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "FILE_NOT_FOUND",
                    "message": f"No uploaded file found with id '{body.file_id}'.",
                },
            )

    file_path = file_meta.get("file_path", "")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "FILE_NOT_FOUND",
                "message": "The file is no longer available on disk.",
            },
        )

    # 3. Mark file as processing
    firestore_service.update_eeg_file_status(uid, body.file_id, "processing")

    # Track total processing time for the system status dashboard
    import time as _time
    _pipeline_start = _time.perf_counter()

    # 4. Preprocess EEG
    try:
        processed_data = _preprocess_edf(file_path)
    except Exception as exc:
        logger.error("Preprocessing failed for %s: %s", body.file_id, exc)
        firestore_service.update_eeg_file_status(uid, body.file_id, "error")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "PREPROCESSING_ERROR",
                "message": f"EEG preprocessing failed: {exc}",
            },
        )

    # 5. Run inference
    try:
        raw_prediction = run_inference(processed_data)
        formatted = format_prediction(raw_prediction)
    except Exception as exc:
        logger.error("Inference failed for %s: %s", body.file_id, exc)
        firestore_service.update_eeg_file_status(uid, body.file_id, "error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "INFERENCE_ERROR",
                "message": f"Model inference failed: {exc}",
            },
        )

    # 6. Generate SHAP explanation
    try:
        shap_raw = generate_shap_explanation(processed_data, formatted)
        shap_data = format_explanation(shap_raw)
        shap_data["shap_status"] = "success"
    except Exception as exc:
        logger.warning("SHAP failed for %s: %s — returning empty explanation", body.file_id, exc)
        shap_data = {
            "feature_importance": {},
            "top_features": [],
            "base_value": 0.0,
            "explanation_summary": f"SHAP explanation could not be generated: {exc}",
            "shap_status": "error",
        }

    # Calculate total pipeline processing time in seconds
    _pipeline_elapsed = round(_time.perf_counter() - _pipeline_start, 2)

    # 7. Mark file as completed
    firestore_service.update_eeg_file_status(uid, body.file_id, "completed")

    # 8. Persist prediction to Firestore
    prediction_record = {
        "prediction_id": formatted["prediction_id"],
        "file_id": body.file_id,
        "depression_probability": formatted["depression_probability"],
        "risk_level": formatted["risk_level"],
        "confidence": formatted["confidence"],
        "timestamp": formatted["timestamp"],
        "shap_explanation": shap_data,
        "model_version": "1.0.0",
        "processing_time": _pipeline_elapsed,
    }

    try:
        firestore_service.save_prediction(uid, prediction_record)
    except Exception as exc:
        logger.warning("Firestore prediction save failed (non-blocking): %s", exc)

    # 9. Build response
    result = PredictionResult(**formatted)
    explanation = ShapExplanation(**shap_data)

    return PredictionResponse(
        result=result,
        explanation=explanation,
        message="Prediction completed successfully",
    )


# ── GET /predictions/history ──────────────────────────────


@router.get("/history", response_model=list[PredictionResponse])
async def prediction_history(user: dict = Depends(get_current_user)):
    """Return all past predictions for the authenticated user from Firestore."""
    records = firestore_service.get_all_predictions(user["uid"])

    return [
        PredictionResponse(
            result=PredictionResult(
                prediction_id=r.get("prediction_id", ""),
                depression_probability=r.get("depression_probability", 0.0),
                risk_level=r.get("risk_level", "unknown"),
                confidence=r.get("confidence", 0.0),
                timestamp=r.get("created_at", r.get("timestamp")),
            ),
            explanation=ShapExplanation(**r.get("shap_explanation", {})),
            message="Historical prediction",
        )
        for r in records
    ]


# ── GET /predictions/{prediction_id} ──────────────────────


@router.get("/{prediction_id}", response_model=PredictionResponse)
async def get_prediction(
    prediction_id: str,
    user: dict = Depends(get_current_user),
):
    """Return a specific prediction result by ID from Firestore."""
    record = firestore_service.get_prediction(user["uid"], prediction_id)

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "PREDICTION_NOT_FOUND",
                "message": "Prediction not found or access denied.",
            },
        )

    return PredictionResponse(
        result=PredictionResult(
            prediction_id=record.get("prediction_id", prediction_id),
            depression_probability=record.get("depression_probability", 0.0),
            risk_level=record.get("risk_level", "unknown"),
            confidence=record.get("confidence", 0.0),
            timestamp=record.get("created_at", record.get("timestamp")),
        ),
        explanation=ShapExplanation(**record.get("shap_explanation", {})),
        message="Prediction retrieved",
    )
