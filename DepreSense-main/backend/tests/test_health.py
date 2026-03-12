"""
Tests for health-check endpoints:  /health, /health/model, /health/firebase
"""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest


class TestHealthCheck:
    """GET /health"""

    def test_health_status(self, test_client):
        resp = test_client.get("/health")
        assert resp.status_code == 200

    def test_health_response_format(self, test_client):
        data = test_client.get("/health").json()
        assert "status" in data
        assert "version" in data

    def test_health_response_value(self, test_client):
        data = test_client.get("/health").json()
        assert data["status"] == "ok"
        assert data["version"] == "1.0.0"

    def test_health_response_time(self, test_client):
        start = time.perf_counter()
        test_client.get("/health")
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 500  # generous bound — should be <10 ms


class TestModelHealth:
    """GET /health/model"""

    @patch("app.routes.health.is_model_loaded", return_value=True)
    def test_model_loaded_true(self, mock_loaded, test_client):
        resp = test_client.get("/health/model")
        assert resp.status_code == 200
        assert resp.json()["model_loaded"] is True

    @patch("app.routes.health.is_model_loaded", return_value=False)
    def test_model_loaded_false(self, mock_loaded, test_client):
        resp = test_client.get("/health/model")
        assert resp.status_code == 200
        assert resp.json()["model_loaded"] is False


class TestFirebaseHealth:
    """GET /health/firebase"""

    @patch("app.routes.health.check_firebase_connection", return_value=True)
    def test_firebase_connected_true(self, mock_conn, test_client):
        resp = test_client.get("/health/firebase")
        assert resp.status_code == 200
        assert resp.json()["firebase_connected"] is True

    @patch("app.routes.health.check_firebase_connection", return_value=False)
    def test_firebase_connected_false(self, mock_conn, test_client):
        resp = test_client.get("/health/firebase")
        assert resp.status_code == 200
        assert resp.json()["firebase_connected"] is False
