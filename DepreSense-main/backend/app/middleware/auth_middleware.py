"""
Firebase ID-token authentication dependency for FastAPI.

Logs every authentication attempt (success and failure) with the
corresponding request ID.  Token values are **never** logged.

Usage::

    from app.middleware.auth_middleware import get_current_user

    @router.get("/protected")
    async def protected_route(user: dict = Depends(get_current_user)):
        return {"uid": user["uid"]}
"""

from __future__ import annotations

import logging

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.utils.firebase_client import auth_client
from app.utils.request_context import get_request_context

logger = logging.getLogger(__name__)

# FastAPI security scheme — extracts "Bearer <token>" from the header.
_bearer_scheme = HTTPBearer(auto_error=False)


def _rid() -> str:
    """Return the current request ID (or ``-``) for log correlation."""
    ctx = get_request_context()
    return ctx.request_id if ctx else "-"


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> dict:
    """Validate the Firebase ID token and return the decoded user info.

    Raises ``HTTPException(401)`` when the token is missing or invalid.
    The decoded payload is also stored on ``request.state.user`` for
    convenience.
    """
    if credentials is None:
        logger.warning(
            "Auth failure [MISSING_TOKEN]  req_id=%s  path=%s",
            _rid(), request.url.path,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "MISSING_TOKEN",
                "message": "Authorization header with Bearer token is required.",
            },
        )

    token = credentials.credentials
    try:
        decoded = auth_client.verify_id_token(token)
        user_info = {
            "uid": decoded["uid"],
            "email": decoded.get("email", ""),
            "name": decoded.get("name", ""),
        }
        # Attach to request state so downstream code can also access it.
        request.state.user = user_info

        # Update request context with user information
        ctx = get_request_context()
        if ctx:
            ctx.user_id = user_info["uid"]

        logger.info(
            "Auth success  uid=%s  req_id=%s", user_info["uid"], _rid()
        )
        return user_info

    except auth_client.ExpiredIdTokenError:
        logger.warning("Auth failure [TOKEN_EXPIRED]  req_id=%s", _rid())
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "TOKEN_EXPIRED",
                "message": "The authentication token has expired. Please log in again.",
            },
        )
    except auth_client.RevokedIdTokenError:
        logger.warning("Auth failure [TOKEN_REVOKED]  req_id=%s", _rid())
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "TOKEN_REVOKED",
                "message": "The authentication token has been revoked.",
            },
        )
    except auth_client.InvalidIdTokenError:
        logger.warning("Auth failure [INVALID_TOKEN]  req_id=%s", _rid())
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "INVALID_TOKEN",
                "message": "The authentication token is invalid.",
            },
        )
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "Auth failure [AUTH_ERROR]  req_id=%s  error=%s", _rid(), exc
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "AUTH_ERROR",
                "message": "Authentication failed.",
            },
        )
