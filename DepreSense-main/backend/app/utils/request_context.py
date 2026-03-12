"""
Thread-safe request context using :mod:`contextvars`.

Each incoming request receives a unique ``request_id`` (UUID4) and an
associated :class:`RequestContext` that travels with the request through
all async middleware and route handler code.
"""

from __future__ import annotations

import time
import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RequestContext:
    """Per-request metadata container."""

    request_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    user_id: Optional[str] = None
    request_method: str = ""
    request_path: str = ""
    start_time: float = field(default_factory=time.perf_counter)
    status_code: Optional[int] = None
    response_time_ms: Optional[float] = None

    def elapsed_ms(self) -> float:
        """Return milliseconds elapsed since *start_time*."""
        return (time.perf_counter() - self.start_time) * 1000.0


# ── Context variable ──────────────────────────────────────
_request_ctx_var: ContextVar[Optional[RequestContext]] = ContextVar(
    "request_context", default=None
)


def get_request_context() -> Optional[RequestContext]:
    """Return the current request context (or ``None``)."""
    return _request_ctx_var.get()


def set_request_context(ctx: RequestContext) -> None:
    """Set the current request context."""
    _request_ctx_var.set(ctx)


def generate_request_id() -> str:
    """Generate a unique request identifier."""
    return uuid.uuid4().hex
