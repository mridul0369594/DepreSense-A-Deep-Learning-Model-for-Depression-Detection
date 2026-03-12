"""
Tests for authentication endpoints:  /auth/signup, /auth/login, /auth/me, /auth/logout
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# ── Signup ──────────────────────────────────────────────────


class TestSignup:
    """POST /auth/signup"""

    @patch("app.routes.auth.firestore_service")
    @patch("app.routes.auth._firebase_rest_auth")
    @patch("app.routes.auth.auth_client")
    def test_signup_success(self, mock_auth, mock_rest, mock_fs, test_client, test_user_data):
        rec = MagicMock()
        rec.uid = "new-uid-001"
        rec.email = test_user_data["email"]
        rec.display_name = test_user_data["name"]
        mock_auth.create_user.return_value = rec
        mock_rest.return_value = {"idToken": "new-id-token"}

        resp = test_client.post("/auth/signup", json=test_user_data)
        assert resp.status_code == 201
        data = resp.json()
        assert "token" in data
        assert data["user"]["uid"] == "new-uid-001"
        assert data["user"]["email"] == test_user_data["email"]
        assert data["message"] == "Account created successfully"

    @patch("app.routes.auth.auth_client")
    def test_signup_duplicate_email(self, mock_auth, test_client, test_user_data):
        mock_auth.EmailAlreadyExistsError = type("EmailAlreadyExistsError", (Exception,), {})
        mock_auth.create_user.side_effect = mock_auth.EmailAlreadyExistsError()

        resp = test_client.post("/auth/signup", json=test_user_data)
        assert resp.status_code == 409
        assert resp.json()["detail"]["code"] == "EMAIL_EXISTS"

    def test_signup_invalid_email(self, test_client):
        resp = test_client.post("/auth/signup", json={
            "email": "not-an-email",
            "password": "StrongPassword123!",
            "name": "Test",
        })
        assert resp.status_code == 422  # pydantic EmailStr validation

    def test_signup_weak_password(self, test_client):
        resp = test_client.post("/auth/signup", json={
            "email": "test@example.com",
            "password": "short",  # min_length=6
            "name": "Test",
        })
        assert resp.status_code == 422

    def test_signup_missing_fields(self, test_client):
        resp = test_client.post("/auth/signup", json={"email": "a@b.com"})
        assert resp.status_code == 422


# ── Login ──────────────────────────────────────────────────


class TestLogin:
    """POST /auth/login"""

    @patch("app.routes.auth.firestore_service")
    @patch("app.routes.auth._firebase_rest_auth")
    @patch("app.routes.auth.auth_client")
    def test_login_success(self, mock_auth, mock_rest, mock_fs, test_client, test_user_data):
        mock_rest.return_value = {"idToken": "login-token"}
        rec = MagicMock()
        rec.uid = "uid-001"
        rec.email = test_user_data["email"]
        rec.display_name = test_user_data["name"]
        mock_auth.get_user_by_email.return_value = rec

        resp = test_client.post("/auth/login", json={
            "email": test_user_data["email"],
            "password": test_user_data["password"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["token"] == "login-token"
        assert data["user"]["uid"] == "uid-001"
        assert data["message"] == "Login successful"

    @patch("app.routes.auth._firebase_rest_auth")
    def test_login_invalid_password(self, mock_rest, test_client, test_user_data):
        from fastapi import HTTPException
        mock_rest.side_effect = HTTPException(401, detail={"code": "AUTH_FAILED", "message": "INVALID_PASSWORD"})

        resp = test_client.post("/auth/login", json={
            "email": test_user_data["email"],
            "password": "wrong-password",
        })
        assert resp.status_code == 401

    @patch("app.routes.auth._firebase_rest_auth")
    @patch("app.routes.auth.auth_client")
    def test_login_user_not_found(self, mock_auth, mock_rest, test_client):
        mock_auth.UserNotFoundError = type("UserNotFoundError", (Exception,), {})
        mock_rest.return_value = {"idToken": "t"}
        mock_auth.get_user_by_email.side_effect = mock_auth.UserNotFoundError()

        resp = test_client.post("/auth/login", json={
            "email": "nobody@example.com",
            "password": "anything123",
        })
        assert resp.status_code == 404
        assert resp.json()["detail"]["code"] == "USER_NOT_FOUND"

    def test_login_missing_credentials(self, test_client):
        resp = test_client.post("/auth/login", json={})
        assert resp.status_code == 422


# ── GET /auth/me ───────────────────────────────────────────


class TestGetMe:
    """GET /auth/me"""

    @patch("app.routes.auth.auth_client")
    @patch("app.routes.auth.firestore_service")
    def test_get_me_authenticated(self, mock_fs, mock_auth, test_client, auth_headers):
        mock_fs.get_user.return_value = {
            "uid": "test-uid-001",
            "email": "test@example.com",
            "name": "Test User",
            "created_at": None,
        }
        resp = test_client.get("/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["uid"] == "test-uid-001"
        assert data["email"] == "test@example.com"

    def test_get_me_unauthenticated(self, test_client):
        resp = test_client.get("/auth/me")
        assert resp.status_code == 401

    def test_get_me_invalid_token(self, test_client, mock_firebase_app):
        mock_firebase_app.verify_id_token.side_effect = mock_firebase_app.InvalidIdTokenError()
        resp = test_client.get("/auth/me", headers={"Authorization": "Bearer bad-token"})
        assert resp.status_code == 401
        # Reset
        mock_firebase_app.verify_id_token.side_effect = None
        mock_firebase_app.verify_id_token.return_value = {
            "uid": "test-uid-001", "email": "test@example.com", "name": "Test User"
        }

    def test_get_me_expired_token(self, test_client, mock_firebase_app):
        mock_firebase_app.verify_id_token.side_effect = mock_firebase_app.ExpiredIdTokenError()
        resp = test_client.get("/auth/me", headers={"Authorization": "Bearer expired-token"})
        assert resp.status_code == 401
        assert resp.json()["detail"]["code"] == "TOKEN_EXPIRED"
        # Reset
        mock_firebase_app.verify_id_token.side_effect = None
        mock_firebase_app.verify_id_token.return_value = {
            "uid": "test-uid-001", "email": "test@example.com", "name": "Test User"
        }


# ── Logout ─────────────────────────────────────────────────


class TestLogout:
    """POST /auth/logout"""

    @patch("app.routes.auth.auth_client")
    def test_logout_success(self, mock_auth, test_client, auth_headers):
        mock_auth.revoke_refresh_tokens.return_value = None
        resp = test_client.post("/auth/logout", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["message"] == "Logged out successfully"

    def test_logout_unauthenticated(self, test_client):
        resp = test_client.post("/auth/logout")
        assert resp.status_code == 401
