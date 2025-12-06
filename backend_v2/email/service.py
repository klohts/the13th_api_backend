from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Mapping, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Content

from backend_v2.email import config as email_config

logger = logging.getLogger("the13th.backend_v2.email.service")

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


# ---------------------------------------------------------------------------
# Settings loader
# ---------------------------------------------------------------------------


class EmailSettingsCompat:
    def __init__(
        self,
        sendgrid_api_key: str,
        from_email: str,
        from_name: str,
        admin_email: Optional[str] = None,
    ) -> None:
        self.sendgrid_api_key = sendgrid_api_key
        self.from_email = from_email
        self.from_name = from_name
        self.admin_email = admin_email


def _unwrap_secret(value: Any) -> Optional[str]:
    if value is None:
        return None
    if hasattr(value, "get_secret_value"):
        try:
            return value.get_secret_value()
        except Exception:
            return None
    return str(value)


def _first_non_empty(*values: Any) -> Optional[str]:
    for v in values:
        v = _unwrap_secret(v)
        if v:
            return v
    return None


def _load_raw_settings() -> Optional[Any]:
    """
    Try multiple ways to get a settings object from backend_v2.email.config:

    - email_settings attribute (preferred)
    - get_email_settings() function
    - EmailSettings() class constructor
    """
    raw = getattr(email_config, "email_settings", None)
    if raw is not None:
        return raw

    getter = getattr(email_config, "get_email_settings", None)
    if callable(getter):
        try:
            raw = getter()
            if raw is not None:
                logger.info("Loaded email settings via get_email_settings()")
                return raw
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Error calling email_config.get_email_settings(): %s",
                exc,
                exc_info=True,
            )

    cls = getattr(email_config, "EmailSettings", None)
    if isinstance(cls, type):
        try:
            raw = cls()
            logger.info("Instantiated email settings via EmailSettings()")
            return raw
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Error instantiating email_config.EmailSettings(): %s",
                exc,
                exc_info=True,
            )

    return None


def _get_settings() -> Optional[EmailSettingsCompat]:
    """
    Load email settings from backend_v2.email.config, with env fallbacks.
    """
    raw = _load_raw_settings()

    sendgrid_api_key = _first_non_empty(
        getattr(raw, "sendgrid_api_key", None),
        getattr(raw, "SENDGRID_API_KEY", None),
        getattr(raw, "api_key", None),
        os.getenv("SENDGRID_API_KEY"),
        os.getenv("EMAIL_SENDGRID_API_KEY"),
    )

    from_email = _first_non_empty(
        getattr(raw, "from_email", None),
        getattr(raw, "EMAIL_FROM", None),
        getattr(raw, "sender", None),
        os.getenv("EMAIL_FROM"),
    )

    from_name = _first_non_empty(
        getattr(raw, "from_name", None),
        getattr(raw, "EMAIL_FROM_NAME", None),
        os.getenv("EMAIL_FROM_NAME"),
        "THE13TH Pilot Desk",
    )

    admin_email = _first_non_empty(
        getattr(raw, "admin_email", None),
        getattr(raw, "EMAIL_ADMIN", None),
        os.getenv("EMAIL_ADMIN"),
    )

    if not sendgrid_api_key or not from_email:
        logger.error(
            "Email settings incomplete (SendGrid API key or from_email missing); "
            "emails will be skipped. "
            "raw_settings_present=%s env_keys=%s",
            bool(raw),
            {
                "SENDGRID_API_KEY": bool(os.getenv("SENDGRID_API_KEY")),
                "EMAIL_FROM": bool(os.getenv("EMAIL_FROM")),
            },
        )
        return None

    return EmailSettingsCompat(
        sendgrid_api_key=sendgrid_api_key,
        from_email=str(from_email),
        from_name=str(from_name),
        admin_email=str(admin_email) if admin_email else None,
    )


# ---------------------------------------------------------------------------
# Jinja environment
# ---------------------------------------------------------------------------


def _init_jinja() -> Optional[Environment]:
    if not TEMPLATES_DIR.exists():
        logger.error("Email templates directory does not exist: %s", TEMPLATES_DIR)
        return None

    return Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
        enable_async=False,
    )


JINJA_ENV: Optional[Environment] = _init_jinja()


def _render_template(template_name: str, context: Mapping[str, Any]) -> str:
    """
    Render a template but never raise; fall back to a plain-text body on error.
    """
    if JINJA_ENV is None:
        logger.error(
            "Jinja environment is not initialised; templates directory missing"
        )
        return f"{template_name} – plain text fallback\n\n{context}"

    try:
        template = JINJA_ENV.get_template(template_name)
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "Failed to load email template %s: %s",
            template_name,
            exc,
            exc_info=True,
        )
        return f"{template_name} – plain text fallback\n\n{context}"

    try:
        return template.render(**context)
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "Failed to render email template %s: %s",
            template_name,
            exc,
            exc_info=True,
        )
        return f"{template_name} – plain text fallback\n\n{context}"


# ---------------------------------------------------------------------------
# Core SendGrid send
# ---------------------------------------------------------------------------


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

    Never raises to the caller; failures are logged as errors so routes keep
    returning 200 even if email is misconfigured.
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
        message.cc = cc

    try:
        client = SendGridAPIClient(settings.sendgrid_api_key)
        response = client.send(message)
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "Failed to send email via SendGrid to %s: %s",
            to_email,
            exc,
            exc_info=True,
        )
        return

    status_code = getattr(response, "status_code", None)
    body = getattr(response, "body", b"")[:1000]

    if status_code is None or status_code >= 400:
        logger.error(
            "SendGrid responded with error for %s: status=%s body=%s",
            to_email,
            status_code,
            body,
        )
    else:
        logger.info(
            "Email sent successfully: to=%s subject=%s status=%s",
            to_email,
            subject,
            status_code,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_attr(obj: Any, name: str, default: Any = "") -> Any:
    """Return attribute or dict key, tolerant of different payload types."""
    if obj is None:
        return default
    if hasattr(obj, name):
        return getattr(obj, name)
    if isinstance(obj, Mapping) and name in obj:
        return obj[name]
    return default


# ---------------------------------------------------------------------------
# Public email functions
# ---------------------------------------------------------------------------


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
    settings_obj = _get_settings()
    admin_email = settings_obj.admin_email if settings_obj else None

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
    """Send the Stripe checkout link to the brokerage once approved."""
    if not to_email:
        logger.error(
            "send_pilot_checkout_email called without a contact email; "
            "checkout_url=%r",
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
    to_email: str,
    full_name: str,
    brokerage_name: str,
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


def send_pilot_summary_email(
    pilot: Any,
    summary_context: Mapping[str, Any],
) -> None:
    """
    Send the 7-day pilot summary + recommendations.
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

def send_lead_first_touch_email(
    *,
    to_email: str,
    full_name: str,
    tenant_key: str,
    source: str,
) -> None:
    """Send the initial first-touch email to a new lead.

    This uses the same underlying email settings as the pilot emails, but
    keeps the body simple and on-brand for THE13TH.
    """
    # Import lazily to avoid circulars if any.
    from email.utils import formataddr  # type: ignore[import]

    try:
        display_name = full_name or "there"
    except Exception:
        display_name = "there"

    subject = "Thanks — we’ve received your inquiry"

    html_body = f"""        <html>
      <body style="margin:0;padding:0;background-color:#050010;">
        <table width="100%" cellspacing="0" cellpadding="0" style="background:radial-gradient(circle at top left,#4b0082,#0a0014 60%);padding:24px 0;">
          <tr>
            <td align="center">
              <table width="640" cellspacing="0" cellpadding="0" style="background-color:#050010;border-radius:24px;border:1px solid rgba(168,85,247,0.4);padding:32px 40px;font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:#e5e7eb;">
                <tr>
                  <td style="text-align:left;padding-bottom:24px;border-bottom:1px solid rgba(148,163,184,0.25);">
                    <div style="font-size:11px;letter-spacing:0.3em;text-transform:uppercase;color:#e9d5ff;margin-bottom:12px;">Lead received</div>
                    <div style="font-size:26px;font-weight:700;color:#FCE6C8;">
                      Thanks, {display_name} — your inquiry is in.
                    </div>
                    <p style="font-size:13px;line-height:1.7;color:#e5e7eb;margin-top:16px;margin-bottom:0;">
                      One of the agents on this brokerage is reviewing your details now. You&apos;ll get a follow-up shortly with next steps and a clear way to move forward.
                    </p>
                  </td>
                </tr>
                <tr>
                  <td style="padding-top:24px;padding-bottom:8px;">
                    <div style="font-size:11px;letter-spacing:0.25em;text-transform:uppercase;color:#c4b5fd;margin-bottom:12px;">What happens next</div>
                    <ul style="padding-left:20px;margin:0;font-size:13px;line-height:1.7;color:#e5e7eb;">
                      <li>You&apos;ll receive a reply from the brokerage team shortly.</li>
                      <li>Your details are safely stored in their system, monitored by THE13TH.</li>
                      <li>If you reply to this email, the team and THE13TH keep the conversation on track.</li>
                    </ul>
                  </td>
                </tr>
                <tr>
                  <td style="padding-top:24px;font-size:11px;color:#9ca3af;">
                    <div style="margin-bottom:4px;">This inbox is assisted by THE13TH – AI Admin &amp; Revenue Intelligence.</div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
        </table>
      </body>
    </html>
    """  # noqa: E501

    # Use the internal low-level sender to reuse existing settings + logging.
    try:
        _send_email(
            to_email=to_email,
            subject=subject,
            html_body=html_body,
        )
        logger.info(
            "First-touch email sent to %s for tenant=%s source=%s",
            to_email,
            tenant_key,
            source,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "Failed to send first-touch email to %s: %s",
            to_email,
            exc,
        )
        raise
