from __future__ import annotations

import logging
from typing import Any, Dict

from pydantic import EmailStr

from backend_v2.schemas.pilot import PilotRequest
from backend_v2.models.pilot import Pilot
from .client import email_client

logger = logging.getLogger(__name__)

PILOT_TEMPLATE_NAME = "pilot_confirmation.html"
PILOT_SUBJECT = "Your 7-Day Revenue Intelligence Pilot with THE13TH"

CHECKOUT_TEMPLATE_NAME = "pilot_checkout.html"
CHECKOUT_SUBJECT = "Confirm your THE13TH Revenue Intelligence Pilot"


def build_pilot_context(pilot: PilotRequest) -> Dict[str, Any]:
    """Map PilotRequest into template context."""
    full_name = getattr(pilot, "full_name", "").strip() or ""
    first_name = getattr(pilot, "first_name", "") or full_name.split(" ")[0] if full_name else ""
    last_name = getattr(pilot, "last_name", "") or " ".join(full_name.split(" ")[1:]) if full_name else ""

    return {
        "full_name": full_name,
        "first_name": first_name,
        "last_name": last_name,
        "brokerage_name": pilot.brokerage_name,
        "website": getattr(pilot, "website", "") or "",
        "agents_on_team": getattr(pilot, "agents_on_team", None) or "Not specified",
        "monthly_online_leads": getattr(pilot, "monthly_online_leads", None) or "Not specified",
        "primary_focus": getattr(pilot, "primary_focus", None) or "Not specified",
        "main_problem": getattr(pilot, "main_problem", None) or "",
        "anything_special": getattr(pilot, "anything_special", None) or "",
    }


def send_pilot_confirmation(pilot: PilotRequest) -> None:
    """
    Send confirmation email to the broker after they submit a pilot request.

    Raises exceptions on failure; caller should handle/log as appropriate.
    """
    to_email: EmailStr = pilot.work_email
    context = build_pilot_context(pilot)

    plain_text_fallback = (
        f"Hi {context['first_name'] or 'there'},\n\n"
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


# ---------- NEW: Stripe checkout email ----------


def build_pilot_checkout_context(pilot: Pilot, checkout_url: str) -> Dict[str, Any]:
    """Template context for the Stripe checkout email."""
    full_name = pilot.contact_name or ""
    return {
        "full_name": full_name,
        "brokerage_name": pilot.brokerage_name,
        "checkout_url": checkout_url,
    }


def send_pilot_checkout_email(pilot: Pilot, checkout_url: str) -> None:
    """
    Email the Stripe checkout link for the pilot setup fee.

    This is triggered from the Admin → Approve & Send Checkout flow.
    """
    to_email: EmailStr = pilot.contact_email  # type: ignore[assignment]
    context = build_pilot_checkout_context(pilot, checkout_url)

    plain_text_fallback = (
        f"Hi {context['full_name'] or 'there'},\n\n"
        "Here is your secure checkout link to start your 7-day Revenue Intelligence Pilot "
        "with THE13TH:\n\n"
        f"{checkout_url}\n\n"
        "If you weren’t expecting this email, you can safely ignore it.\n\n"
        "– THE13TH Pilot Desk"
    )

    logger.info(
        "Sending pilot checkout email to %s for pilot_id=%s",
        to_email,
        getattr(pilot, "id", None),
    )

    email_client.send_html_email(
        to_email=to_email,
        subject=CHECKOUT_SUBJECT,
        template_name=CHECKOUT_TEMPLATE_NAME,
        context=context,
        plain_text_fallback=plain_text_fallback,
    )
