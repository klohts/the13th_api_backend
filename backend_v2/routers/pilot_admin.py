from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend_v2.config import settings
from backend_v2.db import get_db
from backend_v2.models.pilot import Pilot, PilotStatus, touch_pilot_for_update
from backend_v2.email.service import send_pilot_checkout_email

logger = logging.getLogger("the13th.backend_v2.routers.pilot_admin")

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter(tags=["admin-pilots"])


class ApprovePilotRequest(BaseModel):
    """
    Request model kept for future extensibility.
    Currently the pilot_id comes from the URL path.
    """

    pilot_id: int


class ApprovePilotResponse(BaseModel):
    id: int
    status: str
    checkout_url: Optional[str] = None


@router.get("/admin/pilots/", response_class=HTMLResponse)
def list_pilots(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    """
    Render the admin pilot command center.

    The template is responsible for computing / displaying the KPI tiles;
    we just pass the ordered list of pilots.
    """
    pilots: List[Pilot] = (
        db.execute(
            select(Pilot).order_by(Pilot.requested_at.desc())
        )
        .scalars()
        .all()
    )

    return templates.TemplateResponse(
        "admin_pilots.html",
        {
            "request": request,
            "pilots": pilots,
        },
    )


@router.post("/admin/pilots/{pilot_id}/approve", response_model=ApprovePilotResponse)
def approve_pilot(
    pilot_id: int,
    db: Session = Depends(get_db),
) -> ApprovePilotResponse:
    """
    Approve a pilot and send the Stripe checkout link.

    Steps:
    1. Validate pilot exists and is in an approvable state.
    2. Create a Stripe Checkout Session using the configured pilot price.
    3. Update pilot status to APPROVAL_SENT.
    4. Fire-and-forget the checkout email (log failures, but don't block).
    """
    logger.info("Admin attempting to approve pilot_id=%s", pilot_id)

    pilot: Optional[Pilot] = db.get(Pilot, pilot_id)
    if pilot is None:
        logger.warning("Pilot not found for approval: id=%s", pilot_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pilot not found",
        )

    if pilot.status not in {PilotStatus.REQUESTED, PilotStatus.APPROVAL_SENT}:
        logger.warning(
            "Pilot in invalid status for approval: id=%s status=%s",
            pilot.id,
            pilot.status,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pilot is not in a state that can be approved",
        )

    price_id = settings.stripe_pilot_price_id
    if not price_id:
        logger.error("STRIPE_PILOT_PRICE_ID is not configured.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stripe pilot price is not configured",
        )

    if not settings.stripe_api_key:
        logger.error("STRIPE_API_KEY is not configured.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stripe API key is not configured",
        )

    stripe.api_key = settings.stripe_api_key

    try:
        logger.info(
            "Creating Stripe Checkout Session for pilot_id=%s email=%s",
            pilot.id,
            getattr(pilot, "contact_email", None),
        )
        checkout_session = stripe.checkout.Session.create(
            mode="payment",
            line_items=[{"price": price_id, "quantity": 1}],
            customer_email=getattr(pilot, "contact_email", None),
            metadata={
                "pilot_id": str(pilot.id),
                "brokerage_name": getattr(pilot, "brokerage_name", ""),
            },
            success_url=settings.stripe_success_url,
            cancel_url=settings.stripe_cancel_url,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "Unable to create Stripe checkout for pilot_id=%s: %s",
            pilot.id,
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create Stripe checkout",
        ) from exc

    checkout_url: str = checkout_session["url"]

    # Update pilot status and timestamps
    pilot.status = PilotStatus.APPROVAL_SENT
    touch_pilot_for_update(pilot)
    db.add(pilot)
    db.commit()
    db.refresh(pilot)

    # Fire-and-forget email – failure is logged but does not block approval
    try:
        send_pilot_checkout_email(
            to_email=getattr(pilot, "contact_email", None),
            checkout_url=checkout_url,
            brokerage_name=getattr(pilot, "brokerage_name", None),
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "Pilot approved but failed to send checkout email for pilot_id=%s: %s",
            pilot.id,
            exc,
        )

    logger.info(
        "Pilot approval completed: id=%s status=%s",
        pilot.id,
        pilot.status,
    )

    return ApprovePilotResponse(
        id=pilot.id,
        status=str(
            pilot.status.value if hasattr(pilot.status, "value") else pilot.status
        ),
        checkout_url=checkout_url,
    )
