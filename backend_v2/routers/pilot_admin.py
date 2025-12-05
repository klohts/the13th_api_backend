from __future__ import annotations

import logging
from typing import Any, Dict, List

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlmodel import Session, select
from pathlib import Path
from backend_v2.config import settings
from backend_v2.db import get_db
from backend_v2.email.service import send_pilot_checkout_email
from backend_v2.models.pilot import Pilot, PilotStatus, touch_pilot_for_update

logger = logging.getLogger("the13th.backend_v2.routers.pilot_admin")

# Configure Stripe once
stripe.api_key = settings.stripe_api_key

# Adjust this if your templates directory is different
BASE_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(BASE_TEMPLATE_DIR))

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

    Flow:
    - Find Pilot by id.
    - If not found → 404.
    - If already APPROVAL_SENT or ACTIVE → idempotent.
    - Else:
        - Create Stripe Checkout Session for the pilot setup fee.
        - Email the checkout URL to the pilot contact.
        - Mark status as APPROVAL_SENT.
    """
    pilot = db.get(Pilot, pilot_id)
    if pilot is None:
        logger.warning("Pilot with id=%s not found", pilot_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pilot not found",
        )

    # Idempotent: if already processed, just return
    if pilot.status in (PilotStatus.APPROVAL_SENT, PilotStatus.ACTIVE):
        logger.info(
            "Pilot id=%s already in status=%s; returning current state",
            pilot.id,
            pilot.status,
        )
        return ApprovePilotResponse(id=pilot.id, status=pilot.status)

    price_id = settings.stripe_pilot_price_id
    if not price_id:
        logger.error("stripe_pilot_price_id is not configured in settings")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stripe pilot price is not configured",
        )

    # Create Stripe Checkout Session
    try:
        logger.info(
            "Creating Stripe Checkout Session for pilot_id=%s, email=%s",
            pilot.id,
            pilot.contact_email,
        )
        session = stripe.checkout.Session.create(
            mode="payment",
            line_items=[
                {
                    "price": price_id,
                    "quantity": 1,
                }
            ],
            customer_email=pilot.contact_email,
            metadata={"pilot_id": str(pilot.id)},
            success_url="https://the13thhq.com/pilot/confirmed?session_id={CHECKOUT_SESSION_ID}",
            cancel_url="https://the13thhq.com/pilot",
        )
        checkout_url: str = session["url"]
        logger.info(
            "Stripe Checkout Session created for pilot_id=%s: %s",
            pilot.id,
            checkout_url,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "Failed to create Stripe Checkout Session for pilot_id=%s: %s",
            pilot.id,
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create Stripe checkout",
        ) from exc

    # Update pilot status → APPROVAL_SENT
    pilot.status = PilotStatus.APPROVAL_SENT
    touch_pilot_for_update(pilot)
    db.add(pilot)
    db.commit()
    db.refresh(pilot)

    # Fire-and-forget email (errors are logged but do not break the API)
    try:
        send_pilot_checkout_email(pilot, checkout_url)
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "Failed to send pilot checkout email for pilot_id=%s: %s",
            pilot.id,
            exc,
        )

    logger.info(
        "Pilot id=%s approval flow complete with status=%s",
        pilot.id,
        pilot.status,
    )
    return ApprovePilotResponse(id=pilot.id, status=pilot.status)
