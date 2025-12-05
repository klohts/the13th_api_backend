from __future__ import annotations

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlmodel import Session, select

from backend_v2.db import get_db
from backend_v2.models.pilot import Pilot, PilotStatus, touch_pilot_for_update

logger = logging.getLogger("the13th.backend_v2.routers.pilot_admin")

# Adjust this if your templates directory is different
templates = Jinja2Templates(directory="backend_v2/templates")

router = APIRouter(
    prefix="/admin/pilots",
    tags=["admin-pilots"],
)


class ApprovePilotResponse(BaseModel):
    id: int
    status: PilotStatus


@router.get("/", response_class=HTMLResponse)
def list_pilots(
    request: Request,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """
    Admin Pilot Command Center.

    Renders the cinematic pilot review dashboard with all pilot requests.
    """
    logger.info("Loading admin pilot dashboard")
    statement = select(Pilot).order_by(Pilot.requested_at.desc())
    pilots: List[Pilot] = list(db.exec(statement).all())

    context: Dict[str, Any] = {
        "request": request,
        "pilots": pilots,
    }
    return templates.TemplateResponse("admin_pilots.html", context)


@router.post(
    "/{pilot_id}/approve",
    response_model=ApprovePilotResponse,
)
def approve_pilot(
    pilot_id: int,
    db: Session = Depends(get_db),
) -> ApprovePilotResponse:
    """
    One-click pilot approval.

    - Finds the pilot by id.
    - If not found → 404.
    - If already APPROVAL_SENT or ACTIVE → idempotent, returns current status.
    - If REQUESTED → marks as APPROVAL_SENT and persists.

    NOTE:
    Stripe checkout + outbound email can be layered on top of this by
    extending this function or delegating into a service, without changing
    the response contract used by the frontend.
    """
    logger.info("Approve request for pilot_id=%s", pilot_id)

    pilot = db.get(Pilot, pilot_id)
    if pilot is None:
        logger.warning("Pilot with id=%s not found", pilot_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pilot not found",
        )

    # Idempotent behaviour for already-processed pilots
    if pilot.status in (PilotStatus.APPROVAL_SENT, PilotStatus.ACTIVE):
        logger.info(
            "Pilot id=%s already in status=%s, returning current state",
            pilot.id,
            pilot.status,
        )
        return ApprovePilotResponse(id=pilot.id, status=pilot.status)

    # Transition REQUESTED -> APPROVAL_SENT
    if pilot.status == PilotStatus.REQUESTED:
        logger.info("Marking pilot id=%s as APPROVAL_SENT", pilot.id)
        pilot.status = PilotStatus.APPROVAL_SENT
        touch_pilot_for_update(pilot)
        db.add(pilot)
        # db.commit() is handled once by get_db, but an explicit commit
        # here is safe if you prefer immediate persistence semantics.
        db.commit()
        db.refresh(pilot)

    logger.info(
        "Pilot id=%s approval flow complete with status=%s",
        pilot.id,
        pilot.status,
    )
    return ApprovePilotResponse(id=pilot.id, status=pilot.status)
