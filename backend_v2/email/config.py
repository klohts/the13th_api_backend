# backend_v2/email/config.py

from __future__ import annotations

import logging
from dataclasses import dataclass

from pydantic import EmailStr

from backend_v2.config import settings

logger = logging.getLogger(__name__)


@dataclass
class EmailSettings:
    """Thin wrapper around global Settings for email-specific config."""

    sendgrid_api_key: str
    email_from_address: EmailStr
    email_from_name: str


# Build a simple, typed settings object from the main app settings.
email_settings = EmailSettings(
    sendgrid_api_key=settings.sendgrid_api_key,
    email_from_address=settings.email_from_address,
    email_from_name=settings.email_from_name,
)

logger.info(
    "EmailSettings initialized for %s",
    email_settings.email_from_address,
)
