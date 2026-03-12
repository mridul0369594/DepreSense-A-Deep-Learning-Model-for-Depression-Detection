"""
Tests for EEG file endpoints:  /eeg/upload, /eeg/files, /eeg/files/{id}, DELETE /eeg/files/{id}
"""

from __future__ import annotations

import io
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest


# ── Upload ──────────────────────────────────────────────────


class TestUploadEEG:
    """POST /eeg/upload"""

    @patch("app.routes.eeg.firestore_service")
    @patch("app.routes.eeg.validate_edf_file", return_value=True)
    @patch("app.routes.eeg.save_uploaded_file")
    def test_upload_edf_success(self, mock_save, mock_validate, mock_fs, test_client, auth_headers):
        mock_save.return_value = ("file-id-001", "./uploads/file-id-001.edf")
        files = {"file": ("recording.edf", b"\x00" * 256, "application/octet-stream")}
        resp = test_client.post("/eeg/upload", files=files, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["file_id"] == "file-id-001"
        assert data["status"] == "uploaded"
        assert "uploaded_at" in data

    @patch("app.routes.eeg.firestore_service")
    @patch("app.routes.eeg.validate_edf_file", return_value=True)
    @patch("app.routes.eeg.save_uploaded_file")
    def test_upload_saves_metadata_to_firestore(self, mock_save, mock_validate, mock_fs, test_client, auth_headers):
        mock_save.return_value = ("fid", "./uploads/fid.edf")
        files = {"file": ("test.edf", b"\x00" * 100, "application/octet-stream")}
        test_client.post("/eeg/upload", files=files, headers=auth_headers)
        mock_fs.save_eeg_file_metadata.assert_called_once()

    def test_upload_invalid_format(self, test_client, auth_headers):
        files = {"file": ("data.csv", b"col1,col2\n1,2", "text/csv")}
        resp = test_client.post("/eeg/upload", files=files, headers=auth_headers)
        assert resp.status_code == 400
        assert resp.json()["detail"]["code"] == "INVALID_FILE_TYPE"

    @patch("app.routes.eeg.validate_file_size", return_value=False)
    def test_upload_file_too_large(self, mock_size, test_client, auth_headers):
        files = {"file": ("big.edf", b"\x00" * 1000, "application/octet-stream")}
        resp = test_client.post("/eeg/upload", files=files, headers=auth_headers)
        assert resp.status_code == 413
        assert resp.json()["detail"]["code"] == "FILE_TOO_LARGE"

    def test_upload_unauthenticated(self, test_client):
        files = {"file": ("test.edf", b"\x00" * 100, "application/octet-stream")}
        resp = test_client.post("/eeg/upload", files=files)
        assert resp.status_code == 401

    @patch("app.routes.eeg.firestore_service")
    @patch("app.routes.eeg.validate_edf_file", return_value=False)
    @patch("app.routes.eeg.save_uploaded_file")
    @patch("app.routes.eeg.delete_file")
    def test_upload_corrupted_edf(self, mock_del, mock_save, mock_validate, mock_fs, test_client, auth_headers):
        mock_save.return_value = ("fid", "./uploads/fid.edf")
        files = {"file": ("bad.edf", b"\xff" * 100, "application/octet-stream")}
        resp = test_client.post("/eeg/upload", files=files, headers=auth_headers)
        assert resp.status_code == 400
        assert resp.json()["detail"]["code"] == "INVALID_EDF"
        mock_del.assert_called_once()  # Clean up invalid file


# ── List Files ──────────────────────────────────────────────


class TestListEEGFiles:
    """GET /eeg/files"""

    @patch("app.routes.eeg.firestore_service")
    def test_get_files_authenticated(self, mock_fs, test_client, auth_headers, sample_file_metadata):
        mock_fs.get_all_eeg_files.return_value = [sample_file_metadata]
        resp = test_client.get("/eeg/files", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["file_id"] == sample_file_metadata["file_id"]

    @patch("app.routes.eeg.settings")
    @patch("app.routes.eeg.firestore_service")
    def test_get_files_empty_list(self, mock_fs, mock_settings, test_client, auth_headers):
        mock_fs.get_all_eeg_files.return_value = []
        mock_settings.UPLOAD_DIR = "./_test_empty_uploads_"
        resp = test_client.get("/eeg/files", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_files_unauthenticated(self, test_client):
        resp = test_client.get("/eeg/files")
        assert resp.status_code == 401


# ── Get File by ID ──────────────────────────────────────────


class TestGetFileById:
    """GET /eeg/files/{file_id}"""

    @patch("app.routes.eeg.firestore_service")
    def test_get_file_by_id_success(self, mock_fs, test_client, auth_headers, sample_file_metadata):
        mock_fs.get_eeg_file.return_value = sample_file_metadata
        resp = test_client.get(f"/eeg/files/{sample_file_metadata['file_id']}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["file_id"] == sample_file_metadata["file_id"]

    @patch("app.routes.eeg.firestore_service")
    def test_get_file_by_id_not_found(self, mock_fs, test_client, auth_headers):
        mock_fs.get_eeg_file.return_value = None
        resp = test_client.get("/eeg/files/nonexistent-id", headers=auth_headers)
        assert resp.status_code == 404
        assert resp.json()["detail"]["code"] == "FILE_NOT_FOUND"

    def test_get_file_by_id_unauthenticated(self, test_client):
        resp = test_client.get("/eeg/files/some-id")
        assert resp.status_code == 401


# ── Delete File ─────────────────────────────────────────────


class TestDeleteFile:
    """DELETE /eeg/files/{file_id}"""

    @patch("app.routes.eeg.firestore_service")
    @patch("app.routes.eeg.delete_file", return_value=True)
    def test_delete_file_success(self, mock_del, mock_fs, test_client, auth_headers, sample_file_metadata):
        mock_fs.get_eeg_file.return_value = sample_file_metadata
        resp = test_client.delete(f"/eeg/files/{sample_file_metadata['file_id']}", headers=auth_headers)
        assert resp.status_code == 200
        assert "deleted" in resp.json()["message"].lower()
        mock_fs.delete_eeg_file_metadata.assert_called_once()

    @patch("app.routes.eeg.firestore_service")
    def test_delete_file_not_found(self, mock_fs, test_client, auth_headers):
        mock_fs.get_eeg_file.return_value = None
        resp = test_client.delete("/eeg/files/nonexistent-id", headers=auth_headers)
        assert resp.status_code == 404

    def test_delete_file_unauthenticated(self, test_client):
        resp = test_client.delete("/eeg/files/some-id")
        assert resp.status_code == 401
