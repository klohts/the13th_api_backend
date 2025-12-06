from __future__ import annotations

import logging
from functools import lru_cache
from typing import Optional

from pydantic import AnyHttpUrl, EmailStr, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """
    Central configuration for THE13TH backend.

    - Reads from .env (local) and process environment (Render, etc.).
    - Accepts the existing env var names you already use.
    - Ignores extra env vars so adding new ones doesn’t break startup.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # -------------------------------------------------------------------------
    # Core app
    # -------------------------------------------------------------------------
    app_name: str = Field(default="THE13TH Backend v2", alias="APP_NAME")
    debug: bool = Field(default=False, alias="DEBUG")
    environment: str = Field(default="local", alias="ENVIRONMENT")

    jwt_secret_key: str = Field(..., alias="JWT_SECRET_KEY")

    # -------------------------------------------------------------------------
    # Database
    # -------------------------------------------------------------------------
    # Uses existing DATABASE_URL env var, exposed as the13th_db_url.
    the13th_db_url: str = Field(..., alias="DATABASE_URL")

    @property
    def database_url(self) -> str:
        """Backward-compatible alias used by older modules (e.g. db.py)."""
        return self.the13th_db_url

    # -------------------------------------------------------------------------
    # Public URLs
    # -------------------------------------------------------------------------
    public_base_url: AnyHttpUrl = Field(..., alias="PUBLIC_BASE_URL")

    # -------------------------------------------------------------------------
    # Email (SMTP) + optional SendGrid
    # -------------------------------------------------------------------------
    # From address and display name
    email_from_address: EmailStr = Field(..., alias="EMAIL_FROM")
    email_from_name: str = Field(
        default="THE13TH Pilot",
        alias="EMAIL_FROM_NAME",
    )

    # Backwards-compatible alias for any code still using settings.email_from
    @property
    def email_from(self) -> EmailStr:
        return self.email_from_address

    email_smtp_host: str = Field(default="smtp.gmail.com", alias="EMAIL_SMTP_HOST")
    email_smtp_port: int = Field(default=587, alias="EMAIL_SMTP_PORT")
    email_smtp_username: str = Field(..., alias="EMAIL_SMTP_USERNAME")
    email_smtp_password: str = Field(..., alias="EMAIL_SMTP_PASSWORD")
    email_use_tls: bool = Field(default=True, alias="EMAIL_USE_TLS")

    sendgrid_api_key: Optional[str] = Field(default=None, alias="SENDGRID_API_KEY")

    # -------------------------------------------------------------------------
    # Admin dashboard
    # -------------------------------------------------------------------------
    admin_dashboard_secret: str = Field(..., alias="ADMIN_DASHBOARD_SECRET")

    # -------------------------------------------------------------------------
    # Stripe (pilot payments)
    # -------------------------------------------------------------------------
    stripe_api_key: str = Field(..., alias="STRIPE_API_KEY")
    stripe_webhook_secret: str = Field(..., alias="STRIPE_WEBHOOK_SECRET")
    stripe_pilot_price_id: str = Field(..., alias="STRIPE_PILOT_PRICE_ID")

    # New: redirect URLs used by pilot_admin when creating Checkout sessions
    stripe_success_url: AnyHttpUrl = Field(..., alias="STRIPE_SUCCESS_URL")
    stripe_cancel_url: AnyHttpUrl = Field(..., alias="STRIPE_CANCEL_URL")

    # -------------------------------------------------------------------------
    # Lead intake + ingestion
    # -------------------------------------------------------------------------
    # Optional lead intake service wiring (can be empty for now).
    lead_intake_api_key: Optional[str] = Field(
        default=None,
        alias="LEAD_INTAKE_API_KEY",
    )
    # Accept empty string or None, don’t enforce URL yet.
    lead_intake_api_url: Optional[str] = Field(
        default=None,
        alias="LEAD_INTAKE_API_URL",
    )

    # Ingestion service:
    #   INGESTION_API_KEYS=key1,key2
    #   INGESTION_MAX_CSV_SIZE_MB=5
    ingestion_api_keys_raw: Optional[str] = Field(
        default=None,
        alias="INGESTION_API_KEYS",
    )
    ingestion_max_csv_size_mb: int = Field(
        default=5,
        alias="INGESTION_MAX_CSV_SIZE_MB",
    )

    @property
    def ingestion_api_keys(self) -> list[str]:
        """
        Returns a list of API keys from the comma-separated env string.
        Safe if env is missing or empty.
        """
        if not self.ingestion_api_keys_raw:
            return []
        return [
            key.strip()
            for key in self.ingestion_api_keys_raw.split(",")
            if key.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    """
    Cached settings loader so config is evaluated once per process.
    """
    settings = Settings()
    logger.info(
        "Settings loaded (env=%s, debug=%s)",
        settings.environment,
        settings.debug,
    )
    return settings


# Singleton used everywhere else
settings: Settings = get_settings()
