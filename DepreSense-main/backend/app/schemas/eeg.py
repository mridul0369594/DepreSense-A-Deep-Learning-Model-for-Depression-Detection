"""
Pydantic models for EEG file upload and metadata.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Response Models ────────────────────────────────────────


class EEGUploadResponse(BaseModel):
    """Returned after a successful .edf file upload."""

    file_id: str = Field(..., description="Unique identifier for the uploaded file")
    filename: str = Field(..., description="Stored filename on disk")
    status: str = Field("uploaded", description="Current processing status")
    message: str = Field("File uploaded successfully", description="Status message")
    uploaded_at: datetime = Field(..., description="Upload timestamp")


class EEGFileInfo(BaseModel):
    """Metadata about a stored EEG file."""

    file_id: str = Field(..., description="Unique file identifier")
    filename: str = Field(..., description="Stored filename on disk")
    original_filename: str = Field(..., description="Original filename from client")
    file_size: int = Field(..., description="File size in bytes")
    upload_date: datetime = Field(..., description="When the file was uploaded")
    processing_status: str = Field(
        "uploaded",
        description="Processing status: uploaded | processing | completed | failed",
    )
