from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlmodel import Session

from backend_v2.db import get_db
from backend_v2.models.pilot import Pilot, PilotStatus, touch_pilot_for_update
from backend_v2.schemas.pilot import PilotRequest
from backend_v2.email.service import send_pilot_confirmation

logger = logging.getLogger("backend_v2.api.pilot")

router = APIRouter(
    prefix="/pilot",
    tags=["pilot"],
)


def _build_problem_notes(payload: PilotRequest) -> str:
    """
    Condense marketing form fields into a single admin-facing notes string.
    """
    pieces: list[str] = []

    if payload.problem:
        pieces.append(f"Primary problem: {payload.problem}")

    if payload.lead_context:
        pieces.append(f"Lead context: {payload.lead_context}")

    if payload.team_size:
        pieces.append(f"Team size: {payload.team_size}")

    if payload.lead_volume:
        pieces.append(f"Lead volume: {payload.lead_volume}")

    if payload.notes:
        pieces.append(f"Notes: {payload.notes}")

    if payload.source:
        pieces.append(f"Source tag: {payload.source}")

    return " | ".join(pieces)


@router.post("/request", status_code=status.HTTP_201_CREATED)
def create_pilot_request(
    payload: PilotRequest,
    db: Session = Depends(get_db),
) -> JSONResponse:
    """
    Handle the public /pilot form submission.

    - Validates payload via PilotRequest
    - Creates a Pilot row (status=REQUESTED)
    - Attempts to send confirmation email (best-effort)
    - Returns 201 + JSON { ok, id, status } to the frontend
    """
    logger.info(
        "Received pilot request for brokerage=%s, contact=%s <%s>",
        payload.brokerage_name,
        payload.contact_name,
        payload.contact_email,
    )

    # 1) Persist to Pilot table
    try:
        problem_notes = _build_problem_notes(payload)

        pilot = Pilot(
            brokerage_name=payload.brokerage_name,
            contact_name=payload.contact_name,
            contact_email=payload.contact_email,
            role=payload.role,
            agents_count=payload.num_agents,
            problem_notes=problem_notes,
            status=PilotStatus.REQUESTED,
        )
        touch_pilot_for_update(pilot)

        db.add(pilot)
        db.commit()
        db.refresh(pilot)

        logger.info("Pilot row created with id=%s", pilot.id)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error while creating Pilot row: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create pilot request",
        ) from exc

    # 2) Best-effort confirmation email (do NOT break the API if it fails)
    try:
        send_pilot_confirmation(payload)
        logger.info("Pilot confirmation email sent for pilot_id=%s", pilot.id)
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "Non-fatal error while sending pilot confirmation email for pilot_id=%s: %s",
            pilot.id,
            exc,
        )

    # 3) Respond to frontend
    body: Dict[str, Any] = {
        "ok": True,
        "id": pilot.id,
        "status": pilot.status,
    }
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=body)
