"""
Global exception handlers for the FastAPI application.

Defines typed exception classes and registers them with FastAPI so that
every error response follows a consistent JSON shape:

    {
        "error": {
            "code": "ERROR_CODE",
            "message": "Human-readable message",
            "status_code": 400,
            "timestamp": "2026-02-25T22:54:00Z"
        }
    }

Sensitive details (stack traces, internal paths) are never exposed to
the client — they are only written to the server log.
"""

from __future__ import annotations

import logging
import traceback
from datetime import datetime, timezone

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
#  Custom exception classes
# ═══════════════════════════════════════════════════════════


class AppException(Exception):
    """Base application exception that carries a code and HTTP status."""

    def __init__(
        self,
        code: str = "APP_ERROR",
        message: str = "An application error occurred.",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class InvalidFileFormatError(AppException):
    def __init__(self, message: str = "Only .edf files are supported."):
        super().__init__("INVALID_FILE_FORMAT", message, status.HTTP_400_BAD_REQUEST)


class FileTooLargeError(AppException):
    def __init__(self, message: str = "The uploaded file exceeds the size limit."):
        super().__init__("FILE_TOO_LARGE", message, status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)


class FileNotFoundAppError(AppException):
    def __init__(self, message: str = "The requested file was not found."):
        super().__init__("FILE_NOT_FOUND", message, status.HTTP_404_NOT_FOUND)


class UnauthorizedError(AppException):
    def __init__(self, message: str = "Authentication is required."):
        super().__init__("UNAUTHORIZED", message, status.HTTP_401_UNAUTHORIZED)


class ForbiddenError(AppException):
    def __init__(self, message: str = "You do not have permission to perform this action."):
        super().__init__("FORBIDDEN", message, status.HTTP_403_FORBIDDEN)


class ModelNotLoadedError(AppException):
    def __init__(self, message: str = "The ML model is not loaded. Please try again later."):
        super().__init__("MODEL_NOT_LOADED", message, status.HTTP_503_SERVICE_UNAVAILABLE)


class InferenceError(AppException):
    def __init__(self, message: str = "Model inference failed."):
        super().__init__("INFERENCE_ERROR", message, status.HTTP_500_INTERNAL_SERVER_ERROR)


class InvalidPredictionIdError(AppException):
    def __init__(self, message: str = "The prediction ID is invalid or not found."):
        super().__init__("INVALID_PREDICTION_ID", message, status.HTTP_400_BAD_REQUEST)


class FirestoreError(AppException):
    def __init__(self, message: str = "A database error occurred."):
        super().__init__("FIRESTORE_ERROR", message, status.HTTP_500_INTERNAL_SERVER_ERROR)


class InvalidEdfFileError(AppException):
    def __init__(self, message: str = "The uploaded file is not a valid EDF recording."):
        super().__init__("INVALID_EDF_FILE", message, status.HTTP_400_BAD_REQUEST)


class PreprocessingError(AppException):
    def __init__(self, message: str = "EEG preprocessing failed."):
        super().__init__("PREPROCESSING_ERROR", message, status.HTTP_500_INTERNAL_SERVER_ERROR)


class AuthenticationFailedError(AppException):
    def __init__(self, message: str = "Authentication failed."):
        super().__init__("AUTHENTICATION_FAILED", message, status.HTTP_401_UNAUTHORIZED)


class UserNotFoundError(AppException):
    def __init__(self, message: str = "User not found."):
        super().__init__("USER_NOT_FOUND", message, status.HTTP_404_NOT_FOUND)


# ═══════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════


def _error_response(code: str, message: str, status_code: int) -> JSONResponse:
    """Build a consistent error JSON response."""
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "status_code": status_code,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        },
    )


# ═══════════════════════════════════════════════════════════
#  Registration
# ═══════════════════════════════════════════════════════════


def register_error_handlers(app: FastAPI) -> None:
    """Attach exception handlers to the FastAPI *app* instance."""

    # ── AppException (and all subclasses) ──────────────────
    @app.exception_handler(AppException)
    async def app_exception_handler(
        _request: Request, exc: AppException
    ) -> JSONResponse:
        logger.warning(
            "AppException [%s] %d: %s", exc.code, exc.status_code, exc.message
        )
        return _error_response(exc.code, exc.message, exc.status_code)

    # ── ValueError ─────────────────────────────────────────
    @app.exception_handler(ValueError)
    async def value_error_handler(
        _request: Request, exc: ValueError
    ) -> JSONResponse:
        logger.warning("ValueError: %s", exc)
        return _error_response(
            "VALIDATION_ERROR",
            str(exc),
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    # ── FileNotFoundError ──────────────────────────────────
    @app.exception_handler(FileNotFoundError)
    async def file_not_found_handler(
        _request: Request, exc: FileNotFoundError
    ) -> JSONResponse:
        logger.warning("FileNotFoundError: %s", exc)
        return _error_response(
            "FILE_NOT_FOUND",
            "The requested resource was not found.",
            status.HTTP_404_NOT_FOUND,
        )

    # ── PermissionError ────────────────────────────────────
    @app.exception_handler(PermissionError)
    async def permission_error_handler(
        _request: Request, exc: PermissionError
    ) -> JSONResponse:
        logger.warning("PermissionError: %s", exc)
        return _error_response(
            "FORBIDDEN",
            "You do not have permission to perform this action.",
            status.HTTP_403_FORBIDDEN,
        )

    # ── Generic catch-all ──────────────────────────────────
    @app.exception_handler(Exception)
    async def generic_exception_handler(
        _request: Request, exc: Exception
    ) -> JSONResponse:
        logger.error(
            "Unhandled exception: %s\n%s", exc, traceback.format_exc()
        )
        return _error_response(
            "INTERNAL_SERVER_ERROR",
            "An unexpected error occurred. Please try again later.",
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
