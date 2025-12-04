# backend_v2/email/client.py
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import EmailStr, ValidationError

from .config import email_settings
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


class EmailTemplateRenderer:
    """Renders Jinja2-based email templates from the local templates directory."""

    def __init__(self) -> None:
        self._env = Environment(
            loader=FileSystemLoader(str(TEMPLATES_DIR)),
            autoescape=select_autoescape(["html", "xml"]),
        )

    def render(self, template_name: str, context: Dict[str, Any]) -> str:
        try:
            template = self._env.get_template(template_name)
        except Exception as exc:
            logger.error("Email template '%s' not found: %s", template_name, exc)
            raise

        try:
            return template.render(**context)
        except Exception as exc:
            logger.error("Failed to render template '%s': %s", template_name, exc)
            raise


class EmailClient:
    """Thin wrapper around SendGrid API with logging and error handling."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        if email_settings is None:
            raise RuntimeError("EmailSettings not initialized; check environment configuration.")

        self._api_key = api_key or email_settings.sendgrid_api_key
        self._sg = SendGridAPIClient(self._api_key)
        self._renderer = EmailTemplateRenderer()
        self._from_email = Email(
            email=email_settings.email_from_address,
            name=email_settings.email_from_name,
        )

    def send_html_email(
        self,
        to_email: EmailStr,
        subject: str,
        template_name: str,
        context: Dict[str, Any],
        plain_text_fallback: Optional[str] = None,
    ) -> None:
        """Render a template and send as HTML email."""
        try:
            rendered_html = self._renderer.render(template_name, context)
        except Exception:
            logger.exception("Aborting send_html_email due to template rendering failure.")
            raise

        plain_text = plain_text_fallback or "View this email in an HTML-capable client."

        try:
            to = To(str(to_email))
            message = Mail(
                from_email=self._from_email,
                to_emails=to,
                subject=subject,
            )
            message.add_content(Content("text/plain", plain_text))
            message.add_content(Content("text/html", rendered_html))

            response = self._sg.send(message)
            logger.info(
                "Email sent to %s with status %s",
                to_email,
                response.status_code,
            )
        except ValidationError as exc:
            logger.error("Invalid email parameters: %s", exc)
            raise
        except Exception as exc:  # pragma: no cover
            logger.exception("Error sending email via SendGrid: %s", exc)
            raise


# Singleton email client for reuse
email_client = EmailClient()
