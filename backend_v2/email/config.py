import logging
from typing import Optional

from pydantic import BaseModel, EmailStr

from backend_v2.config import settings

logger = logging.getLogger("backend_v2.email.config")


class EmailSettings(BaseModel):
    """
    Centralized email configuration derived from Settings.
    This supports both SMTP and optional SendGrid API key usage.
    """

    from_address: EmailStr
    from_name: Optional[str] = None

    smtp_username: str
    smtp_password: str
    smtp_host: str
    smtp_port: int
    use_tls: bool = True

    sendgrid_api_key: Optional[str] = None


_email_settings: Optional[EmailSettings] = None


def init_email_settings() -> EmailSettings:
    """
    Initialize the global EmailSettings instance from backend_v2.config.settings.
    Safe to call multiple times; initialization is idempotent.
    """
    global _email_settings

    if _email_settings is not None:
        return _email_settings

    # Use email_from_address if present, otherwise email_from
    from_address: EmailStr = settings.email_from_address or settings.email_from  # type: ignore[assignment]

    email_from_name: Optional[str] = settings.email_from_name
    if not email_from_name:
        # fallback to address as name if none provided
        email_from_name = str(from_address)

    _email_settings = EmailSettings(
        from_address=from_address,
        from_name=email_from_name,
        smtp_username=settings.email_smtp_username,
        smtp_password=settings.email_smtp_password,
        smtp_host=settings.email_smtp_host,
        smtp_port=settings.email_smtp_port,
        use_tls=settings.email_use_tls,
        sendgrid_api_key=settings.sendgrid_api_key,
    )

    logger.info(
        "EmailSettings initialized for %s (host=%s, port=%s, use_tls=%s)",
        _email_settings.from_address,
        _email_settings.smtp_host,
        _email_settings.smtp_port,
        _email_settings.use_tls,
    )

    return _email_settings


def get_email_settings() -> EmailSettings:
    """
    Accessor used by email.service and other callers.
    Ensures settings are initialized before returning.
    """
    return init_email_settings()
