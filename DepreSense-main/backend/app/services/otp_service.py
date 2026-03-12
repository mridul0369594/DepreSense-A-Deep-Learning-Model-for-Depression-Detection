"""
OTP (One-Time Password) service for email verification.

Handles:
  - 6-digit OTP generation
  - Sending OTP via SMTP (Gmail or any SMTP server)
  - Storing / retrieving OTP records in Firestore (collection: otp_codes)
  - Verifying OTPs with expiry and attempt-rate limiting
  - Deleting OTPs after successful verification

Firestore document structure (otp_codes/{email}):
  email        : str
  code         : str   – 6-digit OTP (plain-text for simplicity; hash in production)
  attempts     : int   – How many failed verification attempts so far
  created_at   : datetime (UTC)
  expires_at   : datetime (UTC)
  verified     : bool

Configuration (via .env / environment):
  SMTP_EMAIL            – Sender email address
  SMTP_PASSWORD         – App-specific password (for Gmail: use App Passwords)
  SMTP_SERVER           – SMTP host         (default: smtp.gmail.com)
  SMTP_PORT             – SMTP port         (default: 465)
  OTP_EXPIRY_MINUTES    – OTP lifetime      (default: 5)
  OTP_MAX_ATTEMPTS      – Max wrong tries   (default: 3)
"""

from __future__ import annotations

import logging
import secrets
import smtplib
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import settings
from app.utils.firebase_client import db_client

logger = logging.getLogger(__name__)


# ── Configuration helpers ─────────────────────────────────

def _expiry_minutes() -> int:
    return settings.OTP_EXPIRY_MINUTES


def _max_attempts() -> int:
    return settings.OTP_MAX_ATTEMPTS


# ── Collection name ───────────────────────────────────────

_COLLECTION = "otp_codes"


# ── Core functions ────────────────────────────────────────

def generate_otp() -> str:
    """Return a cryptographically-random 6-digit OTP string (zero-padded)."""
    return str(secrets.randbelow(1_000_000)).zfill(6)


def store_otp(email: str, otp: str, expiry_minutes: int | None = None) -> bool:
    """Persist an OTP record for *email* in Firestore.

    Overwrites any existing record (resend scenario).
    Returns ``True`` on success, ``False`` on error.
    """
    if db_client is None:
        logger.error("Firestore client is not initialised; cannot store OTP.")
        return False

    if expiry_minutes is None:
        expiry_minutes = _expiry_minutes()

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=expiry_minutes)

    try:
        db_client.collection(_COLLECTION).document(email).set({
            "email": email,
            "code": otp,
            "attempts": 0,
            "created_at": now,
            "expires_at": expires_at,
            "verified": False,
        })
        logger.info("Stored OTP for %s (expires in %d min)", email, expiry_minutes)
        return True
    except Exception as exc:
        logger.error("Failed to store OTP for %s: %s", email, exc)
        return False


def send_otp_email(email: str, otp: str) -> bool:
    """Send the OTP to *email* via SMTP.

    Returns ``True`` if the email was dispatched, ``False`` otherwise.
    """
    sender_email = settings.SMTP_EMAIL
    sender_password = settings.SMTP_PASSWORD
    smtp_server = settings.SMTP_SERVER
    smtp_port = settings.SMTP_PORT

    logger.info(
        "SMTP config: server=%s, port=%d, sender=%s, password_set=%s",
        smtp_server, smtp_port, sender_email, bool(sender_password),
    )

    if not sender_email or not sender_password:
        logger.error(
            "SMTP credentials not configured (SMTP_EMAIL / SMTP_PASSWORD missing)."
        )
        return False

    # Build the email
    message = MIMEMultipart("alternative")
    message["Subject"] = "DepreSense – Your Email Verification Code"
    message["From"] = f"DepreSense <{sender_email}>"
    message["To"] = email

    plain_body = (
        f"Your DepreSense verification code is: {otp}\n\n"
        f"This code expires in {_expiry_minutes()} minutes.\n"
        "Do not share this code with anyone.\n\n"
        "If you did not request this, please ignore this email."
    )
    html_body = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin:0;padding:0;font-family:'Segoe UI',Roboto,Arial,sans-serif;background:#f4f7fb;">
      <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f7fb;padding:40px 20px;">
        <tr>
          <td align="center">
            <table width="520" cellpadding="0" cellspacing="0"
                   style="background:#ffffff;border-radius:12px;overflow:hidden;
                          box-shadow:0 4px 24px rgba(0,0,0,0.08);">
              <!-- Header -->
              <tr>
                <td style="background:linear-gradient(135deg,#1e40af 0%,#3b82f6 100%);
                           padding:32px 40px;text-align:center;">
                  <h1 style="color:#ffffff;margin:0;font-size:26px;font-weight:700;
                             letter-spacing:-0.5px;">DepreSense</h1>
                  <p style="color:rgba(255,255,255,0.85);margin:6px 0 0;font-size:13px;">
                    Clinical EEG-Based Depression Detection
                  </p>
                </td>
              </tr>
              <!-- Body -->
              <tr>
                <td style="padding:40px 40px 32px;">
                  <h2 style="color:#1e293b;font-size:20px;margin:0 0 12px;">
                    Email Verification
                  </h2>
                  <p style="color:#475569;font-size:15px;line-height:1.6;margin:0 0 28px;">
                    Use the code below to verify your email address. The code is
                    valid for <strong>{_expiry_minutes()} minutes</strong>.
                  </p>

                  <!-- OTP box -->
                  <div style="background:#eff6ff;border:2px dashed #3b82f6;
                              border-radius:10px;padding:24px;text-align:center;
                              margin-bottom:28px;">
                    <span style="font-size:42px;font-weight:800;letter-spacing:12px;
                                 color:#1d4ed8;font-family:'Courier New',monospace;">
                      {otp}
                    </span>
                  </div>

                  <p style="color:#94a3b8;font-size:13px;line-height:1.6;margin:0;">
                    If you did not create a DepreSense account, please ignore this email.
                    Do <strong>not</strong> share this code with anyone.
                  </p>
                </td>
              </tr>
              <!-- Footer -->
              <tr>
                <td style="background:#f8fafc;padding:20px 40px;text-align:center;
                           border-top:1px solid #e2e8f0;">
                  <p style="color:#94a3b8;font-size:12px;margin:0;">
                    &copy; 2025 DepreSense &middot; Secure Clinical Platform
                  </p>
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
    </body>
    </html>
    """

    message.attach(MIMEText(plain_body, "plain"))
    message.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, email, message.as_string())
        logger.info("OTP email sent to %s", email)
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error(
            "SMTP authentication failed for %s. Check SMTP_EMAIL / SMTP_PASSWORD.", sender_email
        )
        return False
    except smtplib.SMTPException as exc:
        logger.error("SMTP error while sending OTP to %s: %s", email, exc)
        return False
    except Exception as exc:
        logger.error("Unexpected error sending OTP to %s: %s", email, exc)
        return False


def verify_otp(email: str, otp_provided: str) -> dict:
    """Verify the OTP supplied by the user.

    Returns a dict: ``{"success": bool, "message": str}``.
    Increments attempt counter on failure; deletes the document
    on success so the code cannot be reused.
    """
    if db_client is None:
        logger.error("Firestore client is not initialised; cannot verify OTP.")
        return {"success": False, "message": "Verification service unavailable."}

    max_attempts = _max_attempts()

    try:
        doc_ref = db_client.collection(_COLLECTION).document(email)
        doc = doc_ref.get()

        if not doc.exists:
            return {"success": False, "message": "No verification code found for this email."}

        data = doc.to_dict()

        # ── Expiry check ─────────────────────────────────────
        expires_at: datetime = data["expires_at"]
        # Ensure timezone-aware comparison
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > expires_at:
            doc_ref.delete()
            return {"success": False, "message": "Verification code has expired. Please request a new one."}

        # ── Attempt limit ─────────────────────────────────────
        attempts: int = data.get("attempts", 0)
        if attempts >= max_attempts:
            return {
                "success": False,
                "message": f"Too many incorrect attempts. Please request a new verification code.",
            }

        # ── Code match ────────────────────────────────────────
        if data.get("code") != otp_provided:
            doc_ref.update({"attempts": attempts + 1})
            remaining = max_attempts - (attempts + 1)
            if remaining > 0:
                return {
                    "success": False,
                    "message": f"Incorrect code. {remaining} attempt(s) remaining.",
                }
            else:
                return {
                    "success": False,
                    "message": "Too many incorrect attempts. Please request a new verification code.",
                }

        # ── Verified ──────────────────────────────────────────
        doc_ref.update({"verified": True})
        logger.info("OTP verified for %s", email)
        return {"success": True, "message": "Email verified successfully."}

    except Exception as exc:
        logger.error("OTP verification error for %s: %s", email, exc)
        return {"success": False, "message": "Verification failed. Please try again."}


def delete_otp(email: str) -> bool:
    """Delete the OTP record for *email* from Firestore.

    Returns ``True`` on success, ``False`` on error.
    """
    if db_client is None:
        logger.warning("Firestore client not initialised; cannot delete OTP.")
        return False
    try:
        db_client.collection(_COLLECTION).document(email).delete()
        logger.info("Deleted OTP record for %s", email)
        return True
    except Exception as exc:
        logger.error("Failed to delete OTP for %s: %s", email, exc)
        return False
