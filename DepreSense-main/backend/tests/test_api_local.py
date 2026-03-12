"""
Smoke tests — verify the backend is running and responding correctly.

Run with:
    pytest tests/test_api_local.py -v
"""

from __future__ import annotations


# ── Health ─────────────────────────────────────────────────


def test_root(test_client):
    """GET / returns 200 with status ok."""
    resp = test_client.get("/")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_health_check(test_client):
    """GET /health returns 200 with status ok."""
    resp = test_client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_health_model(test_client):
    """GET /health/model reports model_loaded flag."""
    resp = test_client.get("/health/model")
    assert resp.status_code == 200
    assert "model_loaded" in resp.json()


def test_health_firebase(test_client):
    """GET /health/firebase reports firebase_connected flag."""
    resp = test_client.get("/health/firebase")
    assert resp.status_code == 200
    assert "firebase_connected" in resp.json()


# ── CORS ───────────────────────────────────────────────────


def test_cors_headers(test_client):
    """Preflight OPTIONS response includes CORS headers for localhost."""
    resp = test_client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    # FastAPI CORSMiddleware returns 200 on preflight
    assert resp.status_code == 200
    assert "access-control-allow-origin" in resp.headers


# ── Auth-protected endpoints require token ─────────────────


def test_auth_me_requires_token(test_client):
    """GET /auth/me without token returns 401."""
    resp = test_client.get("/auth/me")
    assert resp.status_code == 401


def test_eeg_files_requires_token(test_client):
    """GET /eeg/files without token returns 401."""
    resp = test_client.get("/eeg/files")
    assert resp.status_code == 401


def test_predictions_history_requires_token(test_client):
    """GET /predictions/history without token returns 401."""
    resp = test_client.get("/predictions/history")
    assert resp.status_code == 401


# ── Request tracking ───────────────────────────────────────


def test_request_id_header(test_client):
    """Every response should include an X-Request-ID header (UUID hex)."""
    resp = test_client.get("/health")
    rid = resp.headers.get("x-request-id")
    assert rid is not None
    assert len(rid) == 32  # UUID4 hex = 32 chars


# ── API info ───────────────────────────────────────────────


def test_openapi_available(test_client):
    """OpenAPI JSON schema is served at /openapi.json."""
    resp = test_client.get("/openapi.json")
    assert resp.status_code == 200
    data = resp.json()
    assert data["info"]["title"] == "DepreSense API"

