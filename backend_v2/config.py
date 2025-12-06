import logging
from typing import List, Optional

from pydantic import EmailStr, AnyHttpUrl
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
    # Env: DATABASE_URL
    database_url: str

    # Env: PUBLIC_BASE_URL
    public_base_url: AnyHttpUrl

    # --------------------------------------------------
    # Email / SMTP / SendGrid
    # --------------------------------------------------
    # Env: EMAIL_FROM
    email_from: EmailStr

    # Legacy compatibility: some code may use email_from_address
    # Env: EMAIL_FROM_ADDRESS (optional; falls back to EMAIL_FROM)
    email_from_address: Optional[EmailStr] = None

    # Optional display name for from header
    # Env: EMAIL_FROM_NAME
    email_from_name: Optional[str] = None

    # Env: EMAIL_SMTP_USERNAME
    email_smtp_username: str

    # Env: EMAIL_SMTP_PASSWORD
    email_smtp_password: str

    # Env: EMAIL_SMTP_HOST
    email_smtp_host: str = "smtp.sendgrid.net"

    # Env: EMAIL_SMTP_PORT
    email_smtp_port: int = 587

    # Env: EMAIL_USE_TLS
    email_use_tls: bool = True

    # Optional: direct SendGrid API usage
    # Env: SENDGRID_API_KEY
    sendgrid_api_key: Optional[str] = None

    # --------------------------------------------------
    # Auth / JWT
    # --------------------------------------------------
    # Env: JWT_SECRET_KEY
    jwt_secret_key: str

    # Env: JWT_ALGORITHM
    jwt_algorithm: str = "HS256"

    # --------------------------------------------------
    # Lead ingestion
    # --------------------------------------------------
    # Raw string from env; we parse into a list via property.
    # Env: INGESTION_API_KEYS
    ingestion_api_keys_raw: Optional[str] = None

    # Env: INGESTION_MAX_CSV_SIZE_MB
    ingestion_max_csv_size_mb: int = 5

    # --------------------------------------------------
    # Stripe
    # --------------------------------------------------
    # Env: STRIPE_API_KEY
    stripe_api_key: Optional[str] = None

    # Env: STRIPE_WEBHOOK_SECRET
    stripe_webhook_secret: Optional[str] = None

    # Env: STRIPE_PRICE_ID_PILOT_SETUP
    stripe_price_id_pilot_setup: Optional[str] = None

    # Env: STRIPE_PILOT_PRICE_ID
    stripe_pilot_price_id: str

    # --------------------------------------------------
    # Admin auth (for /admin routes etc.)
    # --------------------------------------------------
    # Env: ADMIN_API_TOKEN
    admin_api_token: Optional[str] = None

    # --------------------------------------------------
    # Pydantic settings config
    # --------------------------------------------------
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,  # DATABASE_URL -> database_url, SENDGRID_API_KEY -> sendgrid_api_key, etc.
        extra="ignore",
    )

    # --------------------------------------------------
    # Convenience properties
    # --------------------------------------------------
    @property
    def ingestion_api_keys(self) -> List[str]:
        """
        Return INGESTION_API_KEYS as a list of non-empty strings.
        Accepts:
          - None  -> []
          - ""    -> []
          - "a,b" -> ["a", "b"]
        """
        raw = self.ingestion_api_keys_raw
        if not raw:
            return []
        parts = [p.strip() for p in raw.split(",")]
        return [p for p in parts if p]

    def __init__(self, **values):
        super().__init__(**values)

        # Backwards compatibility: if email_from_address not explicitly set,
        # default it to email_from so email/config.py can rely on it.
        if self.email_from_address is None:
            self.email_from_address = self.email_from

        logger.info(
            "Settings loaded (debug=%s, public_base_url=%s)",
            self.debug,
            self.public_base_url,
        )
        logger.info("Ingestion API keys configured: %d", len(self.ingestion_api_keys))


settings = Settings()
