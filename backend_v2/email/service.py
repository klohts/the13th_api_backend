from __future__ import annotations

import logging
from typing import Any, Dict, Optional

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


# === Pilot checkout email (admin approval → Stripe payment link) ===

PILOT_CHECKOUT_TEMPLATE_NAME = "pilot_checkout.html"
PILOT_CHECKOUT_SUBJECT = "THE13TH Pilot Approved — Complete Your Setup"


def build_pilot_checkout_context(
    *,
    brokerage_name: Optional[str],
    checkout_url: str,
) -> Dict[str, Any]:
    """
    Build context for the checkout email sent after admin approval.

    Keeps dependencies minimal so this can be called from routers, admin tools,
    or background jobs without needing a full PilotRequest object.
    """
    return {
        "brokerage_name": brokerage_name or "your brokerage",
        "checkout_url": checkout_url,
        "support_email": str(settings.email_from_address),
    }


def send_pilot_checkout_email(
    to_email: EmailStr,
    checkout_url: str,
    brokerage_name: Optional[str] = None,
) -> None:
    """
    Send Stripe checkout link to the broker after an admin approves their pilot.

    Signature is positional-friendly for existing calls in routers:
        send_pilot_checkout_email(pilot.work_email, checkout_url, pilot.brokerage_name)
    """
    if not checkout_url:
        raise ValueError("checkout_url is required")

    context = build_pilot_checkout_context(
        brokerage_name=brokerage_name,
        checkout_url=checkout_url,
    )

    plain_text_fallback = (
        "Hi there,\n\n"
        "Your 7-day Revenue Intelligence Pilot with THE13TH has been approved.\n\n"
        "To activate your pilot, please complete your setup using this secure link:\n"
        f"{checkout_url}\n\n"
        f"If you have any questions, you can reply to this email or reach us at "
        f"{context['support_email']}.\n\n"
        "– THE13TH Pilot Desk"
    )

    logger.info(
        "Sending pilot checkout email to %s for brokerage=%s",
        to_email,
        brokerage_name or "N/A",
    )

    email_client.send_html_email(
        to_email=to_email,
        subject=PILOT_CHECKOUT_SUBJECT,
        template_name=PILOT_CHECKOUT_TEMPLATE_NAME,
        context=context,
        plain_text_fallback=plain_text_fallback,
    )


# === 7-Day pilot summary + recommendation email (end of pilot) ===

PILOT_SUMMARY_TEMPLATE_NAME = "pilot_summary.html"
PILOT_SUMMARY_SUBJECT = "Your 7-Day Pilot Summary & Recommendation — THE13TH"


def build_pilot_summary_context(
    *,
    full_name: str,
    brokerage_name: str,
) -> Dict[str, Any]:
    """
    Minimal context for the 7-day summary email.

    Metrics can be added later (lead counts, response speed, etc.).
    """
    full_name_clean = (full_name or "").strip()
    first_name = full_name_clean.split(" ", 1)[0] if full_name_clean else "there"

    return {
        "full_name": full_name_clean or first_name,
        "first_name": first_name,
        "brokerage_name": brokerage_name or "your brokerage",
        "support_email": str(settings.email_from_address),
        # Extend later with real metrics:
        # "total_leads": metrics.total_leads,
        # "avg_response_minutes": metrics.avg_response_minutes,
        # etc.
    }


def send_pilot_summary_email(
    *,
    to_email: EmailStr,
    full_name: str,
    brokerage_name: str,
) -> None:
    """
    Send the 7-day pilot summary + recommendation email.

    Call this from a scheduled job that runs ~7 days after activation.
    """
    context = build_pilot_summary_context(
        full_name=full_name,
        brokerage_name=brokerage_name,
    )

    plain_text_fallback = (
        f"Hi {context['first_name']},\n\n"
        "Your 7-day Revenue Intelligence Pilot with THE13TH has now completed.\n\n"
        "Over the last week, THE13TH has been monitoring lead flow and follow-up patterns "
        "so you can see where revenue is being left on the table.\n\n"
        "Recommendation:\n"
        "Our strong recommendation is to keep THE13TH running beyond the pilot so that email "
        "intelligence and response discipline become a permanent part of how your brokerage operates.\n\n"
        "To move into a full subscription, simply reply to this email and we’ll convert your account "
        "to ongoing access.\n\n"
        "If you’d like to review the pilot together, reply and we’ll schedule a quick call.\n\n"
        "– THE13TH Pilot Desk"
    )

    logger.info(
        "Sending 7-day pilot summary email to %s for brokerage=%s",
        to_email,
        brokerage_name,
    )

    email_client.send_html_email(
        to_email=to_email,
        subject=PILOT_SUMMARY_SUBJECT,
        template_name=PILOT_SUMMARY_TEMPLATE_NAME,
        context=context,
        plain_text_fallback=plain_text_fallback,
    )
