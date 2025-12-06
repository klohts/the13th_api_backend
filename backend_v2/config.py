import logging
from typing import List, Optional

from pydantic import EmailStr, field_validator, AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("the13th.backend_v2.config")


class Settings(BaseSettings):
    # --------------------------------------------------
    # Core app settings
    # --------------------------------------------------
    app_name: str = "THE13TH Backend v2"
    debug: bool = False

    # --------------------------------------------------
    # Database + base URL
    # --------------------------------------------------
    # Environment: DATABASE_URL
    database_url: str

    # Environment: PUBLIC_BASE_URL
    public_base_url: AnyHttpUrl

    # --------------------------------------------------
    # Email / SMTP
    # --------------------------------------------------
    # Environment: EMAIL_FROM
    email_from: EmailStr

    # Environment: EMAIL_SMTP_USERNAME
    email_smtp_username: str

    # Environment: EMAIL_SMTP_PASSWORD
    email_smtp_password: str

    # Environment: EMAIL_SMTP_HOST
    email_smtp_host: str = "smtp.sendgrid.net"

    # Environment: EMAIL_SMTP_PORT
    email_smtp_port: int = 587

    # Environment: EMAIL_USE_TLS
    email_use_tls: bool = True

    # --------------------------------------------------
    # Auth / JWT
    # --------------------------------------------------
    # Environment: JWT_SECRET_KEY
    jwt_secret_key: str

    # Environment: JWT_ALGORITHM
    jwt_algorithm: str = "HS256"

    # --------------------------------------------------
    # Lead ingestion
    # --------------------------------------------------
    # Environment: INGESTION_API_KEYS (comma-separated)
    ingestion_api_keys: List[str] = []

    # Environment: INGESTION_MAX_CSV_SIZE_MB
    ingestion_max_csv_size_mb: int = 5

    # --------------------------------------------------
    # Stripe
    # --------------------------------------------------
    # Environment: STRIPE_API_KEY
    stripe_api_key: Optional[str] = None

    # Environment: STRIPE_WEBHOOK_SECRET
    stripe_webhook_secret: Optional[str] = None

    # Environment: STRIPE_PRICE_ID_PILOT_SETUP
    stripe_price_id_pilot_setup: Optional[str] = None

    # --------------------------------------------------
    # Admin auth (for /admin routes etc.)
    # --------------------------------------------------
    # Environment: ADMIN_API_TOKEN
    admin_api_token: Optional[str] = None

    # --------------------------------------------------
    # Pydantic settings config
    # --------------------------------------------------
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,  # maps DATABASE_URL -> database_url, etc.
        extra="ignore",
    )

    # --------------------------------------------------
    # Validators
    # --------------------------------------------------
    @field_validator("ingestion_api_keys", mode="before")
    @classmethod
    def split_ingestion_api_keys(cls, v: object) -> List[str]:
        """
        Accept either a comma-separated string or a list for INGESTION_API_KEYS.
        """
        if v is None:
            return []
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            return [k.strip() for k in v.split(",") if k.strip()]
        raise TypeError("INGESTION_API_KEYS must be a comma-separated string or a list")


settings = Settings()
logger.info(
    "Settings loaded (debug=%s, public_base_url=%s)",
    settings.debug,
    settings.public_base_url,
)
