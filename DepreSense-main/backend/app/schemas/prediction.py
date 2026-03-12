"""
Pydantic models for prediction requests and responses.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Request ────────────────────────────────────────────────


class PredictionRequest(BaseModel):
    """Payload to request a depression prediction for an uploaded EEG file."""

    file_id: str = Field(..., description="ID of the previously uploaded .edf file")


# ── Result sub-models ──────────────────────────────────────


class PredictionResult(BaseModel):
    """Core prediction output."""

    prediction_id: str = Field(..., description="Unique prediction identifier")
    depression_probability: float = Field(
        ..., ge=0.0, le=1.0, description="Probability of depression (0–1)"
    )
    risk_level: str = Field(
        ..., description="Risk category: low, medium, or high"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Prediction confidence (0–1)"
    )
    timestamp: datetime = Field(..., description="When the prediction was made")


class ShapExplanation(BaseModel):
    """SHAP-based explainability output."""

    feature_importance: dict = Field(
        default_factory=dict,
        description="Per-channel SHAP importance values",
    )
    top_features: list[str] = Field(
        default_factory=list,
        description="Top contributing EEG channels",
    )
    base_value: float = Field(
        0.0, description="Base prediction value (model output on background data)"
    )
    explanation_summary: str = Field(
        "", description="Human-readable summary of the explanation"
    )
    shap_status: str = Field(
        "success",
        description="Status of SHAP computation: 'success', 'error', or 'unavailable'",
    )


# ── Full response ─────────────────────────────────────────


class PredictionResponse(BaseModel):
    """Complete prediction response returned to the client."""

    result: PredictionResult
    explanation: ShapExplanation
    message: str = Field("Prediction completed successfully")
