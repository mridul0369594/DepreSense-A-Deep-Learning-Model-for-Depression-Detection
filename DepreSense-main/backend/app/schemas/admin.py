"""
Pydantic models for Admin Panel requests and responses.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, EmailStr, Field


# ── Admin Login ────────────────────────────────────────────

class AdminLoginRequest(BaseModel):
    """Payload for admin login with hardcoded credentials."""
    email: EmailStr = Field(..., description="Admin email address")
    password: str = Field(..., min_length=1, description="Admin password")


class AdminOTPVerifyRequest(BaseModel):
    """Payload for verifying OTP during admin login."""
    email: EmailStr = Field(..., description="Admin email address")
    otp: str = Field(
        ..., min_length=6, max_length=6, pattern=r"^\d{6}$",
        description="6-digit OTP code",
    )


# ── User Management ───────────────────────────────────────

class AddUserRequest(BaseModel):
    """Payload for adding a new user (clinician or admin)."""
    full_name: str = Field(..., min_length=1, max_length=100, description="Full name")
    email: EmailStr = Field(..., description="User email address")
    role: str = Field(..., description="User role: Clinician or Admin")
    phone: Optional[str] = Field(None, description="Phone number")


class EditUserRequest(BaseModel):
    """Payload for editing a user."""
    full_name: Optional[str] = Field(None, description="Updated full name")
    role: Optional[str] = Field(None, description="Updated role")
    phone: Optional[str] = Field(None, description="Updated phone")
    status: Optional[str] = Field(None, description="Updated status: Active or Removed")


class UserRecord(BaseModel):
    """Public representation of a managed user."""
    id: str = Field(..., description="User document ID")
    full_name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    role: str = Field(..., description="Role")
    phone: Optional[str] = Field(None, description="Phone number")
    last_active: str = Field(..., description="Last active timestamp or 'Never Logged In'")
    status: str = Field(..., description="Active or Removed")


class UserListResponse(BaseModel):
    """Response containing a list of managed users."""
    users: List[UserRecord]


# ── System Logs ────────────────────────────────────────────

class LogEntry(BaseModel):
    """A single system log entry."""
    id: str
    timestamp: str
    type: str  # info, success, warning, error
    user: str
    action: str
    details: str


class LogsResponse(BaseModel):
    """Response containing system logs and statistics."""
    logs: List[LogEntry]
    total_events: int
    user_logins: int
    warnings: int


# ── Admin Settings ─────────────────────────────────────────

class AdminSettingsModel(BaseModel):
    """Admin panel settings."""
    session_timeout: int = Field(30, description="Session timeout in minutes")
    maintenance_mode: bool = Field(False, description="Whether maintenance mode is enabled")
    auto_approve: bool = Field(False, description="Auto-approve clinician registrations")
    email_notifications: bool = Field(True, description="Email notifications enabled")


class AdminSettingsResponse(BaseModel):
    """Response with current admin settings."""
    settings: AdminSettingsModel
    message: str = "Settings retrieved successfully"
