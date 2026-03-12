"""
Firebase client initialisation.

Initialises the Firebase Admin SDK and exposes three helpers:
    - ``auth_client``    – Firebase Authentication
    - ``db_client``      – Cloud Firestore
    - ``storage_client`` – Cloud Storage

A lightweight ``check_firebase_connection()`` function is also provided so
that the /health/firebase endpoint can return a real status.

Credentials can be supplied in two ways (checked in order):
    1. ``FIREBASE_CREDENTIALS_JSON`` env var – a JSON string of the
       service-account key (used on Render / cloud platforms).
    2. ``FIREBASE_CREDENTIALS_PATH`` setting – path to a JSON key file
       (used for local development).
"""

from __future__ import annotations

import json
import logging
import os

import firebase_admin
from firebase_admin import auth, credentials, firestore, storage

from app.config import settings

logger = logging.getLogger(__name__)

# ── Module-level clients (populated by _init_firebase) ─────
_firebase_app: firebase_admin.App | None = None
auth_client = auth
db_client = None
storage_client = None


def _init_firebase() -> None:
    """Initialise the Firebase Admin SDK exactly once."""
    global _firebase_app, db_client, storage_client

    if _firebase_app is not None:
        return  # already initialised

    try:
        # Priority 1: JSON string from environment variable
        creds_json = os.environ.get("FIREBASE_CREDENTIALS_JSON")
        if creds_json:
            cert_dict = json.loads(creds_json)
            cred = credentials.Certificate(cert_dict)
            logger.info("Using Firebase credentials from FIREBASE_CREDENTIALS_JSON env var.")
        else:
            # Priority 2: File path from settings
            cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
            logger.info("Using Firebase credentials from file: %s", settings.FIREBASE_CREDENTIALS_PATH)

        _firebase_app = firebase_admin.initialize_app(cred)
        db_client = firestore.client()
        storage_client = storage
        logger.info("Firebase Admin SDK initialised successfully.")
    except FileNotFoundError:
        logger.error(
            "Firebase credentials file not found at: %s",
            settings.FIREBASE_CREDENTIALS_PATH,
        )
    except (json.JSONDecodeError, ValueError) as exc:
        logger.error("Invalid Firebase credentials: %s", exc)
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to initialise Firebase: %s", exc)


def check_firebase_connection() -> bool:
    """Return *True* if the Firebase Admin SDK is initialised and healthy."""
    try:
        if _firebase_app is None:
            _init_firebase()
        return _firebase_app is not None
    except Exception:  # noqa: BLE001
        return False


# Attempt to initialise on import so clients are ready to use.
_init_firebase()
