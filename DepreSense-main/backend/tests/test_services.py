"""
Unit tests for service-layer functions.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import numpy as np
import pytest


# ═══════════════════════════════════════════════════════════
#  Model Inference Service
# ═══════════════════════════════════════════════════════════


class TestDetermineRiskLevel:
    """app.services.model_inference.determine_risk_level"""

    def test_low_risk(self):
        from app.services.model_inference import determine_risk_level
        assert determine_risk_level(0.0) == "low"
        assert determine_risk_level(0.1) == "low"
        assert determine_risk_level(0.32) == "low"

    def test_medium_risk(self):
        from app.services.model_inference import determine_risk_level
        assert determine_risk_level(0.33) == "medium"
        assert determine_risk_level(0.5) == "medium"
        assert determine_risk_level(0.66) == "medium"

    def test_high_risk(self):
        from app.services.model_inference import determine_risk_level
        assert determine_risk_level(0.67) == "high"
        assert determine_risk_level(0.9) == "high"
        assert determine_risk_level(1.0) == "high"

    def test_boundary_low_medium(self):
        from app.services.model_inference import determine_risk_level
        assert determine_risk_level(0.329) == "low"
        assert determine_risk_level(0.33) == "medium"

    def test_boundary_medium_high(self):
        from app.services.model_inference import determine_risk_level
        assert determine_risk_level(0.669) == "medium"
        assert determine_risk_level(0.67) == "high"


class TestFormatPrediction:
    """app.services.model_inference.format_prediction"""

    @patch("app.services.model_inference.log_model_inference")
    def test_format_prediction_structure(self, mock_log):
        from app.services.model_inference import format_prediction
        raw = {"depression_probability": 0.45, "epoch_probabilities": [0.45], "n_epochs": 1}
        result = format_prediction(raw)
        assert "prediction_id" in result
        assert "depression_probability" in result
        assert "risk_level" in result
        assert "confidence" in result
        assert "timestamp" in result
        assert isinstance(result["timestamp"], datetime)

    @patch("app.services.model_inference.log_model_inference")
    def test_format_prediction_confidence(self, mock_log):
        from app.services.model_inference import format_prediction
        # prob=0.5 → confidence = |0.5-0.5|*2 = 0.0
        result = format_prediction({"depression_probability": 0.5, "epoch_probabilities": [], "n_epochs": 0})
        assert result["confidence"] == 0.0

        # prob=0.0 → confidence = |0.0-0.5|*2 = 1.0
        result = format_prediction({"depression_probability": 0.0, "epoch_probabilities": [], "n_epochs": 0})
        assert result["confidence"] == 1.0


class TestRunInference:
    """app.services.model_inference.run_inference"""

    @patch("app.services.model_inference.get_model")
    @patch("app.services.model_inference.is_model_loaded", return_value=True)
    def test_run_inference_success(self, mock_loaded, mock_model):
        from app.services.model_inference import run_inference
        fake_model = MagicMock()
        fake_model.predict.return_value = np.array([[0.6], [0.7], [0.5]])
        mock_model.return_value = fake_model

        data = np.zeros((3, 1280, 19), dtype=np.float32)
        result = run_inference(data)
        assert "depression_probability" in result
        assert "epoch_probabilities" in result
        assert result["n_epochs"] == 3

    @patch("app.services.model_inference.is_model_loaded", return_value=False)
    def test_run_inference_model_not_loaded(self, mock_loaded):
        from app.services.model_inference import run_inference
        with pytest.raises(RuntimeError, match="Model is not loaded"):
            run_inference(np.zeros((1, 1280, 19), dtype=np.float32))


# ═══════════════════════════════════════════════════════════
#  File Handler Utilities
# ═══════════════════════════════════════════════════════════


class TestFileHandler:
    """app.utils.file_handler"""

    def test_validate_file_extension_valid(self):
        from app.utils.file_handler import validate_file_extension
        assert validate_file_extension("recording.edf") is True
        assert validate_file_extension("recording.EDF") is True

    def test_validate_file_extension_invalid(self):
        from app.utils.file_handler import validate_file_extension
        assert validate_file_extension("data.csv") is False
        assert validate_file_extension("image.png") is False
        assert validate_file_extension("file") is False

    def test_validate_file_size_within_limit(self):
        from app.utils.file_handler import validate_file_size
        assert validate_file_size(10 * 1024 * 1024, 50) is True  # 10 MB < 50 MB

    def test_validate_file_size_exceeds_limit(self):
        from app.utils.file_handler import validate_file_size
        assert validate_file_size(60 * 1024 * 1024, 50) is False  # 60 MB > 50 MB

    def test_generate_unique_file_id(self):
        from app.utils.file_handler import generate_unique_file_id
        id1 = generate_unique_file_id()
        id2 = generate_unique_file_id()
        assert len(id1) == 32
        assert id1 != id2


# ═══════════════════════════════════════════════════════════
#  SHAP Explainer
# ═══════════════════════════════════════════════════════════


class TestShapExplainer:
    """app.services.shap_explainer"""

    def test_empty_explanation(self):
        from app.services.shap_explainer import _empty_explanation
        result = _empty_explanation("test reason")
        assert result["feature_importance"] == {}
        assert result["top_features"] == []
        assert result["explanation_summary"] == "test reason"

    def test_format_explanation_serializable(self):
        from app.services.shap_explainer import format_explanation
        import json
        data = {
            "feature_importance": {"Fp1": {"abs_importance": np.float32(0.05)}},
            "top_features": ["Fp1"],
            "base_value": np.float64(0.5),
            "explanation_summary": "Test",
        }
        result = format_explanation(data)
        # Should not raise
        json.dumps(result)


# ═══════════════════════════════════════════════════════════
#  Firestore Service (mocked)
# ═══════════════════════════════════════════════════════════


class TestFirestoreService:
    """app.services.firestore_service — all DB calls mocked."""

    @patch("app.services.firestore_service.db_client")
    def test_create_user_record(self, mock_db):
        from app.services.firestore_service import create_user_record
        mock_db.collection.return_value.document.return_value.set.return_value = None
        result = create_user_record("uid-1", "a@b.com", "Alice")
        assert result["uid"] == "uid-1"
        assert result["email"] == "a@b.com"

    @patch("app.services.firestore_service.db_client")
    def test_get_user_found(self, mock_db):
        from app.services.firestore_service import get_user
        doc = MagicMock()
        doc.exists = True
        doc.to_dict.return_value = {"uid": "uid-1", "email": "a@b.com"}
        mock_db.collection.return_value.document.return_value.get.return_value = doc
        result = get_user("uid-1")
        assert result["uid"] == "uid-1"

    @patch("app.services.firestore_service.db_client")
    def test_get_user_not_found(self, mock_db):
        from app.services.firestore_service import get_user
        doc = MagicMock()
        doc.exists = False
        mock_db.collection.return_value.document.return_value.get.return_value = doc
        result = get_user("nonexistent")
        assert result is None

    @patch("app.services.firestore_service.db_client")
    def test_save_eeg_file_metadata(self, mock_db):
        from app.services.firestore_service import save_eeg_file_metadata
        chain = mock_db.collection.return_value.document.return_value.collection.return_value.document.return_value
        chain.set.return_value = None
        result = save_eeg_file_metadata("uid", "fid", {"original_filename": "test.edf"})
        assert result["file_id"] == "fid"

    @patch("app.services.firestore_service.db_client")
    def test_save_prediction(self, mock_db):
        from app.services.firestore_service import save_prediction
        chain = mock_db.collection.return_value.document.return_value.collection.return_value.document.return_value
        chain.set.return_value = None
        pred = {"prediction_id": "p1", "file_id": "f1", "depression_probability": 0.5}
        result = save_prediction("uid", pred)
        assert result["prediction_id"] == "p1"
