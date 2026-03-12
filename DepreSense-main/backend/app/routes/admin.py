"""
Admin Panel routes — login, user management, system logs, settings.

Admin login uses hardcoded credentials (not Firebase Auth) plus OTP 2FA
via the same OTP service used for clinician login.

Managed users and system logs are stored in Firestore collections:
  - admin_users     (managed clinician/admin accounts)
  - system_logs     (recorded system events)
  - admin_settings  (singleton settings document)
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from app.middleware.auth_middleware import get_current_user
from app.schemas.admin import (
    AddUserRequest,
    AdminLoginRequest,
    AdminOTPVerifyRequest,
    AdminSettingsModel,
    AdminSettingsResponse,
    EditUserRequest,
    LogEntry,
    LogsResponse,
    UserListResponse,
    UserRecord,
)
from app.services import otp_service
from app.utils.firebase_client import db_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin Panel"])

# ── Hardcoded admin credentials ────────────────────────────
_ADMIN_EMAIL = "mridul06027@gmail.com"
_ADMIN_PASSWORD = "12345678"

# ── Firestore collection names ─────────────────────────────
_USERS_COLLECTION = "admin_users"
_LOGS_COLLECTION = "system_logs"
_SETTINGS_DOC = "admin_settings"
_SETTINGS_COLLECTION = "system_config"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _format_ts(dt: Optional[datetime] = None) -> str:
    """Format a datetime as 'YYYY-MM-DD HH:MM:SS'."""
    if dt is None:
        dt = _now()
    return dt.strftime("%Y-%m-%d %H:%M:%S")


# ═══════════════════════════════════════════════════════════
#  Helper: record a system log entry
# ═══════════════════════════════════════════════════════════

def _record_log(
    log_type: str,
    user: str,
    action: str,
    details: str,
) -> None:
    """Write a system log entry to Firestore (non-blocking on error)."""
    if db_client is None:
        logger.warning("Firestore not available; cannot record log.")
        return
    try:
        log_id = str(uuid.uuid4())
        db_client.collection(_LOGS_COLLECTION).document(log_id).set({
            "id": log_id,
            "timestamp": _format_ts(),
            "type": log_type,
            "user": user,
            "action": action,
            "details": details,
            "created_at": _now(),
        })
    except Exception as exc:
        logger.error("Failed to record system log: %s", exc)


# ═══════════════════════════════════════════════════════════
#  Helper: verify the caller is an admin
# ═══════════════════════════════════════════════════════════

def _require_admin(user: dict) -> None:
    """Raise 403 if the caller is not the hardcoded admin."""
    admin_token = user.get("admin_token")
    if not admin_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Admin access required."},
        )


# ═══════════════════════════════════════════════════════════
#  ADMIN LOGIN
# ═══════════════════════════════════════════════════════════


@router.post("/login")
async def admin_login(body: AdminLoginRequest):
    """Validate hardcoded admin credentials and send OTP."""
    if body.email != _ADMIN_EMAIL or body.password != _ADMIN_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "INVALID_CREDENTIALS",
                "message": "Invalid admin email or password.",
            },
        )

    # Generate and send OTP using the existing OTP service
    otp = otp_service.generate_otp()
    if not otp_service.store_otp(body.email, otp, expiry_minutes=1):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "OTP_STORE_FAILED",
                "message": "Could not initiate verification. Please try again.",
            },
        )

    if not otp_service.send_otp_email(body.email, otp):
        otp_service.delete_otp(body.email)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "EMAIL_SEND_FAILED",
                "message": "Could not send verification email. Please try again.",
            },
        )

    logger.info("Admin login OTP sent to %s", body.email)
    return {
        "message": "Verification code sent to your email.",
        "email": body.email,
        "status": "otp_sent",
    }


@router.post("/verify-otp")
async def admin_verify_otp(body: AdminOTPVerifyRequest):
    """Verify OTP for admin login and return an admin session token."""
    if body.email != _ADMIN_EMAIL:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "INVALID_CREDENTIALS",
                "message": "Invalid admin email.",
            },
        )

    result = otp_service.verify_otp(body.email, body.otp)
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "OTP_INVALID", "message": result["message"]},
        )

    # Clean up OTP
    otp_service.delete_otp(body.email)

    # Generate a simple admin session token (UUID-based)
    admin_token = f"admin-{uuid.uuid4().hex}"

    # Store the admin session in Firestore for validation
    if db_client is not None:
        try:
            db_client.collection("admin_sessions").document(admin_token).set({
                "email": body.email,
                "created_at": _now(),
                "expires_at": _now() + timedelta(hours=24),
            })
        except Exception as exc:
            logger.warning("Failed to store admin session: %s", exc)

    # Record login log
    _record_log("info", "Admin", "Admin login successful",
                f"Admin authenticated via email/OTP: {body.email}")

    logger.info("Admin login completed for %s", body.email)
    return {
        "token": admin_token,
        "user": {
            "uid": "admin",
            "email": body.email,
            "name": "System Administrator",
        },
        "message": "Admin login successful",
    }


# ═══════════════════════════════════════════════════════════
#  ADMIN AUTH MIDDLEWARE (using admin token)
# ═══════════════════════════════════════════════════════════


async def get_admin_user(
    credentials=Depends(get_current_user),
) -> dict:
    """Dependency that validates admin authentication.

    Accepts either:
    - Firebase token from a user with admin email
    - Admin session token
    """
    return credentials


# For admin routes that need the admin token directly from the header
from fastapi import Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

_admin_bearer = HTTPBearer(auto_error=False)


async def verify_admin_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_admin_bearer),
) -> dict:
    """Validate admin session token from Authorization header."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "MISSING_TOKEN",
                "message": "Admin authorization required.",
            },
        )

    token = credentials.credentials

    # Check if it's an admin session token
    if token.startswith("admin-"):
        if db_client is not None:
            try:
                doc = db_client.collection("admin_sessions").document(token).get()
                if doc.exists:
                    data = doc.to_dict()
                    expires_at = data.get("expires_at")
                    if expires_at:
                        if hasattr(expires_at, 'tzinfo') and expires_at.tzinfo is None:
                            expires_at = expires_at.replace(tzinfo=timezone.utc)
                        if _now() < expires_at:
                            return {
                                "uid": "admin",
                                "email": data.get("email", _ADMIN_EMAIL),
                                "name": "System Administrator",
                                "admin_token": True,
                            }
            except Exception as exc:
                logger.error("Admin session validation error: %s", exc)

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "INVALID_TOKEN",
                "message": "Admin session expired or invalid.",
            },
        )

    # Try Firebase token validation as fallback
    try:
        from app.utils.firebase_client import auth_client
        decoded = auth_client.verify_id_token(token)
        email = decoded.get("email", "")
        if email == _ADMIN_EMAIL:
            return {
                "uid": decoded["uid"],
                "email": email,
                "name": decoded.get("name", "System Administrator"),
                "admin_token": True,
            }
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "FORBIDDEN",
                "message": "Admin access required.",
            },
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "INVALID_TOKEN",
                "message": "Authentication failed.",
            },
        )


# ═══════════════════════════════════════════════════════════
#  USER MANAGEMENT
# ═══════════════════════════════════════════════════════════


@router.get("/users", response_model=UserListResponse)
async def list_users(
    status_filter: str = "Active",
    admin: dict = Depends(verify_admin_token),
):
    """List all managed users filtered by status (Active or Removed)."""
    if db_client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "DB_UNAVAILABLE", "message": "Database not available."},
        )

    try:
        docs = (
            db_client.collection(_USERS_COLLECTION)
            .where("status", "==", status_filter)
            .stream()
        )
        users = []
        for doc in docs:
            data = doc.to_dict()
            users.append(UserRecord(
                id=doc.id,
                full_name=data.get("full_name", ""),
                email=data.get("email", ""),
                role=data.get("role", "Clinician"),
                phone=data.get("phone"),
                last_active=data.get("last_active", "Never Logged In"),
                status=data.get("status", "Active"),
            ))
        return UserListResponse(users=users)
    except Exception as exc:
        logger.error("Failed to list users: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "LIST_ERROR", "message": "Failed to retrieve users."},
        )


@router.post("/users", response_model=UserRecord)
async def add_user(
    body: AddUserRequest,
    admin: dict = Depends(verify_admin_token),
):
    """Add a new user (clinician or admin)."""
    if db_client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "DB_UNAVAILABLE", "message": "Database not available."},
        )

    # Validate role
    if body.role not in ("Clinician", "Admin"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_ROLE",
                "message": "Role must be 'Clinician' or 'Admin'.",
            },
        )

    # Check if email already exists
    try:
        existing = list(
            db_client.collection(_USERS_COLLECTION)
            .where("email", "==", body.email)
            .limit(1)
            .stream()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "EMAIL_EXISTS",
                    "message": "A user with this email already exists.",
                },
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Email uniqueness check failed: %s", exc)

    try:
        user_id = str(uuid.uuid4())[:8].upper()
        user_data = {
            "full_name": body.full_name,
            "email": body.email,
            "role": body.role,
            "phone": body.phone or "",
            "last_active": "Never Logged In",
            "status": "Active",
            "created_at": _now(),
        }
        db_client.collection(_USERS_COLLECTION).document(user_id).set(user_data)

        # Record log
        _record_log(
            "success", "Admin", "User added",
            f"{body.full_name} ({body.email}) added as {body.role}",
        )

        logger.info("Added user %s (%s)", body.full_name, user_id)
        return UserRecord(id=user_id, **{k: v for k, v in user_data.items() if k != "created_at"})

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to add user: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "CREATE_ERROR", "message": "Failed to create user."},
        )


@router.put("/users/{user_id}", response_model=UserRecord)
async def edit_user(
    user_id: str,
    body: EditUserRequest,
    admin: dict = Depends(verify_admin_token),
):
    """Edit an existing user's details."""
    if db_client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "DB_UNAVAILABLE", "message": "Database not available."},
        )

    try:
        doc_ref = db_client.collection(_USERS_COLLECTION).document(user_id)
        doc = doc_ref.get()

        if not doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "USER_NOT_FOUND", "message": "User not found."},
            )

        current_data = doc.to_dict()
        updates = {}
        if body.full_name is not None:
            updates["full_name"] = body.full_name
        if body.role is not None:
            if body.role not in ("Clinician", "Admin"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "code": "INVALID_ROLE",
                        "message": "Role must be 'Clinician' or 'Admin'.",
                    },
                )
            updates["role"] = body.role
        if body.phone is not None:
            updates["phone"] = body.phone
        if body.status is not None:
            updates["status"] = body.status

        if updates:
            doc_ref.update(updates)
            current_data.update(updates)

        # Record log
        _record_log(
            "info", "Admin", "User edited",
            f"{current_data.get('full_name', user_id)} updated: {list(updates.keys())}",
        )

        return UserRecord(
            id=user_id,
            full_name=current_data.get("full_name", ""),
            email=current_data.get("email", ""),
            role=current_data.get("role", "Clinician"),
            phone=current_data.get("phone"),
            last_active=current_data.get("last_active", "Never Logged In"),
            status=current_data.get("status", "Active"),
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to edit user %s: %s", user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "UPDATE_ERROR", "message": "Failed to update user."},
        )


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    admin: dict = Depends(verify_admin_token),
):
    """Soft-delete a user by changing their status to 'Removed'."""
    if db_client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "DB_UNAVAILABLE", "message": "Database not available."},
        )

    try:
        doc_ref = db_client.collection(_USERS_COLLECTION).document(user_id)
        doc = doc_ref.get()

        if not doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "USER_NOT_FOUND", "message": "User not found."},
            )

        user_data = doc.to_dict()
        doc_ref.update({"status": "Removed"})

        # Record log
        _record_log(
            "warning", "Admin", "User removed",
            f"{user_data.get('full_name', user_id)} status changed to Removed",
        )

        return {
            "message": f"User {user_data.get('full_name', user_id)} has been removed.",
            "user_id": user_id,
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to delete user %s: %s", user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "DELETE_ERROR", "message": "Failed to remove user."},
        )


@router.post("/users/{user_id}/restore")
async def restore_user(
    user_id: str,
    admin: dict = Depends(verify_admin_token),
):
    """Restore a removed user back to Active status."""
    if db_client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "DB_UNAVAILABLE", "message": "Database not available."},
        )

    try:
        doc_ref = db_client.collection(_USERS_COLLECTION).document(user_id)
        doc = doc_ref.get()

        if not doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "USER_NOT_FOUND", "message": "User not found."},
            )

        user_data = doc.to_dict()
        doc_ref.update({"status": "Active"})

        # Record log
        _record_log(
            "success", "Admin", "User restored",
            f"{user_data.get('full_name', user_id)} restored to Active",
        )

        return {
            "message": f"User {user_data.get('full_name', user_id)} has been restored.",
            "user_id": user_id,
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to restore user %s: %s", user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "RESTORE_ERROR", "message": "Failed to restore user."},
        )


# ═══════════════════════════════════════════════════════════
#  SYSTEM LOGS
# ═══════════════════════════════════════════════════════════


@router.get("/logs", response_model=LogsResponse)
async def get_system_logs(
    admin: dict = Depends(verify_admin_token),
):
    """Retrieve system logs with statistics."""
    if db_client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "DB_UNAVAILABLE", "message": "Database not available."},
        )

    try:
        docs = (
            db_client.collection(_LOGS_COLLECTION)
            .order_by("created_at", direction="DESCENDING")
            .limit(100)
            .stream()
        )

        logs = []
        total_events = 0
        user_logins = 0
        warnings = 0
        twenty_four_hours_ago = _now() - timedelta(hours=24)

        for doc in docs:
            data = doc.to_dict()
            log_entry = LogEntry(
                id=data.get("id", doc.id),
                timestamp=data.get("timestamp", ""),
                type=data.get("type", "info"),
                user=data.get("user", "System"),
                action=data.get("action", ""),
                details=data.get("details", ""),
            )
            logs.append(log_entry)

            # Calculate stats for last 24 hours
            created_at = data.get("created_at")
            if created_at:
                if hasattr(created_at, 'tzinfo') and created_at.tzinfo is None:
                    created_at = created_at.replace(tzinfo=timezone.utc)
                if created_at >= twenty_four_hours_ago:
                    total_events += 1
                    if "login" in data.get("action", "").lower():
                        user_logins += 1
                    if data.get("type") == "warning":
                        warnings += 1

        return LogsResponse(
            logs=logs,
            total_events=total_events,
            user_logins=user_logins,
            warnings=warnings,
        )

    except Exception as exc:
        logger.error("Failed to get system logs: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "LOGS_ERROR", "message": "Failed to retrieve system logs."},
        )


@router.post("/logs")
async def create_log(
    log_type: str = "info",
    user: str = "System",
    action: str = "",
    details: str = "",
    admin: dict = Depends(verify_admin_token),
):
    """Manually create a system log entry."""
    _record_log(log_type, user, action, details)
    return {"message": "Log entry created."}


# ═══════════════════════════════════════════════════════════
#  ADMIN SETTINGS
# ═══════════════════════════════════════════════════════════


def _get_settings() -> dict:
    """Retrieve admin settings from Firestore, returning defaults if not found."""
    defaults = {
        "session_timeout": 30,
        "maintenance_mode": False,
        "auto_approve": False,
        "email_notifications": True,
    }
    if db_client is None:
        return defaults

    try:
        doc = (
            db_client.collection(_SETTINGS_COLLECTION)
            .document(_SETTINGS_DOC)
            .get()
        )
        if doc.exists:
            data = doc.to_dict()
            return {
                "session_timeout": data.get("session_timeout", 30),
                "maintenance_mode": data.get("maintenance_mode", False),
                "auto_approve": data.get("auto_approve", False),
                "email_notifications": data.get("email_notifications", True),
            }
    except Exception as exc:
        logger.error("Failed to get admin settings: %s", exc)

    return defaults


@router.get("/settings", response_model=AdminSettingsResponse)
async def get_admin_settings(
    admin: dict = Depends(verify_admin_token),
):
    """Retrieve current admin settings."""
    settings_data = _get_settings()
    return AdminSettingsResponse(
        settings=AdminSettingsModel(**settings_data),
        message="Settings retrieved successfully",
    )


@router.put("/settings", response_model=AdminSettingsResponse)
async def update_admin_settings(
    body: AdminSettingsModel,
    admin: dict = Depends(verify_admin_token),
):
    """Update admin settings."""
    if db_client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "DB_UNAVAILABLE", "message": "Database not available."},
        )

    try:
        settings_data = {
            "session_timeout": body.session_timeout,
            "maintenance_mode": body.maintenance_mode,
            "auto_approve": body.auto_approve,
            "email_notifications": body.email_notifications,
            "updated_at": _now(),
        }
        db_client.collection(_SETTINGS_COLLECTION).document(_SETTINGS_DOC).set(
            settings_data, merge=True,
        )

        # Record log
        _record_log(
            "info", "Admin", "Settings updated",
            f"Admin settings updated: timeout={body.session_timeout}min, "
            f"maintenance={body.maintenance_mode}, auto_approve={body.auto_approve}",
        )

        return AdminSettingsResponse(
            settings=body,
            message="Settings saved successfully",
        )
    except Exception as exc:
        logger.error("Failed to update settings: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "SETTINGS_ERROR", "message": "Failed to save settings."},
        )


# ═══════════════════════════════════════════════════════════
#  MAINTENANCE MODE CHECK (for clinician login)
# ═══════════════════════════════════════════════════════════


@router.get("/maintenance-status")
async def check_maintenance():
    """Public endpoint: check if maintenance mode is active."""
    settings_data = _get_settings()
    return {
        "maintenance_mode": settings_data.get("maintenance_mode", False),
        "message": "System is currently under maintenance. Please try again later."
        if settings_data.get("maintenance_mode") else "System is operational.",
    }
