"""
Structured logging setup for the DepreSense API.

Provides:
- ``setup_logging()``  — initialise root logger with console + rotating file handlers
- ``get_logger(name)`` — convenience for per-module loggers
- Helper functions that emit structured log messages for common operations
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler


# ── Directories ────────────────────────────────────────────
_LOGS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "logs")


# ── Formatters ─────────────────────────────────────────────
_CONSOLE_FMT = (
    "%(asctime)s  %(levelname)-8s  [%(name)s]  %(message)s"
)
_FILE_FMT = (
    "%(asctime)s  %(levelname)-8s  [%(name)s]  %(message)s"
)
_DATE_FMT = "%Y-%m-%d %H:%M:%S"


def setup_logging(log_level: str = "INFO") -> None:
    """Initialise root logger with console + rotating file handlers.

    Call once during app startup.
    """
    os.makedirs(_LOGS_DIR, exist_ok=True)

    level = getattr(logging, log_level.upper(), logging.INFO)

    root = logging.getLogger()
    root.setLevel(level)

    # Prevent duplicate handlers on reload
    if root.handlers:
        return

    # Console handler
    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(logging.Formatter(_CONSOLE_FMT, datefmt=_DATE_FMT))
    root.addHandler(console)

    # Rotating file handler (10 MB, keep 5 backups)
    log_file = os.path.join(_LOGS_DIR, "depresense.log")
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(logging.Formatter(_FILE_FMT, datefmt=_DATE_FMT))
    root.addHandler(file_handler)

    # Silence noisy third-party loggers
    for noisy in ("urllib3", "httpcore", "httpx", "h5py", "absl"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logging.getLogger("root").info(
        "Logging initialised — level=%s, file=%s", log_level, log_file
    )


def get_logger(name: str) -> logging.Logger:
    """Return a named logger instance (convenience wrapper)."""
    return logging.getLogger(name)


# ═══════════════════════════════════════════════════════════
#  Structured log helpers
# ═══════════════════════════════════════════════════════════

_api_logger = logging.getLogger("depresense.api")


def log_request(
    request_method: str,
    request_path: str,
    user_id: str | None = None,
    request_id: str | None = None,
) -> None:
    """Log an incoming HTTP request."""
    extra = f"  user={user_id}" if user_id else ""
    rid = f"  req_id={request_id}" if request_id else ""
    _api_logger.info("→ %s %s%s%s", request_method, request_path, extra, rid)


def log_response(
    status_code: int,
    response_time_ms: float,
    request_id: str | None = None,
) -> None:
    """Log an outgoing HTTP response."""
    rid = f"  req_id={request_id}" if request_id else ""
    _api_logger.info("← %d  %.1f ms%s", status_code, response_time_ms, rid)


def log_error(
    error_code: str,
    error_message: str,
    tb: str | None = None,
    request_id: str | None = None,
) -> None:
    """Log an application error with optional traceback."""
    rid = f"  req_id={request_id}" if request_id else ""
    _api_logger.error("[%s] %s%s", error_code, error_message, rid)
    if tb:
        _api_logger.debug("Traceback:\n%s", tb)


def log_model_inference(
    file_id: str,
    prediction_result: dict,
    inference_time_ms: float | None = None,
) -> None:
    """Log a completed model inference operation."""
    prob = prediction_result.get("depression_probability", "?")
    risk = prediction_result.get("risk_level", "?")
    time_str = f"  {inference_time_ms:.1f} ms" if inference_time_ms else ""
    _api_logger.info(
        "Inference file=%s  prob=%.4f  risk=%s%s",
        file_id, float(prob), risk, time_str,
    )


def log_database_operation(
    operation: str,
    collection: str,
    status: str,
    doc_count: int | None = None,
) -> None:
    """Log a Firestore database operation."""
    count = f"  docs={doc_count}" if doc_count is not None else ""
    _api_logger.info(
        "Firestore %s on %s → %s%s", operation, collection, status, count
    )
