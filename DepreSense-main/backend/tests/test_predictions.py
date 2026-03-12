"""
Tests for prediction endpoints:  /predictions/predict, /predictions/history, /predictions/{id}
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import numpy as np
import pytest


# ── Predict ─────────────────────────────────────────────────


class TestPredict:
    """POST /predictions/predict"""

    @patch("app.routes.predictions.firestore_service")
    @patch("app.routes.predictions.format_explanation")
    @patch("app.routes.predictions.generate_shap_explanation")
    @patch("app.routes.predictions.format_prediction")
    @patch("app.routes.predictions.run_inference")
    @patch("app.routes.predictions._preprocess_edf")
    @patch("app.routes.predictions.is_model_loaded", return_value=True)
    @patch("os.path.exists", return_value=True)
    def test_predict_success(
        self, mock_exists, mock_loaded, mock_preprocess, mock_infer,
        mock_format, mock_shap, mock_shap_fmt, mock_fs,
        test_client, auth_headers,
    ):
        mock_fs.get_eeg_file.return_value = {"file_path": "./uploads/f.edf", "file_id": "fid"}
        mock_preprocess.return_value = np.zeros((10, 1280, 19), dtype=np.float32)
        mock_infer.return_value = {"depression_probability": 0.45, "epoch_probabilities": [0.45], "n_epochs": 10}
        now = datetime.now(timezone.utc)
        mock_format.return_value = {
            "prediction_id": "pred-001",
            "depression_probability": 0.45,
            "risk_level": "medium",
            "confidence": 0.10,
            "timestamp": now,
        }
        mock_shap.return_value = {
            "feature_importance": {"Fp1": {"abs_importance": 0.05}},
            "top_features": ["Fp1", "F3"],
            "base_value": 0.45,
            "explanation_summary": "Medium risk.",
        }
        mock_shap_fmt.return_value = {
            "feature_importance": {"Fp1": {"abs_importance": 0.05}},
            "top_features": ["Fp1", "F3"],
            "base_value": 0.45,
            "explanation_summary": "Medium risk.",
        }

        resp = test_client.post("/predictions/predict", json={"file_id": "fid"}, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert "result" in data
        assert "explanation" in data
        assert data["result"]["prediction_id"] == "pred-001"
        assert data["result"]["risk_level"] == "medium"

    @patch("app.routes.predictions.firestore_service")
    @patch("app.routes.predictions.format_explanation")
    @patch("app.routes.predictions.generate_shap_explanation")
    @patch("app.routes.predictions.format_prediction")
    @patch("app.routes.predictions.run_inference")
    @patch("app.routes.predictions._preprocess_edf")
    @patch("app.routes.predictions.is_model_loaded", return_value=True)
    @patch("os.path.exists", return_value=True)
    def test_predict_response_structure(
        self, mock_exists, mock_loaded, mock_pre, mock_inf,
        mock_fmt, mock_shap, mock_shap_fmt, mock_fs,
        test_client, auth_headers,
    ):
        now = datetime.now(timezone.utc)
        mock_fs.get_eeg_file.return_value = {"file_path": "./x.edf", "file_id": "fid"}
        mock_pre.return_value = np.zeros((1, 1280, 19), dtype=np.float32)
        mock_inf.return_value = {"depression_probability": 0.2, "epoch_probabilities": [0.2], "n_epochs": 1}
        mock_fmt.return_value = {
            "prediction_id": "p1", "depression_probability": 0.2,
            "risk_level": "low", "confidence": 0.6, "timestamp": now,
        }
        mock_shap_fmt.return_value = {"feature_importance": {}, "top_features": [], "base_value": 0.0, "explanation_summary": ""}

        resp = test_client.post("/predictions/predict", json={"file_id": "fid"}, headers=auth_headers)
        data = resp.json()
        # Verify required fields
        for key in ("prediction_id", "depression_probability", "risk_level", "confidence", "timestamp"):
            assert key in data["result"]
        for key in ("feature_importance", "top_features", "explanation_summary"):
            assert key in data["explanation"]

    @patch("app.routes.predictions.firestore_service")
    @patch("app.routes.predictions.is_model_loaded", return_value=True)
    def test_predict_file_not_found(self, mock_loaded, mock_fs, test_client, auth_headers):
        mock_fs.get_eeg_file.return_value = None
        resp = test_client.post("/predictions/predict", json={"file_id": "bad-id"}, headers=auth_headers)
        assert resp.status_code == 404
        assert resp.json()["detail"]["code"] == "FILE_NOT_FOUND"

    @patch("app.routes.predictions.is_model_loaded", return_value=False)
    def test_predict_model_not_loaded(self, mock_loaded, test_client, auth_headers):
        resp = test_client.post("/predictions/predict", json={"file_id": "fid"}, headers=auth_headers)
        assert resp.status_code == 503
        assert resp.json()["detail"]["code"] == "MODEL_NOT_LOADED"

    @patch("app.routes.predictions.firestore_service")
    @patch("app.routes.predictions._preprocess_edf")
    @patch("app.routes.predictions.is_model_loaded", return_value=True)
    @patch("os.path.exists", return_value=True)
    def test_predict_preprocessing_error(self, mock_exists, mock_loaded, mock_pre, mock_fs, test_client, auth_headers):
        mock_fs.get_eeg_file.return_value = {"file_path": "./x.edf", "file_id": "fid"}
        mock_pre.side_effect = RuntimeError("Channel mismatch")
        resp = test_client.post("/predictions/predict", json={"file_id": "fid"}, headers=auth_headers)
        assert resp.status_code == 422
        assert resp.json()["detail"]["code"] == "PREPROCESSING_ERROR"

    @patch("app.routes.predictions.firestore_service")
    @patch("app.routes.predictions.run_inference")
    @patch("app.routes.predictions._preprocess_edf")
    @patch("app.routes.predictions.is_model_loaded", return_value=True)
    @patch("os.path.exists", return_value=True)
    def test_predict_inference_error(self, mock_exists, mock_loaded, mock_pre, mock_inf, mock_fs, test_client, auth_headers):
        mock_fs.get_eeg_file.return_value = {"file_path": "./x.edf", "file_id": "fid"}
        mock_pre.return_value = np.zeros((1, 1280, 19), dtype=np.float32)
        mock_inf.side_effect = RuntimeError("TensorFlow OOM")
        resp = test_client.post("/predictions/predict", json={"file_id": "fid"}, headers=auth_headers)
        assert resp.status_code == 500
        assert resp.json()["detail"]["code"] == "INFERENCE_ERROR"

    def test_predict_unauthenticated(self, test_client):
        resp = test_client.post("/predictions/predict", json={"file_id": "fid"})
        assert resp.status_code == 401

    def test_predict_missing_file_id(self, test_client, auth_headers):
        resp = test_client.post("/predictions/predict", json={}, headers=auth_headers)
        assert resp.status_code == 422  # pydantic validation


# ── History ─────────────────────────────────────────────────


class TestPredictionHistory:
    """GET /predictions/history"""

    @patch("app.routes.predictions.firestore_service")
    def test_get_history_authenticated(self, mock_fs, test_client, auth_headers, sample_prediction_data):
        mock_fs.get_all_predictions.return_value = [sample_prediction_data]
        resp = test_client.get("/predictions/history", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 1

    @patch("app.routes.predictions.firestore_service")
    def test_get_history_empty_list(self, mock_fs, test_client, auth_headers):
        mock_fs.get_all_predictions.return_value = []
        resp = test_client.get("/predictions/history", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_history_unauthenticated(self, test_client):
        resp = test_client.get("/predictions/history")
        assert resp.status_code == 401


# ── Get Prediction by ID ───────────────────────────────────


class TestGetPredictionById:
    """GET /predictions/{prediction_id}"""

    @patch("app.routes.predictions.firestore_service")
    def test_get_prediction_by_id_success(self, mock_fs, test_client, auth_headers, sample_prediction_data):
        mock_fs.get_prediction.return_value = sample_prediction_data
        pid = sample_prediction_data["prediction_id"]
        resp = test_client.get(f"/predictions/{pid}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["result"]["prediction_id"] == pid

    @patch("app.routes.predictions.firestore_service")
    def test_get_prediction_by_id_not_found(self, mock_fs, test_client, auth_headers):
        mock_fs.get_prediction.return_value = None
        resp = test_client.get("/predictions/nonexistent-id", headers=auth_headers)
        assert resp.status_code == 404
        assert resp.json()["detail"]["code"] == "PREDICTION_NOT_FOUND"

    def test_get_prediction_by_id_unauthenticated(self, test_client):
        resp = test_client.get("/predictions/some-id")
        assert resp.status_code == 401
