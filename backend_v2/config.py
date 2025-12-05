# backend_v2/config.py

from __future__ import annotations

import logging
from functools import lru_cache

from pydantic import ValidationError, Field, EmailStr
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Central application configuration for THE13TH Backend v2."""

    # General
    app_name: str = "THE13TH Backend v2"
    environment: str = "local"  # local | staging | production
    debug: bool = True

    # CORS
    # Note: Pydantic will parse comma-separated string or JSON array from env if provided.
    allowed_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]
    allowed_methods: list[str] = ["*"]
    allowed_headers: list[str] = ["*"]
    allow_credentials: bool = True

    # Security / JWT
    # from .env: jwt_secret_key=...
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expires_minutes: int = 60 * 24  # 1 day
    refresh_token_expires_days: int = 30

    # Stripe
    # from .env: stripe_api_key=...
    stripe_api_key: str
    # from .env: stripe_webhook_secret=...
    stripe_webhook_secret: str
    stripe_pilot_price_id: str | None = None

    # Core DB
    # from .env: the13th_db_url=sqlite:///./data/the13th_allinone.db
    the13th_db_url: str

    # Lead intake service
    # from .env: lead_intake_api_key=...
    lead_intake_api_key: str
    # from .env: lead_intake_api_url=http://127.0.0.1:7000
    lead_intake_api_url: str

    # Email / SendGrid
    # from .env: SENDGRID_API_KEY=...
    sendgrid_api_key: str
    # from .env: EMAIL_FROM_ADDRESS=pilot@the13thhq.com
    email_from_address: EmailStr
    # from .env: EMAIL_FROM_NAME=THE13TH Pilot Desk
    email_from_name: str = "THE13TH Pilot Desk"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",        # strict: all env keys must be declared as fields
        case_sensitive=False,  # so SENDGRID_API_KEY matches sendgrid_api_key
    )

    @property
    def database_url(self) -> str:
        """Alias for primary DB URL so the rest of the app can use settings.database_url."""
        return self.the13th_db_url


@lru_cache
def get_settings() -> Settings:
    """Load and cache settings once per process."""
    try:
        settings = Settings()
    except ValidationError as exc:
        logger.error("Failed to load Settings from environment: %s", exc, exc_info=True)
        raise

    logger.info(
        "Settings loaded for environment=%s debug=%s db=%s",
        settings.environment,
        settings.debug,
        settings.database_url,
    )
    return settings


# Eager, cached singleton for modules that just import `settings`
settings: Settings = get_settings()
