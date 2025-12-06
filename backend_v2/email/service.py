from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import EmailStr
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Content

# IMPORTANT: use the shared email settings loader
from backend_v2.email.config import get_email_settings

logger = logging.getLogger("the13th.backend_v2.email.service")

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


# ---------------------------------------------------------------------------
# Local dataclass kept for compatibility (not used to read env directly)
# ---------------------------------------------------------------------------


@dataclass
class EmailSettingsCompat:
    """Compatibility holder for email settings used by this service layer."""

    sendgrid_api_key: str
    from_email: EmailStr
    from_name: str
    admin_email: Optional[EmailStr]


def _get_settings() -> Optional[EmailSettingsCompat]:
    """
    Load email settings from backend_v2.email.config.

    This wraps get_email_settings() so service.py always uses the single
    central configuration source, which is already initialised at startup.
    """
    try:
        raw = get_email_settings()
    except Exception as exc:  # defensive: misconfigured env etc.
        logger.error("Failed to load EmailSettings: %s", exc, exc_info=True)
        return None

    # Be tolerant of different attribute naming conventions.
    sendgrid_api_key = (
        getattr(raw, "sendgrid_api_key", None)
        or getattr(raw, "SENDGRID_API_KEY", None)
    )
    from_email = (
        getattr(raw, "from_email", None)
        or getattr(raw, "EMAIL_FROM", None)
    )
    from_name = (
        getattr(raw, "from_name", None)
        or getattr(raw, "EMAIL_FROM_NAME", None)
        or "THE13TH Pilot Desk"
    )
    admin_email = (
        getattr(raw, "admin_email", None)
        or getattr(raw, "EMAIL_ADMIN", None)
    )

    if not sendgrid_api_key or not from_email:
        logger.error(
            "Email settings incomplete (SENDGRID_API_KEY or EMAIL_FROM missing); "
            "emails will be skipped."
        )
        return None

    return EmailSettingsCompat(
        sendgrid_api_key=sendgrid_api_key,
        from_email=EmailStr(str(from_email)),
        from_name=str(from_name),
        admin_email=EmailStr(str(admin_email)) if admin_email else None,
    )


def _init_jinja() -> Optional[Environment]:
    if not TEMPLATES_DIR.exists():
        logger.error("Email templates directory does not exist: %s", TEMPLATES_DIR)
        return None

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
        enable_async=False,
    )
    return env


JINJA_ENV: Optional[Environment] = _init_jinja()


def _render_template(template_name: str, context: Mapping[str, Any]) -> str:
    if JINJA_ENV is None:
        raise RuntimeError(
            "Jinja environment is not initialised; templates directory missing"
        )

    try:
        template = JINJA_ENV.get_template(template_name)
    except Exception as exc:
        logger.error(
            "Failed to load email template %s: %s",
            template_name,
            exc,
            exc_info=True,
        )
        raise

    try:
        return template.render(**context)
    except Exception as exc:  # defensive
        logger.error(
            "Failed to render email template %s: %s",
            template_name,
            exc,
            exc_info=True,
        )
        raise


def _send_email(
    *,
    to_email: str,
    subject: str,
    html_body: str,
    plain_body: Optional[str] = None,
    cc: Optional[list[str]] = None,
) -> None:
    """
    Core SendGrid send wrapper.

    Never raises to the caller; failures are logged as errors so the
    pilot flow keeps running even if email fails.
    """
    settings = _get_settings()
    if settings is None:
        logger.error(
            "Email settings not available; skipping send to %s (subject=%s)",
            to_email,
            subject,
        )
        return

    message = Mail(
        from_email=(settings.from_email, settings.from_name),
        to_emails=to_email,
        subject=subject,
        html_content=html_body,
    )

    if plain_body:
        message.add_content(Content("text/plain", plain_body))

    if cc:
        # Mail.cc expects a list of email strings
        message.cc = cc

    try:
        client = SendGridAPIClient(settings.sendgrid_api_key)
        response = client.send(message)
    except Exception as exc:  # network / API errors
        logger.error(
            "Failed to send email via SendGrid to %s: %s",
            to_email,
            exc,
            exc_info=True,
        )
        return

    if response.status_code >= 400:
        logger.error(
            "SendGrid responded with error for %s: status=%s body=%s",
            to_email,
            response.status_code,
            getattr(response, "body", b"")[:1000],
        )
    else:
        logger.info(
            "Email sent successfully: to=%s subject=%s status=%s",
            to_email,
            subject,
            response.status_code,
        )


def _safe_attr(obj: Any, name: str, default: Any = "") -> Any:
    """Return attribute or dict key, tolerant of different payload types."""
    if obj is None:
        return default
    if hasattr(obj, name):
        return getattr(obj, name)
    if isinstance(obj, Mapping) and name in obj:
        return obj[name]
    return default


# ============================================================
# Public email functions used by the rest of backend_v2
# ============================================================


def send_pilot_confirmation(pilot_request: Any) -> None:
    """Send confirmation email to the brokerage that submitted a pilot request."""
    to_email = _safe_attr(pilot_request, "contact_email") or _safe_attr(
        pilot_request, "email"
    )
    full_name = _safe_attr(pilot_request, "contact_name") or _safe_attr(
        pilot_request, "full_name"
    )
    brokerage_name = _safe_attr(pilot_request, "brokerage_name")
    problem = _safe_attr(pilot_request, "problem_notes") or _safe_attr(
        pilot_request, "problem"
    )
    team_size = _safe_attr(pilot_request, "agents_count") or _safe_attr(
        pilot_request, "team_size"
    )
    lead_volume = _safe_attr(pilot_request, "lead_volume")

    if not to_email:
        logger.error(
            "send_pilot_confirmation called without a contact email; payload=%r",
            pilot_request,
        )
        return

    context = {
        "full_name": full_name or "there",
        "brokerage_name": brokerage_name or "your brokerage",
        "problem": problem or "Slow follow-up and lead leakage",
        "team_size": team_size or "your team",
        "lead_volume": lead_volume or "your online leads",
    }

    html_body = _render_template("pilot_confirmation.html", context)
    subject = "We’ve received your Revenue Intelligence Pilot request"

    _send_email(
        to_email=to_email,
        subject=subject,
        html_body=html_body,
    )


def send_admin_pilot_notification(pilot_request: Any) -> None:
    """Send internal notification to THE13TH admin when a pilot is requested."""
    settings = _get_settings()
    admin_email = settings.admin_email if settings else None

    if not admin_email:
        logger.warning(
            "Admin email not configured; skipping admin pilot notification for %r",
            pilot_request,
        )
        return

    to_email = str(admin_email)
    full_name = _safe_attr(pilot_request, "contact_name") or _safe_attr(
        pilot_request, "full_name"
    )
    brokerage_name = _safe_attr(pilot_request, "brokerage_name")
    problem = _safe_attr(pilot_request, "problem_notes") or _safe_attr(
        pilot_request, "problem"
    )
    team_size = _safe_attr(pilot_request, "agents_count") or _safe_attr(
        pilot_request, "team_size"
    )
    lead_volume = _safe_attr(pilot_request, "lead_volume")
    source_tag = _safe_attr(pilot_request, "source")

    context = {
        "full_name": full_name or "",
        "brokerage_name": brokerage_name or "",
        "problem": problem or "",
        "team_size": team_size or "",
        "lead_volume": lead_volume or "",
        "source": source_tag or "",
        "raw": pilot_request,
    }

    html_body = _render_template("admin_pilot_notification.html", context)
    subject = f"[THE13TH] New Revenue Intelligence Pilot request – {brokerage_name}"

    _send_email(
        to_email=to_email,
        subject=subject,
        html_body=html_body,
    )


def send_pilot_checkout_email(
    to_email: str,
    checkout_url: str,
    brokerage_name: Optional[str] = None,
    full_name: Optional[str] = None,
) -> None:
    """
    Send the Stripe checkout link to the brokerage once approved.

    Called from pilot_admin.approve_pilot with explicit to_email / brokerage_name.
    """
    if not to_email:
        logger.error(
            "send_pilot_checkout_email called without a contact email; "
            "to_email=%r checkout_url=%r",
            to_email,
            checkout_url,
        )
        return

    context = {
        "full_name": full_name or "there",
        "brokerage_name": brokerage_name or "your brokerage",
        "checkout_url": checkout_url,
    }

    html_body = _render_template("pilot_checkout.html", context)
    subject = "Confirm your THE13TH Revenue Intelligence Pilot"

    _send_email(
        to_email=to_email,
        subject=subject,
        html_body=html_body,
    )


def send_pilot_onboarding_email(
    to_email: str, full_name: str, brokerage_name: str
) -> None:
    """Send onboarding email when Stripe marks the pilot as active."""
    if not to_email:
        logger.error("send_pilot_onboarding_email called with empty to_email")
        return

    context = {
        "full_name": full_name or "there",
        "brokerage_name": brokerage_name or "your brokerage",
    }

    html_body = _render_template("pilot_onboarding.html", context)
    subject = "Your THE13TH Revenue Intelligence Pilot is now live"

    _send_email(
        to_email=to_email,
        subject=subject,
        html_body=html_body,
    )


def send_pilot_summary_email(pilot: Any, summary_context: Mapping[str, Any]) -> None:
    """
    Send the 7-day pilot summary + recommendations.

    Wired for future use; safe even if not yet invoked.
    """
    to_email = _safe_attr(pilot, "contact_email") or _safe_attr(pilot, "email")
    full_name = _safe_attr(pilot, "contact_name") or _safe_attr(pilot, "full_name")
    brokerage_name = _safe_attr(pilot, "brokerage_name")

    if not to_email:
        logger.error(
            "send_pilot_summary_email called without a contact email; payload=%r",
            pilot,
        )
        return

    context = {
        "full_name": full_name or "there",
        "brokerage_name": brokerage_name or "your brokerage",
        **summary_context,
    }

    html_body = _render_template("pilot_summary.html", context)
    subject = "Your Revenue Intelligence Pilot results & recommendations"

    _send_email(
        to_email=to_email,
        subject=subject,
        html_body=html_body,
    )
