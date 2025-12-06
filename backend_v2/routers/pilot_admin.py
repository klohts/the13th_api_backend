from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, List, Optional

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


class ApprovePilotResponse(BaseModel):
    id: int
    status: str
    checkout_url: Optional[str] = None


@router.get("/admin/pilots/", response_class=HTMLResponse)
def list_pilots(
    request: Request,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """
    Render the admin pilot command center.
    """
    pilots: List[Pilot] = (
        db.execute(select(Pilot).order_by(Pilot.requested_at.desc()))
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


def _unwrap_secret(value: Any) -> Optional[str]:
    """Return plain string from SecretStr or similar, or None."""
    if value is None:
        return None
    if hasattr(value, "get_secret_value"):
        try:
            return value.get_secret_value()
        except Exception:
            return None
    return str(value)


def _determine_checkout_mode(price_id: str) -> str:
    """
    Inspect the Stripe Price to decide whether to use 'subscription' or 'payment'.

    - If price.recurring is present -> 'subscription'
    - Otherwise -> 'payment'
    """
    try:
        price_obj = stripe.Price.retrieve(price_id)
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "Failed to retrieve Stripe Price %s; defaulting to payment mode: %s",
            price_id,
            exc,
            exc_info=True,
        )
        return "payment"

    is_recurring = getattr(price_obj, "recurring", None) is not None
    mode = "subscription" if is_recurring else "payment"
    logger.info(
        "Determined checkout mode for price %s: %s (recurring=%s)",
        price_id,
        mode,
        is_recurring,
    )
    return mode


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

    api_key = _unwrap_secret(getattr(settings, "stripe_api_key", None))
    if not api_key:
        logger.error("STRIPE_API_KEY is not configured or invalid.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stripe API key is not configured",
        )

    # Derive customer email & brokerage name with fallbacks
    customer_email: Optional[str] = (
        getattr(pilot, "contact_email", None)
        or getattr(pilot, "email", None)
    )
    brokerage_name: str = (
        getattr(pilot, "brokerage_name", None)
        or getattr(pilot, "brokerage", None)
        or ""
    )

    if not customer_email:
        logger.error(
            "Pilot %s has no contact_email/email; cannot approve & send checkout",
            pilot.id,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pilot does not have a contact email configured.",
        )

    # Build success / cancel URLs from PUBLIC_BASE_URL (AnyHttpUrl -> str)
    public_base = str(settings.public_base_url).rstrip("/")
    success_url = f"{public_base}/thankyou?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{public_base}/pilot"

    stripe.api_key = api_key

    # Decide mode based on the price object itself
    checkout_mode = _determine_checkout_mode(price_id)

    try:
        logger.info(
            "Creating Stripe Checkout Session for pilot_id=%s email=%s price_id=%s mode=%s",
            pilot.id,
            customer_email,
            price_id,
            checkout_mode,
        )
        checkout_session = stripe.checkout.Session.create(
            mode=checkout_mode,
            line_items=[{"price": price_id, "quantity": 1}],
            customer_email=customer_email,
            metadata={
                "pilot_id": str(pilot.id),
                "brokerage_name": brokerage_name,
            },
            success_url=success_url,
            cancel_url=cancel_url,
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
            to_email=customer_email,
            checkout_url=checkout_url,
            brokerage_name=brokerage_name or None,
            full_name=getattr(pilot, "contact_name", None)
            or getattr(pilot, "full_name", None),
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

    status_value: Any = (
        pilot.status.value if hasattr(pilot.status, "value") else pilot.status
    )

    return ApprovePilotResponse(
        id=pilot.id,
        status=str(status_value),
        checkout_url=checkout_url,
    )
