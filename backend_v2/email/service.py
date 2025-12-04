# backend_v2/email/service.py
from __future__ import annotations

import logging
from typing import Any, Dict

from pydantic import EmailStr

from backend_v2.schemas.pilot import PilotRequest
from .client import email_client

logger = logging.getLogger(__name__)

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
