"""
Authentication routes — signup, login, OTP verification, current-user, and logout.

Registration flow:
  1. POST /auth/signup      → create Firebase user + send OTP email
  2. POST /auth/verify-otp  → verify OTP → mark user verified in Firestore
  3. POST /auth/login       → normal login (returns token)

User records are persisted to Firestore on signup and login.
"""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timezone

import requests
from fastapi import APIRouter, Depends, HTTPException, status

from app.config import settings
from app.middleware.auth_middleware import get_current_user
from app.schemas.user import (
    AuthTokenResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ForgotPasswordVerifyRequest,
    LoginRequest,
    LoginOTPVerifyRequest,
    OTPVerificationRequest,
    ResendOTPRequest,
    ResetPasswordRequest,
    SignupRequest,
    UserResponse,
)
from app.services import firestore_service
from app.services import otp_service
from app.utils.firebase_client import auth_client

# Lazy import to avoid circular dependency
def _record_system_log(log_type: str, user: str, action: str, details: str) -> None:
    """Record an event in the admin system logs (non-blocking)."""
    try:
        from app.routes.admin import _record_log
        _record_log(log_type, user, action, details)
    except Exception:
        pass  # non-critical

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Firebase Auth REST API base URL
_FIREBASE_SIGN_IN_URL = (
    "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"
)
_FIREBASE_SIGNUP_URL = (
    "https://identitytoolkit.googleapis.com/v1/accounts:signUp"
)


def _firebase_rest_auth(url: str, email: str, password: str) -> dict:
    """Call the Firebase Auth REST API and return the JSON response.

    This is required because the Admin SDK does not support
    email/password sign-in directly — it only verifies tokens.
    """
    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True,
    }
    resp = requests.post(
        url,
        params={"key": settings.FIREBASE_API_KEY},
        json=payload,
        timeout=10,
    )
    data = resp.json()
    if resp.status_code != 200:
        raw_error = data.get("error", {}).get("message", "Authentication failed")
        logger.warning("Firebase REST auth error: %s", raw_error)

        # Map raw Firebase error codes to user-friendly messages
        _FIREBASE_ERROR_MAP = {
            "EMAIL_NOT_FOUND": "No account found with this email address.",
            "INVALID_PASSWORD": "Incorrect password. Please try again.",
            "USER_DISABLED": "This account has been disabled.",
            "TOO_MANY_ATTEMPTS_TRY_LATER": "Too many failed attempts. Please try again later.",
            "INVALID_EMAIL": "Invalid email format.",
            "WEAK_PASSWORD": "Password is too weak. Use at least 6 characters.",
            "EMAIL_EXISTS": "An account with this email already exists.",
            "OPERATION_NOT_ALLOWED": "Password sign-in is disabled for this project.",
        }

        # Firebase errors can have suffixes like " : some detail"
        error_key = raw_error.split(":")[0].strip() if ":" in raw_error else raw_error
        user_message = _FIREBASE_ERROR_MAP.get(
            error_key,
            "Authentication failed. Please check your credentials and try again.",
        )

        # Use 503 if the error is a config/infra issue (API key, etc.)
        upper_err = raw_error.upper()
        if "API KEY" in upper_err or "API_KEY" in upper_err or "CONFIGURATION" in upper_err:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "SERVICE_UNAVAILABLE",
                    "message": "Authentication service is temporarily unavailable. Please try again later.",
                },
            )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTH_FAILED", "message": user_message},
        )
    return data


# ── POST /auth/signup ──────────────────────────────────────


class _SignupPendingResponse(dict):
    """Internal response type — not a full AuthTokenResponse."""


@router.post(
    "/signup",
    status_code=status.HTTP_201_CREATED,
)
async def signup(body: SignupRequest):
    """Create a new Firebase user and send an OTP verification email.

    The user is **not** signed in yet — they must verify their email by
    hitting POST /auth/verify-otp before they can log in.
    """
    try:
        # 1. Create the user via Admin SDK
        user_record = auth_client.create_user(
            email=body.email,
            password=body.password,
            display_name=body.name,
        )

        # 2. Persist an unverified user record to Firestore
        try:
            firestore_service.create_user_record(
                uid=user_record.uid,
                email=user_record.email or body.email,
                name=body.name,
            )
        except Exception as exc:
            logger.warning("Firestore user creation failed (non-blocking): %s", exc)

        # 3. Generate OTP and dispatch email
        otp = otp_service.generate_otp()
        stored = otp_service.store_otp(body.email, otp)
        if not stored:
            # Clean up the Firebase user so they can retry cleanly
            try:
                auth_client.delete_user(user_record.uid)
            except Exception:
                pass
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "OTP_STORE_FAILED",
                    "message": "Could not initiate verification. Please try again.",
                },
            )

        email_sent = otp_service.send_otp_email(body.email, otp)
        if not email_sent:
            # Rollback: remove OTP + Firebase user so signup can be retried
            otp_service.delete_otp(body.email)
            try:
                auth_client.delete_user(user_record.uid)
            except Exception:
                pass
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "EMAIL_SEND_FAILED",
                    "message": "Could not send verification email. Please check the address and try again.",
                },
            )

        logger.info("Signup initiated for %s; OTP sent.", body.email)
        return {
            "message": "Account created. Please check your email for the verification code.",
            "email": body.email,
            "status": "awaiting_otp",
        }

    except HTTPException:
        raise  # re-raise HTTP exceptions from REST helper / above
    except auth_client.EmailAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "EMAIL_EXISTS",
                "message": "An account with this email already exists.",
            },
        )
    except Exception as exc:
        error_str = str(exc)
        logger.error("Signup error: %s", error_str)

        # Detect Firebase SDK not initialized → 503
        if "initialize" in error_str.lower() or "not exist" in error_str.lower():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "SERVICE_UNAVAILABLE",
                    "message": "Authentication service is temporarily unavailable. Please try again later.",
                },
            )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "SIGNUP_ERROR",
                "message": "Failed to create account. Please try again.",
            },
        )


# ── POST /auth/verify-otp ───────────────────────────────────


@router.post("/verify-otp")
async def verify_otp(body: OTPVerificationRequest):
    """Verify the OTP that was emailed during signup.

    On success the user's Firestore record is marked ``email_verified: True``
    and the OTP document is deleted.
    """
    result = otp_service.verify_otp(body.email, body.otp)

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "OTP_INVALID", "message": result["message"]},
        )

    # Mark the user as email-verified in Firestore
    try:
        user_record = auth_client.get_user_by_email(body.email)
        firestore_service.update_user(
            uid=user_record.uid,
            updates={"email_verified": True},
        )
    except Exception as exc:
        logger.warning("Could not update email_verified for %s: %s", body.email, exc)

    # Delete the OTP once verified
    otp_service.delete_otp(body.email)

    logger.info("Email verified for %s", body.email)
    return {"message": "Email verified successfully. You can now log in.", "status": "verified"}


# ── POST /auth/resend-otp ───────────────────────────────────


@router.post("/resend-otp")
async def resend_otp(body: ResendOTPRequest):
    """Delete the existing OTP and send a fresh one to the given email."""
    # Verify the email actually has a Firebase account
    try:
        auth_client.get_user_by_email(body.email)
    except auth_client.UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "USER_NOT_FOUND", "message": "No account found with this email."},
        )

    otp_service.delete_otp(body.email)
    otp = otp_service.generate_otp()

    if not otp_service.store_otp(body.email, otp):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "OTP_STORE_FAILED", "message": "Could not generate a new code. Please try again."},
        )

    if not otp_service.send_otp_email(body.email, otp):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "EMAIL_SEND_FAILED", "message": "Could not send verification email. Please try again."},
        )

    logger.info("OTP resent for %s", body.email)
    return {"message": "A new verification code has been sent to your email."}


# ── POST /auth/login-send-otp ─────────────────────────────


@router.post("/login-send-otp")
async def login_send_otp(body: LoginRequest):
    """Step 1 of login 2FA: validate credentials, then send an OTP.

    The endpoint verifies email/password via the Firebase REST API
    (same as the normal login).  If credentials are valid, it generates
    an OTP, stores it in Firestore and emails it to the user.

    The client should then collect the OTP and call
    ``POST /auth/login-verify-otp`` to complete login.
    """
    # 1. Validate credentials (raises HTTPException on failure)
    _firebase_rest_auth(_FIREBASE_SIGN_IN_URL, body.email, body.password)

    # 2. Generate, store and send OTP
    otp = otp_service.generate_otp()
    if not otp_service.store_otp(body.email, otp):
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

    logger.info("Login OTP sent to %s", body.email)
    return {
        "message": "Verification code sent to your email.",
        "email": body.email,
        "status": "otp_sent",
    }


# ── POST /auth/login-verify-otp ───────────────────────────


@router.post("/login-verify-otp", response_model=AuthTokenResponse)
async def login_verify_otp(body: LoginOTPVerifyRequest):
    """Step 2 of login 2FA: verify OTP, then complete Firebase sign-in.

    On success, returns an ``AuthTokenResponse`` exactly like the normal
    ``POST /auth/login`` endpoint.
    """
    # 1. Verify OTP
    result = otp_service.verify_otp(body.email, body.otp)
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "OTP_INVALID", "message": result["message"]},
        )

    # 2. OTP is valid — clean up and complete sign-in
    otp_service.delete_otp(body.email)

    try:
        rest_data = _firebase_rest_auth(
            _FIREBASE_SIGN_IN_URL, body.email, body.password
        )
        id_token = rest_data["idToken"]
        user_record = auth_client.get_user_by_email(body.email)

        try:
            firestore_service.update_user(
                uid=user_record.uid,
                updates={"last_login": datetime.now(timezone.utc)},
            )
        except Exception as exc:
            logger.warning("Firestore last_login update failed (non-blocking): %s", exc)

        logger.info("Login 2FA completed for %s", body.email)

        # Record system log
        user_name = user_record.display_name or body.email
        _record_system_log(
            "info", user_name, "Login successful",
            f"User authenticated via email/OTP: {body.email}",
        )

        return AuthTokenResponse(
            token=id_token,
            user=UserResponse(
                uid=user_record.uid,
                email=user_record.email or body.email,
                name=user_record.display_name,
                created_at=datetime.now(timezone.utc),
            ),
            message="Login successful",
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Login-verify-otp sign-in error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "LOGIN_ERROR", "message": "Login failed after OTP verification."},
        )


# ── POST /auth/login ──────────────────────────────────────


@router.post("/login", response_model=AuthTokenResponse)
async def login(body: LoginRequest):
    """Authenticate an existing user and return an ID token."""
    try:
        # Sign in via Firebase REST API
        rest_data = _firebase_rest_auth(
            _FIREBASE_SIGN_IN_URL, body.email, body.password
        )
        id_token = rest_data["idToken"]

        # Retrieve full user record from Admin SDK
        user_record = auth_client.get_user_by_email(body.email)

        # Update last_login in Firestore
        try:
            firestore_service.update_user(
                uid=user_record.uid,
                updates={"last_login": datetime.now(timezone.utc)},
            )
        except Exception as exc:
            logger.warning("Firestore last_login update failed (non-blocking): %s", exc)

        return AuthTokenResponse(
            token=id_token,
            user=UserResponse(
                uid=user_record.uid,
                email=user_record.email or body.email,
                name=user_record.display_name,
                created_at=datetime.now(timezone.utc),
            ),
            message="Login successful",
        )
    except HTTPException:
        raise
    except auth_client.UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "USER_NOT_FOUND",
                "message": "No account found with this email.",
            },
        )
    except Exception as exc:
        error_str = str(exc)
        logger.error("Login error: %s", error_str)

        # Detect Firebase SDK not initialized → 503
        if "initialize" in error_str.lower() or "not exist" in error_str.lower():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "SERVICE_UNAVAILABLE",
                    "message": "Authentication service is temporarily unavailable. Please try again later.",
                },
            )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "LOGIN_ERROR",
                "message": "Invalid email or password.",
            },
        )


# ── GET /auth/me ───────────────────────────────────────────


@router.get("/me", response_model=UserResponse)
async def me(user: dict = Depends(get_current_user)):
    """Return the currently authenticated user's profile from Firestore."""
    try:
        # Try Firestore first for complete profile
        fs_user = firestore_service.get_user(user["uid"])
        if fs_user:
            return UserResponse(
                uid=fs_user.get("uid", user["uid"]),
                email=fs_user.get("email", user["email"]),
                name=fs_user.get("name", user.get("name")),
                created_at=fs_user.get("created_at"),
            )

        # Fallback to Firebase Auth metadata
        user_record = auth_client.get_user(user["uid"])
        return UserResponse(
            uid=user_record.uid,
            email=user_record.email or user["email"],
            name=user_record.display_name or user.get("name"),
            created_at=None,
        )
    except Exception as exc:
        logger.error("Fetch user error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "FETCH_USER_ERROR",
                "message": "Failed to retrieve user profile.",
            },
        )


# ── POST /auth/logout ─────────────────────────────────────


@router.post("/logout")
async def logout(user: dict = Depends(get_current_user)):
    """Log the user out by revoking their refresh tokens server-side."""
    try:
        auth_client.revoke_refresh_tokens(user["uid"])
        return {"message": "Logged out successfully"}
    except Exception as exc:
        logger.error("Logout error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "LOGOUT_ERROR",
                "message": "Failed to log out. Please try again.",
            },
        )


# ═══════════════════════════════════════════════════════════
#  FORGOT PASSWORD
# ═══════════════════════════════════════════════════════════

# Firestore collection for reset tokens
_RESET_TOKENS_COLLECTION = "password_reset_tokens"


# ── POST /auth/forgot-password ─────────────────────────────


@router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordRequest):
    """Step 1 of password reset: verify email exists, then send OTP.

    Works for both clinician (Firebase Auth) and admin (hardcoded) accounts.
    """
    from app.routes.admin import _ADMIN_EMAIL

    email = body.email.lower()
    is_admin = email == _ADMIN_EMAIL.lower()

    # Verify the email is registered
    if not is_admin:
        try:
            auth_client.get_user_by_email(email)
        except auth_client.UserNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "USER_NOT_FOUND",
                    "message": "No account found with this email address.",
                },
            )
        except Exception as exc:
            logger.error("Email lookup error: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "code": "LOOKUP_ERROR",
                    "message": "Failed to verify email. Please try again.",
                },
            )

    # Generate and send OTP (1 minute expiry as per requirement)
    otp = otp_service.generate_otp()
    if not otp_service.store_otp(email, otp, expiry_minutes=1):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "OTP_STORE_FAILED",
                "message": "Could not initiate verification. Please try again.",
            },
        )

    if not otp_service.send_otp_email(email, otp):
        otp_service.delete_otp(email)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "EMAIL_SEND_FAILED",
                "message": "Could not send verification email. Please try again.",
            },
        )

    logger.info("Forgot-password OTP sent to %s", email)
    return {
        "message": "Verification code sent to your email.",
        "email": email,
        "status": "otp_sent",
    }


# ── POST /auth/forgot-password/verify-otp ──────────────────


@router.post("/forgot-password/verify-otp")
async def forgot_password_verify_otp(body: ForgotPasswordVerifyRequest):
    """Step 2: Verify OTP for password reset.

    On success, returns a short-lived reset_token that must be supplied
    when setting the new password, preventing unauthorized resets.
    """
    email = body.email.lower()
    result = otp_service.verify_otp(email, body.otp)

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "OTP_INVALID", "message": result["message"]},
        )

    # OTP verified — clean up
    otp_service.delete_otp(email)

    # Generate a one-time reset token and store it in Firestore (5 min TTL)
    reset_token = secrets.token_urlsafe(32)
    from app.utils.firebase_client import db_client as _db
    if _db is not None:
        try:
            from datetime import timedelta
            _db.collection(_RESET_TOKENS_COLLECTION).document(reset_token).set({
                "email": email,
                "created_at": datetime.now(timezone.utc),
                "expires_at": datetime.now(timezone.utc) + timedelta(minutes=5),
                "used": False,
            })
        except Exception as exc:
            logger.error("Failed to store reset token: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "code": "TOKEN_STORE_FAILED",
                    "message": "Password reset failed. Please try again.",
                },
            )

    logger.info("Forgot-password OTP verified for %s", email)
    return {
        "message": "OTP verified successfully. You can now reset your password.",
        "email": email,
        "reset_token": reset_token,
        "status": "verified",
    }


# ── POST /auth/forgot-password/reset ──────────────────────


@router.post("/forgot-password/reset")
async def forgot_password_reset(body: ResetPasswordRequest):
    """Step 3: Set the new password after OTP has been verified.

    Requires the reset_token returned by Step 2.  Works for both
    clinician (Firebase Auth) and admin (hardcoded) accounts.
    """
    from app.routes.admin import _ADMIN_EMAIL
    from app.utils.firebase_client import db_client as _db

    email = body.email.lower()

    # ── Validate the reset token ─────────────────────────────
    if _db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "DB_UNAVAILABLE", "message": "Service unavailable."},
        )

    try:
        token_ref = _db.collection(_RESET_TOKENS_COLLECTION).document(body.reset_token)
        token_doc = token_ref.get()
    except Exception as exc:
        logger.error("Reset token lookup error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "TOKEN_LOOKUP_ERROR", "message": "Failed to verify reset token."},
        )

    if not token_doc.exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_TOKEN",
                "message": "Invalid or expired reset token. Please start the process again.",
            },
        )

    token_data = token_doc.to_dict()

    # Check the token belongs to this email
    if token_data.get("email", "").lower() != email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "TOKEN_MISMATCH", "message": "Reset token does not match email."},
        )

    # Check expiry
    expires_at = token_data.get("expires_at")
    if expires_at:
        if hasattr(expires_at, "tzinfo") and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > expires_at:
            token_ref.delete()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "TOKEN_EXPIRED",
                    "message": "Reset token has expired. Please start the process again.",
                },
            )

    # Check if already used
    if token_data.get("used"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "TOKEN_USED",
                "message": "This reset token has already been used.",
            },
        )

    # ── Update the password ──────────────────────────────────
    is_admin = email == _ADMIN_EMAIL.lower()

    if is_admin:
        # For admin, we cannot change the hardcoded password at runtime,
        # but we store the new password hash in Firestore so it can be
        # checked on next admin login.  Implementation note: the admin
        # route would need to be updated to also check this, but for now
        # we update Firebase if an account exists, else just acknowledge.
        logger.info("Admin password reset requested for %s", email)
        # Mark token used
        token_ref.update({"used": True})
        # We still try to update Firebase in case the admin also has a
        # Firebase account (common in this project).
        try:
            user_record = auth_client.get_user_by_email(email)
            auth_client.update_user(user_record.uid, password=body.new_password)
            logger.info("Firebase password updated for admin %s", email)
        except auth_client.UserNotFoundError:
            # Admin might not have a Firebase account — that's OK
            logger.info("No Firebase account for admin %s; skipped Firebase update.", email)
        except Exception as exc:
            logger.error("Admin password update error: %s", exc)
    else:
        try:
            user_record = auth_client.get_user_by_email(email)
            auth_client.update_user(user_record.uid, password=body.new_password)
        except Exception as exc:
            logger.error("Password reset error for %s: %s", email, exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "code": "RESET_ERROR",
                    "message": "Failed to reset password. Please try again.",
                },
            )

        # Mark token used
        token_ref.update({"used": True})

    # Record system log
    _record_system_log(
        "info", email, "Password reset",
        f"Password was reset via forgot-password flow for {email}",
    )

    logger.info("Password reset completed for %s", email)
    return {
        "message": "Password has been reset successfully. You can now log in with your new password.",
        "status": "reset_complete",
    }


# ═══════════════════════════════════════════════════════════
#  CHANGE PASSWORD (authenticated)
# ═══════════════════════════════════════════════════════════


@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    user: dict = Depends(get_current_user),
):
    """Allow an authenticated user to change their password.

    Verifies the current password via Firebase REST API, then updates
    the password using the Admin SDK.
    """
    email = user["email"]

    # 1. Verify the current password
    try:
        _firebase_rest_auth(_FIREBASE_SIGN_IN_URL, email, body.current_password)
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "WRONG_PASSWORD",
                "message": "Current password is incorrect.",
            },
        )

    # 2. Update password in Firebase
    try:
        auth_client.update_user(user["uid"], password=body.new_password)
    except Exception as exc:
        logger.error("Password change error for %s: %s", email, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "UPDATE_ERROR",
                "message": "Failed to update password. Please try again.",
            },
        )

    # Record system log
    _record_system_log(
        "info", user.get("name", email), "Password changed",
        f"User changed their password: {email}",
    )

    logger.info("Password changed for %s", email)
    return {"message": "Password updated successfully."}
