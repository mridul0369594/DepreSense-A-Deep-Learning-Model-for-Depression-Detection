"""
EEG file upload, listing, info, and deletion endpoints.

All endpoints require authentication via Firebase ID token.
File metadata is persisted to Firestore.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.config import settings
from app.middleware.auth_middleware import get_current_user
from app.schemas.eeg import EEGFileInfo, EEGUploadResponse
from app.services import firestore_service
from app.services.eeg_processor import validate_edf_file
from app.utils.file_handler import (
    delete_file,
    get_file_path,
    save_uploaded_file,
    validate_file_extension,
    validate_file_size,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/eeg", tags=["EEG"])


# ── POST /eeg/upload ───────────────────────────────────────


@router.post(
    "/upload",
    response_model=EEGUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_eeg_file(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    """Upload a .edf EEG file.

    Validates the extension and size, saves to disk, and persists
    metadata to Firestore.
    """
    # 1. Validate file extension
    if not validate_file_extension(file.filename or ""):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_FILE_TYPE",
                "message": "Only .edf files are accepted.",
            },
        )

    # 2. Read content to check size (seek back afterwards)
    content = await file.read()
    file_size = len(content)
    await file.seek(0)  # rewind so save_uploaded_file can read again

    if not validate_file_size(file_size, settings.MAX_FILE_SIZE_MB):
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "code": "FILE_TOO_LARGE",
                "message": f"File exceeds the {settings.MAX_FILE_SIZE_MB} MB limit.",
            },
        )

    # 3. Save to disk
    try:
        file_id, file_path = await save_uploaded_file(file, settings.UPLOAD_DIR)
    except Exception as exc:
        logger.error("Upload save failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "UPLOAD_FAILED",
                "message": "Failed to save uploaded file.",
            },
        )

    # 4. Validate EDF content
    if not validate_edf_file(file_path):
        # Clean up invalid file
        delete_file(file_path)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_EDF",
                "message": "The uploaded file is not a valid EDF recording.",
            },
        )

    # 5. Persist metadata to Firestore
    now = datetime.now(timezone.utc)
    file_info = {
        "filename": f"{file_id}.edf",
        "original_filename": file.filename or "unknown.edf",
        "file_size": file_size,
        "upload_date": now,
        "processing_status": "uploaded",
        "file_path": file_path,
    }

    try:
        firestore_service.save_eeg_file_metadata(
            uid=user["uid"], file_id=file_id, file_info=file_info
        )
    except Exception as exc:
        logger.warning("Firestore metadata save failed (non-blocking): %s", exc)

    return EEGUploadResponse(
        file_id=file_id,
        filename=f"{file_id}.edf",
        status="uploaded",
        message="File uploaded successfully",
        uploaded_at=now,
    )


# ── GET /eeg/files ─────────────────────────────────────────


@router.get("/files", response_model=list[EEGFileInfo])
async def list_files(user: dict = Depends(get_current_user)):
    """Return all EEG files uploaded by the authenticated user."""
    files = firestore_service.get_all_eeg_files(user["uid"])

    # Fallback: if Firestore returns nothing, scan the uploads directory
    if not files:
        import os
        from pathlib import Path

        upload_path = Path(settings.UPLOAD_DIR)
        if upload_path.exists():
            for edf in upload_path.glob("*.edf"):
                stat = edf.stat()
                files.append({
                    "file_id": edf.stem,
                    "filename": edf.name,
                    "original_filename": edf.name,
                    "file_size": stat.st_size,
                    "upload_date": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
                    "processing_status": "uploaded",
                })

    return [
        EEGFileInfo(
            file_id=f.get("file_id", ""),
            filename=f.get("filename", ""),
            original_filename=f.get("original_filename", ""),
            file_size=f.get("file_size", 0),
            upload_date=f.get("upload_date", datetime.now(timezone.utc)),
            processing_status=f.get("processing_status", "uploaded"),
        )
        for f in files
    ]


# ── GET /eeg/files/{file_id} ──────────────────────────────


@router.get("/files/{file_id}", response_model=EEGFileInfo)
async def get_file_info(
    file_id: str,
    user: dict = Depends(get_current_user),
):
    """Return metadata for a specific uploaded file from Firestore."""
    meta = firestore_service.get_eeg_file(user["uid"], file_id)

    if meta is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "FILE_NOT_FOUND",
                "message": "File not found or access denied.",
            },
        )

    return EEGFileInfo(
        file_id=meta.get("file_id", file_id),
        filename=meta.get("filename", ""),
        original_filename=meta.get("original_filename", ""),
        file_size=meta.get("file_size", 0),
        upload_date=meta.get("upload_date", datetime.now(timezone.utc)),
        processing_status=meta.get("processing_status", "uploaded"),
    )


# ── DELETE /eeg/files/{file_id} ───────────────────────────


@router.delete("/files/{file_id}", status_code=status.HTTP_200_OK)
async def delete_eeg_file(
    file_id: str,
    user: dict = Depends(get_current_user),
):
    """Delete an uploaded EEG file from disk and Firestore."""
    # Check file exists in Firestore
    meta = firestore_service.get_eeg_file(user["uid"], file_id)

    if meta is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "FILE_NOT_FOUND",
                "message": "File not found or access denied.",
            },
        )

    # Delete from disk
    file_path = meta.get("file_path") or get_file_path(file_id, settings.UPLOAD_DIR)
    delete_file(file_path)

    # Delete from Firestore
    firestore_service.delete_eeg_file_metadata(user["uid"], file_id)

    return {"message": "File deleted successfully"}
