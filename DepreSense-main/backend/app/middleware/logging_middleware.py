"""
Request / response logging middleware.

For every HTTP request the middleware:

1. Creates a :class:`RequestContext` and stores it via *contextvars*.
2. Logs the incoming request method and path.
3. Calls the next handler.
4. Calculates elapsed time and logs the response status code.
5. Adds an ``X-Request-ID`` response header.
"""

from __future__ import annotations

import logging

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.utils.logger import log_request, log_response
from app.utils.request_context import RequestContext, set_request_context

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Log every request and response with timing information."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # 1. Build context
        ctx = RequestContext(
            request_method=request.method,
            request_path=request.url.path,
        )
        set_request_context(ctx)

        # Try to pick up user_id later if auth runs, but log request now
        user_id = getattr(getattr(request, "state", None), "user", {}).get("uid")
        ctx.user_id = user_id

        # 2. Log incoming request
        log_request(
            ctx.request_method,
            ctx.request_path,
            user_id=ctx.user_id,
            request_id=ctx.request_id,
        )

        # 3. Process request
        response = await call_next(request)

        # 4. Capture user_id if it was set during auth
        if ctx.user_id is None:
            ctx.user_id = getattr(
                getattr(request, "state", None), "user", {}
            ).get("uid")

        # 5. Calculate elapsed time
        ctx.status_code = response.status_code
        ctx.response_time_ms = ctx.elapsed_ms()

        # 6. Log response
        log_response(
            ctx.status_code,
            ctx.response_time_ms,
            request_id=ctx.request_id,
        )

        # 7. Include request ID in response headers
        response.headers["X-Request-ID"] = ctx.request_id

        return response
