"""
File-handling utilities for EEG uploads.

Covers unique ID generation, saving / deleting uploaded files, and
basic extension / size validation.
"""

from __future__ import annotations

import logging
import os
import shutil
import uuid
from pathlib import Path

from fastapi import UploadFile

logger = logging.getLogger(__name__)


def generate_unique_file_id() -> str:
    """Return a new UUID4 hex string to use as a file identifier."""
    return uuid.uuid4().hex


def validate_file_extension(filename: str) -> bool:
    """Return ``True`` if *filename* ends with ``.edf`` (case-insensitive)."""
    return Path(filename).suffix.lower() == ".edf"


def validate_file_size(file_size: int, max_size_mb: int) -> bool:
    """Return ``True`` if *file_size* (bytes) is within *max_size_mb*."""
    return file_size <= max_size_mb * 1024 * 1024


def get_file_path(file_id: str, upload_dir: str) -> str:
    """Construct the full path for a stored file given its *file_id*."""
    return str(Path(upload_dir) / f"{file_id}.edf")


async def save_uploaded_file(
    file: UploadFile, upload_dir: str
) -> tuple[str, str]:
    """Save an ``UploadFile`` to *upload_dir*.

    Returns:
        ``(file_id, file_path)`` — the generated unique ID and saved path.
    """
    file_id = generate_unique_file_id()
    upload_path = Path(upload_dir)
    upload_path.mkdir(parents=True, exist_ok=True)

    file_path = get_file_path(file_id, upload_dir)

    try:
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        logger.info("Saved upload %s → %s", file_id, file_path)
        return file_id, file_path
    except Exception as exc:
        logger.error("Failed to save file %s: %s", file_id, exc)
        # Clean up partial write if it exists
        if os.path.exists(file_path):
            os.remove(file_path)
        raise


def delete_file(file_path: str) -> bool:
    """Delete the file at *file_path*. Returns ``True`` on success."""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info("Deleted file: %s", file_path)
            return True
        logger.warning("File not found for deletion: %s", file_path)
        return False
    except Exception as exc:
        logger.error("Failed to delete file %s: %s", file_path, exc)
        return False
