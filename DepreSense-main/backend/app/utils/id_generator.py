"""
ID generation utilities.
"""

from __future__ import annotations

import uuid


def generate_file_id() -> str:
    """Generate a unique file identifier (UUID4 hex)."""
    return uuid.uuid4().hex


def generate_prediction_id() -> str:
    """Generate a unique prediction identifier (UUID4 hex)."""
    return uuid.uuid4().hex
