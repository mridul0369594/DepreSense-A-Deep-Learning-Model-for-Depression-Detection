"""
Tests for global error handling and the error response format.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import patch

import pytest

from app.middleware.error_handler import (
    AppException,
    AuthenticationFailedError,
    FileNotFoundAppError,
    FileTooLargeError,
    ForbiddenError,
    InferenceError,
    InvalidEdfFileError,
    InvalidFileFormatError,
    ModelNotLoadedError,
    PreprocessingError,
    UnauthorizedError,
)


# ── Exception class tests ──────────────────────────────────


class TestExceptionClasses:
    """Verify custom exception attributes."""

    def test_app_exception_defaults(self):
        exc = AppException()
        assert exc.code == "APP_ERROR"
        assert exc.status_code == 500

    def test_invalid_file_format_error(self):
        exc = InvalidFileFormatError()
        assert exc.code == "INVALID_FILE_FORMAT"
        assert exc.status_code == 400

    def test_file_too_large_error(self):
        exc = FileTooLargeError()
        assert exc.code == "FILE_TOO_LARGE"
        assert exc.status_code == 413

    def test_file_not_found_error(self):
        exc = FileNotFoundAppError()
        assert exc.code == "FILE_NOT_FOUND"
        assert exc.status_code == 404

    def test_unauthorized_error(self):
        exc = UnauthorizedError()
        assert exc.code == "UNAUTHORIZED"
        assert exc.status_code == 401

    def test_forbidden_error(self):
        exc = ForbiddenError()
        assert exc.code == "FORBIDDEN"
        assert exc.status_code == 403

    def test_model_not_loaded_error(self):
        exc = ModelNotLoadedError()
        assert exc.code == "MODEL_NOT_LOADED"
        assert exc.status_code == 503

    def test_inference_error(self):
        exc = InferenceError()
        assert exc.code == "INFERENCE_ERROR"
        assert exc.status_code == 500

    def test_preprocessing_error(self):
        exc = PreprocessingError()
        assert exc.code == "PREPROCESSING_ERROR"
        assert exc.status_code == 500

    def test_authentication_failed_error(self):
        exc = AuthenticationFailedError()
        assert exc.code == "AUTHENTICATION_FAILED"
        assert exc.status_code == 401

    def test_custom_message(self):
        exc = InvalidFileFormatError("Only .edf please")
        assert exc.message == "Only .edf please"


# ── Error response format via API ──────────────────────────


class TestErrorResponseFormat:
    """Hit actual endpoints to verify the error JSON shape."""

    def test_401_missing_token(self, test_client):
        resp = test_client.get("/auth/me")
        assert resp.status_code == 401
        detail = resp.json()["detail"]
        assert "code" in detail
        assert "message" in detail

    @patch("app.routes.eeg.firestore_service")
    def test_404_file_not_found(self, mock_fs, test_client, auth_headers):
        mock_fs.get_eeg_file.return_value = None
        resp = test_client.get("/eeg/files/nonexistent", headers=auth_headers)
        assert resp.status_code == 404
        detail = resp.json()["detail"]
        assert detail["code"] == "FILE_NOT_FOUND"

    def test_422_invalid_body(self, test_client, auth_headers):
        resp = test_client.post("/auth/signup", json={"email": "bad"})
        assert resp.status_code == 422

    def test_error_does_not_expose_traceback(self, test_client):
        resp = test_client.get("/auth/me")
        body = resp.text
        assert "Traceback" not in body
        assert "File " not in body

    def test_x_request_id_on_error(self, test_client):
        resp = test_client.get("/auth/me")
        rid = resp.headers.get("x-request-id", "")
        assert len(rid) == 32

    @patch("app.routes.predictions.is_model_loaded", return_value=False)
    def test_503_model_not_loaded(self, mock_loaded, test_client, auth_headers):
        resp = test_client.post("/predictions/predict", json={"file_id": "x"}, headers=auth_headers)
        assert resp.status_code == 503
        assert resp.json()["detail"]["code"] == "MODEL_NOT_LOADED"

    def test_missing_required_fields(self, test_client, auth_headers):
        resp = test_client.post("/predictions/predict", json={}, headers=auth_headers)
        assert resp.status_code == 422

    def test_invalid_json_body(self, test_client, auth_headers):
        resp = test_client.post(
            "/auth/signup",
            content=b"not json",
            headers={**auth_headers, "Content-Type": "application/json"},
        )
        assert resp.status_code == 422
