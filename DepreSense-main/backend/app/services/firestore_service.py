"""
Firestore database service.

Provides CRUD operations for users, EEG file metadata, and predictions
using the Firebase Firestore database.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Optional

from app.utils.firebase_client import db_client
from app.utils.logger import log_database_operation

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ═══════════════════════════════════════════════════════════
#  User Collection  —  users/{uid}
# ═══════════════════════════════════════════════════════════


def create_user_record(uid: str, email: str, name: str) -> dict:
    """Create a new user document in Firestore.

    Collection: ``users``
    """
    start = time.perf_counter()
    try:
        user_data = {
            "uid": uid,
            "email": email,
            "name": name,
            "created_at": _now(),
            "last_login": _now(),
            "profile_picture_url": None,
        }
        db_client.collection("users").document(uid).set(user_data)
        elapsed = (time.perf_counter() - start) * 1000
        log_database_operation("CREATE", "users", "success")
        logger.info("Created Firestore user %s (%.1f ms)", uid, elapsed)
        return user_data
    except Exception as exc:
        log_database_operation("CREATE", "users", "error")
        logger.error("Failed to create user record %s: %s", uid, exc)
        raise


def get_user(uid: str) -> Optional[dict]:
    """Retrieve a user document from Firestore.

    Returns ``None`` if the user does not exist.
    """
    start = time.perf_counter()
    try:
        doc = db_client.collection("users").document(uid).get()
        elapsed = (time.perf_counter() - start) * 1000
        if doc.exists:
            log_database_operation("READ", "users", "found")
            logger.debug("Fetched user %s (%.1f ms)", uid, elapsed)
            return doc.to_dict()
        log_database_operation("READ", "users", "not_found")
        return None
    except Exception as exc:
        log_database_operation("READ", "users", "error")
        logger.error("Failed to get user %s: %s", uid, exc)
        return None


def update_user(uid: str, updates: dict) -> dict:
    """Update specific fields on a user document.

    Returns the merged update data.
    """
    start = time.perf_counter()
    try:
        db_client.collection("users").document(uid).update(updates)
        elapsed = (time.perf_counter() - start) * 1000
        log_database_operation("UPDATE", "users", "success")
        logger.info(
            "Updated user %s fields=%s (%.1f ms)",
            uid, list(updates.keys()), elapsed,
        )
        return updates
    except Exception as exc:
        log_database_operation("UPDATE", "users", "error")
        logger.error("Failed to update user %s: %s", uid, exc)
        raise


# ═══════════════════════════════════════════════════════════
#  EEG Files Collection  —  users/{uid}/eeg_files/{file_id}
# ═══════════════════════════════════════════════════════════


def save_eeg_file_metadata(uid: str, file_id: str, file_info: dict) -> dict:
    """Save uploaded EEG file metadata to Firestore.

    Collection: ``users/{uid}/eeg_files``
    """
    start = time.perf_counter()
    try:
        metadata = {
            "file_id": file_id,
            "original_filename": file_info.get("original_filename", "unknown.edf"),
            "filename": file_info.get("filename", f"{file_id}.edf"),
            "file_size": file_info.get("file_size", 0),
            "upload_date": file_info.get("upload_date", _now()),
            "processing_status": file_info.get("processing_status", "uploaded"),
            "file_path": file_info.get("file_path", ""),
        }
        (
            db_client.collection("users")
            .document(uid)
            .collection("eeg_files")
            .document(file_id)
            .set(metadata)
        )
        elapsed = (time.perf_counter() - start) * 1000
        log_database_operation("CREATE", "eeg_files", "success")
        logger.info(
            "Saved EEG metadata user=%s file=%s (%.1f ms)", uid, file_id, elapsed
        )
        return metadata
    except Exception as exc:
        log_database_operation("CREATE", "eeg_files", "error")
        logger.error("Failed to save EEG metadata %s/%s: %s", uid, file_id, exc)
        raise


def get_eeg_file(uid: str, file_id: str) -> Optional[dict]:
    """Retrieve specific EEG file metadata from Firestore.

    Returns ``None`` if the document does not exist.
    """
    start = time.perf_counter()
    try:
        doc = (
            db_client.collection("users")
            .document(uid)
            .collection("eeg_files")
            .document(file_id)
            .get()
        )
        elapsed = (time.perf_counter() - start) * 1000
        if doc.exists:
            log_database_operation("READ", "eeg_files", "found")
            logger.debug("Fetched EEG file %s/%s (%.1f ms)", uid, file_id, elapsed)
            return doc.to_dict()
        log_database_operation("READ", "eeg_files", "not_found")
        return None
    except Exception as exc:
        log_database_operation("READ", "eeg_files", "error")
        logger.error("Failed to get EEG file %s/%s: %s", uid, file_id, exc)
        return None


def get_all_eeg_files(uid: str) -> list[dict]:
    """Return all EEG file metadata for a user, most recent first."""
    start = time.perf_counter()
    try:
        docs = (
            db_client.collection("users")
            .document(uid)
            .collection("eeg_files")
            .order_by("upload_date", direction="DESCENDING")
            .stream()
        )
        result = [doc.to_dict() for doc in docs]
        elapsed = (time.perf_counter() - start) * 1000
        log_database_operation("LIST", "eeg_files", "success", doc_count=len(result))
        logger.debug("Listed %d EEG files for %s (%.1f ms)", len(result), uid, elapsed)
        return result
    except Exception as exc:
        log_database_operation("LIST", "eeg_files", "error")
        logger.error("Failed to list EEG files for %s: %s", uid, exc)
        return []


def update_eeg_file_status(uid: str, file_id: str, status_val: str) -> dict:
    """Update the processing status of an EEG file.

    Valid statuses: ``uploaded``, ``processing``, ``completed``, ``error``.
    """
    start = time.perf_counter()
    try:
        updates = {"processing_status": status_val}
        (
            db_client.collection("users")
            .document(uid)
            .collection("eeg_files")
            .document(file_id)
            .update(updates)
        )
        elapsed = (time.perf_counter() - start) * 1000
        log_database_operation("UPDATE", "eeg_files", "success")
        logger.info(
            "Updated EEG status %s/%s → %s (%.1f ms)",
            uid, file_id, status_val, elapsed,
        )
        return updates
    except Exception as exc:
        log_database_operation("UPDATE", "eeg_files", "error")
        logger.error("Failed to update EEG status %s/%s: %s", uid, file_id, exc)
        return {"processing_status": status_val}


def delete_eeg_file_metadata(uid: str, file_id: str) -> bool:
    """Delete EEG file metadata from Firestore."""
    start = time.perf_counter()
    try:
        (
            db_client.collection("users")
            .document(uid)
            .collection("eeg_files")
            .document(file_id)
            .delete()
        )
        elapsed = (time.perf_counter() - start) * 1000
        log_database_operation("DELETE", "eeg_files", "success")
        logger.info("Deleted EEG metadata %s/%s (%.1f ms)", uid, file_id, elapsed)
        return True
    except Exception as exc:
        log_database_operation("DELETE", "eeg_files", "error")
        logger.error("Failed to delete EEG metadata %s/%s: %s", uid, file_id, exc)
        return False


# ═══════════════════════════════════════════════════════════
#  Predictions Collection  —  users/{uid}/predictions/{id}
# ═══════════════════════════════════════════════════════════


def save_prediction(uid: str, prediction_data: dict) -> dict:
    """Save a complete prediction result to Firestore.

    Collection: ``users/{uid}/predictions``
    """
    start = time.perf_counter()
    pred_id = prediction_data.get("prediction_id", "")
    try:
        record = {
            "prediction_id": pred_id,
            "file_id": prediction_data.get("file_id", ""),
            "depression_probability": prediction_data.get("depression_probability", 0.0),
            "risk_level": prediction_data.get("risk_level", "unknown"),
            "confidence": prediction_data.get("confidence", 0.0),
            "shap_explanation": prediction_data.get("shap_explanation", {}),
            "created_at": prediction_data.get("timestamp", _now()),
            "model_version": prediction_data.get("model_version", "1.0.0"),
            "processing_time": prediction_data.get("processing_time"),
        }
        (
            db_client.collection("users")
            .document(uid)
            .collection("predictions")
            .document(pred_id)
            .set(record)
        )
        elapsed = (time.perf_counter() - start) * 1000
        log_database_operation("CREATE", "predictions", "success")
        logger.info(
            "Saved prediction %s for user %s (%.1f ms)", pred_id, uid, elapsed
        )
        return record
    except Exception as exc:
        log_database_operation("CREATE", "predictions", "error")
        logger.error("Failed to save prediction %s/%s: %s", uid, pred_id, exc)
        raise


def get_prediction(uid: str, prediction_id: str) -> Optional[dict]:
    """Retrieve a specific prediction from Firestore.

    Returns ``None`` if the document does not exist.
    """
    start = time.perf_counter()
    try:
        doc = (
            db_client.collection("users")
            .document(uid)
            .collection("predictions")
            .document(prediction_id)
            .get()
        )
        elapsed = (time.perf_counter() - start) * 1000
        if doc.exists:
            log_database_operation("READ", "predictions", "found")
            logger.debug(
                "Fetched prediction %s/%s (%.1f ms)", uid, prediction_id, elapsed
            )
            return doc.to_dict()
        log_database_operation("READ", "predictions", "not_found")
        return None
    except Exception as exc:
        log_database_operation("READ", "predictions", "error")
        logger.error("Failed to get prediction %s/%s: %s", uid, prediction_id, exc)
        return None


def get_all_predictions(uid: str, limit: int = 50) -> list[dict]:
    """Return all predictions for a user, most recent first."""
    start = time.perf_counter()
    try:
        docs = (
            db_client.collection("users")
            .document(uid)
            .collection("predictions")
            .order_by("created_at", direction="DESCENDING")
            .limit(limit)
            .stream()
        )
        result = [doc.to_dict() for doc in docs]
        elapsed = (time.perf_counter() - start) * 1000
        log_database_operation("LIST", "predictions", "success", doc_count=len(result))
        logger.debug(
            "Listed %d predictions for %s (%.1f ms)", len(result), uid, elapsed
        )
        return result
    except Exception as exc:
        log_database_operation("LIST", "predictions", "error")
        logger.error("Failed to list predictions for %s: %s", uid, exc)
        return []


def delete_prediction(uid: str, prediction_id: str) -> bool:
    """Delete a prediction from Firestore."""
    start = time.perf_counter()
    try:
        (
            db_client.collection("users")
            .document(uid)
            .collection("predictions")
            .document(prediction_id)
            .delete()
        )
        elapsed = (time.perf_counter() - start) * 1000
        log_database_operation("DELETE", "predictions", "success")
        logger.info(
            "Deleted prediction %s/%s (%.1f ms)", uid, prediction_id, elapsed
        )
        return True
    except Exception as exc:
        log_database_operation("DELETE", "predictions", "error")
        logger.error("Failed to delete prediction %s/%s: %s", uid, prediction_id, exc)
        return False
