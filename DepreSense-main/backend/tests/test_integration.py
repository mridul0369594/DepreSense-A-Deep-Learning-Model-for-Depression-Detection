"""
End-to-end integration tests that exercise full request workflows.

These tests mock Firebase but exercise the complete middleware → route →
service → response pipeline.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import numpy as np
import pytest


@pytest.mark.integration
class TestFullAuthFlow:
    """Signup → Login → Get Me → Logout"""

    @patch("app.routes.auth.auth_client")
    @patch("app.routes.auth._firebase_rest_auth")
    @patch("app.routes.auth.firestore_service")
    def test_full_auth_flow(self, mock_fs, mock_rest, mock_auth, test_client, auth_headers):
        # 1. Signup
        rec = MagicMock()
        rec.uid = "int-uid"
        rec.email = "int@test.com"
        rec.display_name = "Int User"
        mock_auth.create_user.return_value = rec
        mock_rest.return_value = {"idToken": "signup-token"}
        mock_auth.EmailAlreadyExistsError = type("EmailAlreadyExistsError", (Exception,), {})

        resp = test_client.post("/auth/signup", json={
            "email": "int@test.com", "password": "Pass123!", "name": "Int User"
        })
        assert resp.status_code == 201
        token = resp.json()["token"]

        # 2. Get Me (using the existing mock_firebase_app from conftest)
        mock_user_fs = {"uid": "test-uid-001", "email": "test@example.com", "name": "Test User"}
        with patch("app.routes.auth.firestore_service") as fs2:
            fs2.get_user.return_value = mock_user_fs
            resp = test_client.get("/auth/me", headers=auth_headers)
            assert resp.status_code == 200
            assert resp.json()["uid"] == "test-uid-001"

        # 3. Logout
        with patch("app.routes.auth.auth_client") as logout_auth:
            logout_auth.revoke_refresh_tokens.return_value = None
            resp = test_client.post("/auth/logout", headers=auth_headers)
            assert resp.status_code == 200


@pytest.mark.integration
class TestFullEEGFlow:
    """Upload → List → Get → Delete"""

    @patch("app.routes.eeg.firestore_service")
    @patch("app.routes.eeg.validate_edf_file", return_value=True)
    @patch("app.routes.eeg.save_uploaded_file")
    @patch("app.routes.eeg.delete_file", return_value=True)
    def test_full_eeg_flow(self, mock_del, mock_save, mock_validate, mock_fs, test_client, auth_headers, sample_file_metadata):
        file_id = "flow-fid"
        mock_save.return_value = (file_id, f"./uploads/{file_id}.edf")

        # 1. Upload
        files = {"file": ("test.edf", b"\x00" * 100, "application/octet-stream")}
        resp = test_client.post("/eeg/upload", files=files, headers=auth_headers)
        assert resp.status_code == 201

        # 2. List
        meta = {**sample_file_metadata, "file_id": file_id}
        mock_fs.get_all_eeg_files.return_value = [meta]
        resp = test_client.get("/eeg/files", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

        # 3. Get
        mock_fs.get_eeg_file.return_value = meta
        resp = test_client.get(f"/eeg/files/{file_id}", headers=auth_headers)
        assert resp.status_code == 200

        # 4. Delete
        resp = test_client.delete(f"/eeg/files/{file_id}", headers=auth_headers)
        assert resp.status_code == 200


@pytest.mark.integration
class TestFullPredictionFlow:
    """Upload → Predict → History → Get specific"""

    @patch("app.routes.predictions.firestore_service")
    @patch("app.routes.predictions.format_explanation")
    @patch("app.routes.predictions.generate_shap_explanation")
    @patch("app.routes.predictions.format_prediction")
    @patch("app.routes.predictions.run_inference")
    @patch("app.routes.predictions._preprocess_edf")
    @patch("app.routes.predictions.is_model_loaded", return_value=True)
    @patch("os.path.exists", return_value=True)
    def test_full_prediction_flow(
        self, mock_exists, mock_loaded, mock_pre, mock_inf,
        mock_fmt, mock_shap, mock_shap_fmt, mock_fs,
        test_client, auth_headers, sample_prediction_data,
    ):
        now = datetime.now(timezone.utc)
        mock_fs.get_eeg_file.return_value = {"file_path": "./x.edf", "file_id": "fid"}
        mock_pre.return_value = np.zeros((1, 1280, 19), dtype=np.float32)
        mock_inf.return_value = {"depression_probability": 0.7, "epoch_probabilities": [0.7], "n_epochs": 1}
        mock_fmt.return_value = {
            "prediction_id": "pred-flow", "depression_probability": 0.7,
            "risk_level": "high", "confidence": 0.4, "timestamp": now,
        }
        mock_shap_fmt.return_value = {
            "feature_importance": {}, "top_features": ["Fp1"],
            "explanation_summary": "High risk.",
        }

        # 1. Predict
        resp = test_client.post("/predictions/predict",
                                json={"file_id": "fid"}, headers=auth_headers)
        assert resp.status_code == 201
        pid = resp.json()["result"]["prediction_id"]

        # 2. History
        mock_fs.get_all_predictions.return_value = [sample_prediction_data]
        resp = test_client.get("/predictions/history", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

        # 3. Get specific
        mock_fs.get_prediction.return_value = sample_prediction_data
        resp = test_client.get(f"/predictions/{sample_prediction_data['prediction_id']}",
                               headers=auth_headers)
        assert resp.status_code == 200


@pytest.mark.integration
class TestCrossEndpointSecurity:
    """Verify auth required across all protected endpoints."""

    @pytest.mark.parametrize("method,path", [
        ("GET", "/auth/me"),
        ("POST", "/auth/logout"),
        ("GET", "/eeg/files"),
        ("GET", "/eeg/files/x"),
        ("DELETE", "/eeg/files/x"),
        ("GET", "/predictions/history"),
        ("GET", "/predictions/x"),
    ])
    def test_all_protected_endpoints_require_auth(self, method, path, test_client):
        resp = test_client.request(method, path)
        assert resp.status_code == 401, f"{method} {path} should require auth"

    def test_upload_requires_auth(self, test_client):
        files = {"file": ("t.edf", b"\x00", "application/octet-stream")}
        resp = test_client.post("/eeg/upload", files=files)
        assert resp.status_code == 401

    def test_predict_requires_auth(self, test_client):
        resp = test_client.post("/predictions/predict", json={"file_id": "x"})
        assert resp.status_code == 401
