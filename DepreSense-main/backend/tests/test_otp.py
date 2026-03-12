"""
Unit tests for the OTP service.

Covers:
  - OTP generation format
  - OTP storage / retrieval
  - OTP verification (success, wrong code, expiry, max attempts)
  - OTP deletion
  - Email sending (mocked SMTP)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.services import otp_service


# ── generate_otp ──────────────────────────────────────────


class TestGenerateOTP:
    """Tests for the OTP generator."""

    def test_returns_six_digit_string(self):
        otp = otp_service.generate_otp()
        assert len(otp) == 6
        assert otp.isdigit()

    def test_zero_padded(self):
        """Even very small numbers should still be 6 chars."""
        with patch("secrets.randbelow", return_value=42):
            assert otp_service.generate_otp() == "000042"

    def test_uniqueness(self):
        """Generate a batch and check for reasonable uniqueness."""
        codes = {otp_service.generate_otp() for _ in range(50)}
        # With 1M possible codes, 50 should be nearly all unique
        assert len(codes) >= 45


# ── store_otp / verify_otp / delete_otp (Firestore mocked) ─


@pytest.fixture()
def mock_db():
    """Patch ``otp_service.db_client`` with an in-memory mock."""
    _store: dict[str, dict] = {}

    mock_collection = MagicMock()

    def _document(email: str):
        doc = MagicMock()

        # .set()
        def _set(data: dict):
            _store[email] = dict(data)

        doc.set = _set

        # .get()
        def _get():
            snap = MagicMock()
            if email in _store:
                snap.exists = True
                snap.to_dict = lambda: dict(_store[email])
            else:
                snap.exists = False
                snap.to_dict = lambda: None
            return snap

        doc.get = _get

        # .update()
        def _update(updates: dict):
            if email in _store:
                _store[email].update(updates)

        doc.update = _update

        # .delete()
        def _delete():
            _store.pop(email, None)

        doc.delete = _delete
        return doc

    mock_collection.document = _document

    mock_client = MagicMock()
    mock_client.collection.return_value = mock_collection

    with patch.object(otp_service, "db_client", mock_client):
        yield _store


class TestStoreAndVerify:
    """Integration-like tests for store → verify → delete cycle."""

    def test_store_creates_record(self, mock_db):
        assert otp_service.store_otp("a@b.com", "123456")
        assert "a@b.com" in mock_db
        assert mock_db["a@b.com"]["code"] == "123456"
        assert mock_db["a@b.com"]["verified"] is False

    def test_verify_success(self, mock_db):
        otp_service.store_otp("a@b.com", "654321")
        result = otp_service.verify_otp("a@b.com", "654321")
        assert result["success"] is True

    def test_verify_wrong_code(self, mock_db):
        otp_service.store_otp("a@b.com", "111111")
        result = otp_service.verify_otp("a@b.com", "999999")
        assert result["success"] is False
        assert "attempt" in result["message"].lower() or "incorrect" in result["message"].lower()

    def test_verify_no_record(self, mock_db):
        result = otp_service.verify_otp("nobody@x.com", "000000")
        assert result["success"] is False
        assert "no verification" in result["message"].lower() or "not found" in result["message"].lower()

    def test_verify_expired(self, mock_db):
        otp_service.store_otp("a@b.com", "123456", expiry_minutes=0)
        # Manually set expiry in the past
        mock_db["a@b.com"]["expires_at"] = datetime.now(timezone.utc) - timedelta(seconds=10)
        result = otp_service.verify_otp("a@b.com", "123456")
        assert result["success"] is False
        assert "expired" in result["message"].lower()

    def test_verify_max_attempts(self, mock_db):
        otp_service.store_otp("a@b.com", "123456")

        # Exhaust attempts with wrong code
        for _ in range(3):
            otp_service.verify_otp("a@b.com", "000000")

        # Even with correct code, should be locked out
        result = otp_service.verify_otp("a@b.com", "123456")
        assert result["success"] is False
        assert "too many" in result["message"].lower()

    def test_delete_otp(self, mock_db):
        otp_service.store_otp("a@b.com", "123456")
        assert otp_service.delete_otp("a@b.com") is True
        assert "a@b.com" not in mock_db

    def test_delete_nonexistent(self, mock_db):
        # Should not raise
        assert otp_service.delete_otp("ghost@x.com") is True


# ── send_otp_email (SMTP mocked) ─────────────────────────


class TestSendOTPEmail:
    """Test the email dispatch with mocked SMTP."""

    @patch.dict("os.environ", {
        "SMTP_EMAIL": "test@gmail.com",
        "SMTP_PASSWORD": "app-password",
        "SMTP_SERVER": "smtp.gmail.com",
        "SMTP_PORT": "465",
    })
    @patch("smtplib.SMTP_SSL")
    def test_send_success(self, mock_smtp_cls):
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = lambda self: mock_server
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        result = otp_service.send_otp_email("user@example.com", "123456")
        assert result is True
        mock_server.login.assert_called_once_with("test@gmail.com", "app-password")
        mock_server.sendmail.assert_called_once()

    @patch.dict("os.environ", {"SMTP_EMAIL": "", "SMTP_PASSWORD": ""})
    def test_send_missing_credentials(self):
        result = otp_service.send_otp_email("user@example.com", "123456")
        assert result is False

    @patch.dict("os.environ", {
        "SMTP_EMAIL": "test@gmail.com",
        "SMTP_PASSWORD": "app-password",
    })
    @patch("smtplib.SMTP_SSL", side_effect=Exception("connection refused"))
    def test_send_smtp_error(self, _):
        result = otp_service.send_otp_email("user@example.com", "123456")
        assert result is False


# ── db_client is None guard ──────────────────────────────


class TestNullDbClient:
    """Ensure functions handle db_client being None gracefully."""

    def test_store_returns_false(self):
        with patch.object(otp_service, "db_client", None):
            assert otp_service.store_otp("a@b.com", "123456") is False

    def test_verify_returns_failure(self):
        with patch.object(otp_service, "db_client", None):
            result = otp_service.verify_otp("a@b.com", "123456")
            assert result["success"] is False

    def test_delete_returns_false(self):
        with patch.object(otp_service, "db_client", None):
            assert otp_service.delete_otp("a@b.com") is False
