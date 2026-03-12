"""
Pydantic models for authentication requests and responses.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


# ── Request Models ─────────────────────────────────────────


class SignupRequest(BaseModel):
    """Payload for creating a new user account."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(
        ..., min_length=6, max_length=128, description="Password (min 6 chars)"
    )
    name: str = Field(
        ..., min_length=1, max_length=100, description="Display name"
    )


class LoginRequest(BaseModel):
    """Payload for logging into an existing account."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=1, description="User password")


# ── Response Models ────────────────────────────────────────


class UserResponse(BaseModel):
    """Public representation of a user."""

    uid: str = Field(..., description="Firebase user UID")
    email: str = Field(..., description="Email address")
    name: Optional[str] = Field(None, description="Display name")
    created_at: Optional[datetime] = Field(
        None, description="Account creation timestamp"
    )


class AuthTokenResponse(BaseModel):
    """Returned after successful signup or login."""

    token: str = Field(..., description="Firebase ID token")
    user: UserResponse
    message: str = Field("success", description="Status message")


# ── OTP Models ─────────────────────────────────────────────


class OTPVerificationRequest(BaseModel):
    """Payload for verifying an email OTP."""

    email: EmailStr = Field(..., description="User email address")
    otp: str = Field(
        ..., min_length=6, max_length=6, pattern=r"^\d{6}$",
        description="6-digit OTP code",
    )


class LoginOTPVerifyRequest(BaseModel):
    """Payload for verifying OTP during login (2FA)."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=1, description="User password")
    otp: str = Field(
        ..., min_length=6, max_length=6, pattern=r"^\d{6}$",
        description="6-digit OTP code",
    )


class ResendOTPRequest(BaseModel):
    """Payload for requesting a new OTP to be resent."""

    email: EmailStr = Field(..., description="User email address")


# ── Forgot Password Models ─────────────────────────────────


class ForgotPasswordRequest(BaseModel):
    """Step 1: Send OTP to verify ownership of the email."""

    email: EmailStr = Field(..., description="Registered email address")


class ForgotPasswordVerifyRequest(BaseModel):
    """Step 2: Verify OTP received by email."""

    email: EmailStr = Field(..., description="Registered email address")
    otp: str = Field(
        ..., min_length=6, max_length=6, pattern=r"^\d{6}$",
        description="6-digit OTP code",
    )


class ResetPasswordRequest(BaseModel):
    """Step 3: Set new password after OTP verified."""

    email: EmailStr = Field(..., description="Registered email address")
    new_password: str = Field(
        ..., min_length=8, max_length=128,
        description="New password (min 8 chars)",
    )
    reset_token: str = Field(
        ..., description="Token received after successful OTP verification",
    )


# ── Change Password Model ──────────────────────────────────


class ChangePasswordRequest(BaseModel):
    """Payload for changing password from the Settings page (authenticated)."""

    current_password: str = Field(..., min_length=1, description="Current password")
    new_password: str = Field(
        ..., min_length=8, max_length=128,
        description="New password (min 8 chars)",
    )
