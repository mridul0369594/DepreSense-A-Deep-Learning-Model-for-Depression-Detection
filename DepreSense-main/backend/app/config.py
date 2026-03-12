"""
Application configuration loaded from environment variables / .env file.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration — values are read from the .env file or
    environment variables at startup."""

    # ── Firebase ────────────────────────────────────────────
    FIREBASE_CREDENTIALS_PATH: str = "config/firebase-service-account.json"
    FIREBASE_API_KEY: str = ""  # Firebase Web API key (for REST auth)

    # ── Model ───────────────────────────────────────────────
    MODEL_PATH: str = "../output/model"
    SHAP_BG_PATH: str = "../output/assets/shap_bg_ec.npy"

    # ── CORS ────────────────────────────────────────────────
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # ── App ─────────────────────────────────────────────────
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    # ── File uploads ────────────────────────────────────────
    MAX_FILE_SIZE_MB: int = 50
    UPLOAD_DIR: str = "uploads"

    # ── Email / SMTP ─────────────────────────────────────────
    SMTP_EMAIL: str = ""           # Sender address (Gmail recommended)
    SMTP_PASSWORD: str = ""        # App-specific password
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 465

    # ── OTP ─────────────────────────────────────────────────
    OTP_EXPIRY_MINUTES: int = 5    # OTP lifetime in minutes
    OTP_MAX_ATTEMPTS: int = 3      # Max wrong-code tries before lockout

    # ── Pydantic-settings configuration ─────────────────────
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def allowed_origins_list(self) -> list[str]:
        """Return ALLOWED_ORIGINS as a list of strings."""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]


# Singleton instance used across the application
settings = Settings()
