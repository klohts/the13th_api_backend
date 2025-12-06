# backend_v2/email/service.py
from __future__ import annotations

import logging
from typing import Any, Dict

from pydantic import EmailStr

from backend_v2.schemas.pilot import PilotRequest
from backend_v2.config import settings
from .client import email_client

logger = logging.getLogger(__name__)

# === Pilot request confirmation (already live) ===

PILOT_TEMPLATE_NAME = "pilot_confirmation.html"
PILOT_SUBJECT = "Your 7-Day Revenue Intelligence Pilot with THE13TH"


def build_pilot_context(pilot: PilotRequest) -> Dict[str, Any]:
    """Map PilotRequest into template context."""
    full_name = f"{pilot.first_name} {pilot.last_name}".strip()
    return {
        "full_name": full_name,
        "first_name": pilot.first_name,
        "last_name": pilot.last_name,
        "brokerage_name": pilot.brokerage_name,
        "website": pilot.website or "",
        "agents_on_team": pilot.agents_on_team or "Not specified",
        "monthly_online_leads": pilot.monthly_online_leads or "Not specified",
        "primary_focus": pilot.primary_focus or "Not specified",
        "main_problem": pilot.main_problem or "",
        "anything_special": pilot.anything_special or "",
    }


def send_pilot_confirmation(pilot: PilotRequest) -> None:
    """
    Send confirmation email to the broker after they submit a pilot request.

    Raises exceptions on failure; caller should handle/log as appropriate.
    """
    to_email: EmailStr = pilot.work_email
    context = build_pilot_context(pilot)

    plain_text_fallback = (
        f"Hi {pilot.first_name},\n\n"
        "Thanks for requesting a 7-day Revenue Intelligence Pilot with THE13TH. "
        "We’ll review your details and email next steps shortly.\n\n"
        "– THE13TH Pilot Desk"
    )

    logger.info("Sending pilot confirmation email to %s", to_email)

    email_client.send_html_email(
        to_email=to_email,
        subject=PILOT_SUBJECT,
        template_name=PILOT_TEMPLATE_NAME,
        context=context,
        plain_text_fallback=plain_text_fallback,
    )


# === Post-payment onboarding automation (new) ===

PILOT_ONBOARDING_TEMPLATE_NAME = "pilot_onboarding.html"
PILOT_ONBOARDING_SUBJECT = "Welcome — Your THE13TH Revenue Intelligence Pilot Is Live"


def build_pilot_onboarding_context(
    *,
    full_name: str,
    brokerage_name: str,
) -> Dict[str, Any]:
    """
    Build context for the post-payment onboarding email.

    This is intentionally lightweight and only depends on primitives so it can
    be called from webhooks, admin tools, or background jobs.
    """
    full_name_clean = (full_name or "").strip()
    first_name = full_name_clean.split(" ", 1)[0] if full_name_clean else "there"

    return {
        "full_name": full_name_clean or first_name,
        "first_name": first_name,
        "brokerage_name": brokerage_name or "your brokerage",
        "support_email": str(settings.email_from_address),
    }


def send_pilot_onboarding_email(
    *,
    to_email: EmailStr,
    full_name: str,
    brokerage_name: str,
) -> None:
    """
    Send the first onboarding email after a pilot is activated (Stripe payment
    succeeded and the pilot status has been flipped to ACTIVE).

    This should be called exactly once per successful pilot activation.
    """
    context = build_pilot_onboarding_context(
        full_name=full_name,
        brokerage_name=brokerage_name,
    )

    plain_text_fallback = (
        f"Hi {context['first_name']},\n\n"
        "Your 7-day Revenue Intelligence Pilot with THE13TH is now active.\n\n"
        "Over the next 24 hours we’ll:\n"
        "• Connect THE13TH to one lead inbox + one lead source\n"
        "• Turn on intelligent first-touch and follow-up email support\n"
        "• Start watching lead flow and agent response speed in your pilot dashboard\n\n"
        f"If you’d like to get a head start, reply to this email with:\n"
        "• The inbox you’d like us to connect\n"
        "• Your primary lead source for the pilot week\n\n"
        f"If you have any questions, you can always reach us at {context['support_email']}.\n\n"
        "– THE13TH Pilot Desk"
    )

    logger.info(
        "Sending pilot onboarding email to %s for brokerage=%s",
        to_email,
        brokerage_name,
    )

    email_client.send_html_email(
        to_email=to_email,
        subject=PILOT_ONBOARDING_SUBJECT,
        template_name=PILOT_ONBOARDING_TEMPLATE_NAME,
        context=context,
        plain_text_fallback=plain_text_fallback,
    )
