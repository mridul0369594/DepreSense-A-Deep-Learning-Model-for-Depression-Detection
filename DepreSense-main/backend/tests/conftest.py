"""
Shared pytest fixtures for the DepreSense backend test suite.

Provides mock Firebase clients, authenticated test clients, and reusable
sample data so individual test files stay focused on assertions.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# ── Fake Firebase helpers ──────────────────────────────────


def _fake_user_record(uid: str = "test-uid-001", email: str = "test@example.com", name: str = "Test User"):
    """Return a mock object that looks like a Firebase UserRecord."""
    rec = MagicMock()
    rec.uid = uid
    rec.email = email
    rec.display_name = name
    return rec


# ── Fixtures ───────────────────────────────────────────────


@pytest.fixture(scope="session")
def mock_firebase_app():
    """Patch Firebase initialisation for the entire test session.

    This prevents any real Firebase calls during testing.
    """
    with (
        patch("app.utils.firebase_client._init_firebase"),
        patch("app.utils.firebase_client._firebase_app", new=MagicMock()),
        patch("app.utils.firebase_client.db_client", new=MagicMock()),
        patch("app.utils.firebase_client.auth_client") as mock_auth,
    ):
        # Wire up exception classes the middleware checks for
        mock_auth.ExpiredIdTokenError = type("ExpiredIdTokenError", (Exception,), {})
        mock_auth.RevokedIdTokenError = type("RevokedIdTokenError", (Exception,), {})
        mock_auth.InvalidIdTokenError = type("InvalidIdTokenError", (Exception,), {})
        mock_auth.EmailAlreadyExistsError = type("EmailAlreadyExistsError", (Exception,), {})
        mock_auth.UserNotFoundError = type("UserNotFoundError", (Exception,), {})

        # Default: verify_id_token returns a valid decoded payload
        mock_auth.verify_id_token.return_value = {
            "uid": "test-uid-001",
            "email": "test@example.com",
            "name": "Test User",
        }
        yield mock_auth


@pytest.fixture()
def test_client(mock_firebase_app) -> Generator[TestClient, None, None]:
    """Provide a TestClient **without** an Authorization header."""
    from app.main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def mock_auth_token() -> str:
    """A fake JWT-like Bearer token string for testing."""
    return "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.FAKE_TEST_TOKEN"


@pytest.fixture()
def auth_headers(mock_auth_token) -> dict:
    """Ready-to-use Authorization header dict."""
    return {"Authorization": f"Bearer {mock_auth_token}"}


@pytest.fixture()
def client_with_auth(test_client, auth_headers) -> TestClient:
    """TestClient with the default Bearer header set on every request.

    Usage:  resp = client_with_auth.get("/eeg/files", headers=auth_headers)
    Note: You still need to pass ``headers=auth_headers`` explicitly because
    ``TestClient`` does not support sticky headers.  This fixture is mostly
    a convenience alias returned alongside ``auth_headers``.
    """
    return test_client


@pytest.fixture()
def test_user_data() -> dict:
    """Sample user payload for signup / login tests."""
    return {
        "email": "test@example.com",
        "password": "StrongPassword123!",
        "name": "Test User",
    }


@pytest.fixture()
def test_user_info() -> dict:
    """The decoded token / user info dict returned by ``get_current_user``."""
    return {
        "uid": "test-uid-001",
        "email": "test@example.com",
        "name": "Test User",
    }


@pytest.fixture()
def sample_eeg_file_bytes() -> bytes:
    """Minimal fake EDF-like binary data (not a real EDF, for upload tests)."""
    # A real EDF header starts with "0       " (8 bytes) — enough for extension checks
    return b"0       " + b"\x00" * 248  # 256-byte minimal header stub


@pytest.fixture()
def sample_file_metadata() -> dict:
    """Sample EEG file metadata as returned by Firestore."""
    return {
        "file_id": "abc123def456",
        "filename": "abc123def456.edf",
        "original_filename": "recording.edf",
        "file_size": 1024000,
        "upload_date": datetime.now(timezone.utc),
        "processing_status": "uploaded",
        "file_path": "./uploads/abc123def456.edf",
    }


@pytest.fixture()
def sample_prediction_data() -> dict:
    """Sample prediction record as stored in Firestore."""
    return {
        "prediction_id": "pred-" + uuid.uuid4().hex[:8],
        "file_id": "abc123def456",
        "depression_probability": 0.6234,
        "risk_level": "medium",
        "confidence": 0.2468,
        "timestamp": datetime.now(timezone.utc),
        "created_at": datetime.now(timezone.utc),
        "shap_explanation": {
            "feature_importance": {"Fp1": {"abs_importance": 0.05, "signed_importance": 0.03}},
            "top_features": ["Fp1", "F3", "Cz", "P3", "O1"],
            "base_value": 0.6234,
            "explanation_summary": "The model predicts a medium risk of depression.",
            "shap_status": "success",
        },
        "model_version": "1.0.0",
    }
