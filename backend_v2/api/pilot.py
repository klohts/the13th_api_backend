# backend_v2/api/pilot.py

from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from backend_v2.db import get_db
from backend_v2.models.pilot import Pilot, PilotStatus
from backend_v2.schemas.pilot import PilotRequest
from backend_v2.email.service import send_pilot_confirmation

logger = logging.getLogger("the13th.backend_v2.api.pilot")

router = APIRouter(prefix="/pilot", tags=["pilot"])


def _safe_get(obj: Any, name: str, default: str = "") -> str:
    """Safely pull a string-ish attribute off a Pydantic model."""
    try:
        value = getattr(obj, name, default)
    except Exception:
        return default
    if value is None:
        return default
    return str(value).strip()


def _build_problem_notes(payload: PilotRequest) -> str:
    """
    Build the human-readable 'problem / notes' string that shows up
    on the admin dashboard. This mirrors the format already visible:

    "Primary problem: ... | Team size: ... | Lead volume: ...
     | Notes: Problem to surface: ... | Source tag: ..."
    """
    parts = []

    primary_problem = _safe_get(payload, "primary_problem") or _safe_get(
        payload, "problem"
    )
    if primary_problem:
        parts.append(f"Primary problem: {primary_problem}")

    team_size = _safe_get(payload, "team_size") or _safe_get(payload, "agents_on_team")
    if team_size:
        parts.append(f"Team size: {team_size}")

    lead_volume = _safe_get(payload, "lead_volume") or _safe_get(
        payload, "monthly_online_leads"
    )
    if lead_volume:
        parts.append(f"Lead volume: {lead_volume}")

    notes = (
        _safe_get(payload, "problem_to_surface")
        or _safe_get(payload, "notes")
        or _safe_get(payload, "lead_context")
        or _safe_get(payload, "special_lead_sources")
    )
    if notes:
        parts.append(f"Notes: Problem to surface: {notes}")

    source_tag = _safe_get(payload, "source")
    if source_tag:
        parts.append(f"Source tag: {source_tag}")

    return " | ".join(parts)


def _build_pilot_model(payload: PilotRequest) -> Dict[str, Any]:
    """
    Map the incoming PilotRequest (Pydantic) object into fields
    for the Pilot ORM model. We keep this mapping defensive so
    small schema changes don't break the API.
    """
    contact_name = (
        _safe_get(payload, "contact_name")
        or _safe_get(payload, "full_name")
        or "Unknown"
    )

    contact_email = (
        _safe_get(payload, "contact_email")
        or _safe_get(payload, "work_email")
        or _safe_get(payload, "email")
    )

    if not contact_email:
        # We treat missing email as a hard error – broker must have a contact email.
        raise ValueError("Contact email is required for pilot requests.")

    brokerage_name = _safe_get(payload, "brokerage_name") or "Unknown brokerage"
    role = _safe_get(payload, "role") or "Owner / Broker-in-Charge"

    # Try multiple possible integer-ish fields for agents/team size.
    agents_raw = (
        _safe_get(payload, "agents_count")
        or _safe_get(payload, "num_agents")
        or _safe_get(payload, "agents_on_team")
        or _safe_get(payload, "team_size_numeric")
    )

    try:
        agents_count = int(agents_raw) if agents_raw else 0
    except ValueError:
        agents_count = 0

    problem_notes = _build_problem_notes(payload)

    return {
        "brokerage_name": brokerage_name,
        "contact_name": contact_name,
        "contact_email": contact_email,
        "role": role,
        "agents_count": agents_count,
        "problem_notes": problem_notes,
        "status": PilotStatus.REQUESTED,
    }


@router.post(
    "/request",
    status_code=status.HTTP_201_CREATED,
    summary="Create a Revenue Intelligence Pilot request",
)
async def create_pilot_request(
    payload: PilotRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Public endpoint hit by the marketing-site /pilot form.

    Responsibilities:
    - Validate and persist the pilot request to the database.
    - Fire the pilot confirmation email to the brokerage owner.
    - Never leak internal errors to the browser (returns generic 500 on failure).
    """
    try:
        # Ensure payload is fully validated (in case this is called internally).
        payload = PilotRequest.model_validate(payload)
    except ValidationError as exc:
        logger.warning(
            "Validation error on pilot request from %s: %s",
            request.client.host if request.client else "unknown",
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.errors(),
        ) from exc

    logger.info(
        "Received pilot request from '%s' (%s) for brokerage '%s' [source=%s]",
        _safe_get(payload, "contact_name") or _safe_get(payload, "full_name"),
        _safe_get(payload, "contact_email")
        or _safe_get(payload, "work_email")
        or _safe_get(payload, "email"),
        _safe_get(payload, "brokerage_name"),
        _safe_get(payload, "source"),
    )

    # 1) Persist to database
    try:
        pilot_kwargs = _build_pilot_model(payload)
        pilot = Pilot(**pilot_kwargs)
        db.add(pilot)
        db.commit()
        db.refresh(pilot)
        logger.info("Stored pilot request with id=%s", pilot.id)
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        logger.exception("Failed to persist pilot request: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to submit pilot request at this time.",
        ) from exc

    # 2) Fire confirmation email (non-fatal if this fails)
    try:
        send_pilot_confirmation(payload)
        logger.info("Pilot confirmation email queued for pilot_id=%s", pilot.id)
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "Pilot request stored but failed to send confirmation email "
            "for pilot_id=%s: %s",
            pilot.id,
            exc,
        )

    return {
        "id": pilot.id,
        "status": pilot.status.value if hasattr(pilot.status, "value") else pilot.status,
        "message": "Pilot request received. We'll review and confirm availability.",
    }


__all__ = ["router"]
