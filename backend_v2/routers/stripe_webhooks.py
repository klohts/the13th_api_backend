from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlmodel import Session

from backend_v2.config import settings
from backend_v2.db import get_db
from backend_v2.models.pilot import Pilot, PilotStatus, touch_pilot_for_update

logger = logging.getLogger("the13th.backend_v2.routers.stripe_webhooks")

# Configure Stripe from env-backed settings
stripe.api_key = settings.stripe_api_key  # type: ignore[attr-defined]

router = APIRouter(
    prefix="/stripe",
    tags=["stripe"],
)


def _get_webhook_secret() -> str:
    try:
        secret = settings.stripe_webhook_secret  # type: ignore[attr-defined]
    except AttributeError as exc:  # settings missing field
        logger.error("Stripe webhook secret not configured on settings: %s", exc)
        raise RuntimeError("Stripe webhook secret not configured") from exc

    if not secret:
        logger.error("Stripe webhook secret is empty")
        raise RuntimeError("Stripe webhook secret is empty")
    return secret


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(..., alias="Stripe-Signature"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Stripe webhook endpoint.

    Expected flow:
    - Stripe sends events to /stripe/webhook
    - We verify signature using STRIPE_WEBHOOK_SECRET
    - On `checkout.session.completed` with a pilot_id in metadata:
        - Mark the corresponding Pilot as ACTIVE
        - Persist the change
        - (Optionally) trigger onboarding email

    Returns 200 on success so Stripe doesn't retry unnecessarily.
    """
    payload = await request.body()
    payload_str = payload.decode("utf-8")

    logger.info("Received Stripe webhook (len=%s)", len(payload_str))

    try:
        secret = _get_webhook_secret()
        event = stripe.Webhook.construct_event(
            payload=payload_str,
            sig_header=stripe_signature,
            secret=secret,
        )
    except stripe.error.SignatureVerificationError as exc:
        logger.warning("Stripe signature verification failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Stripe signature",
        ) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error while parsing Stripe webhook: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payload",
        ) from exc

    event_type: str = event.get("type", "")
    data_object: Dict[str, Any] = event.get("data", {}).get("object", {})  # type: ignore[assignment]

    logger.info("Processing Stripe event type=%s", event_type)

    if event_type == "checkout.session.completed":
        await _handle_checkout_session_completed(data_object, db)
    else:
        logger.debug("Unhandled Stripe event type=%s; ignoring", event_type)

    return {"received": True}


async def _handle_checkout_session_completed(
    session_obj: Dict[str, Any],
    db: Session,
) -> None:
    """
    Handle checkout.session.completed events.

    We expect the Checkout Session to carry a `pilot_id` in metadata so we can
    activate the correct Pilot after successful payment.
    """
    metadata: Dict[str, Any] = session_obj.get("metadata", {}) or {}
    pilot_id_raw: Optional[str] = metadata.get("pilot_id")

    logger.info(
        "checkout.session.completed metadata=%s, pilot_id=%s",
        json.dumps(metadata),
        pilot_id_raw,
    )

    if not pilot_id_raw:
        logger.warning("checkout.session.completed missing pilot_id metadata; skipping")
        return

    try:
        pilot_id = int(pilot_id_raw)
    except ValueError:
        logger.warning("Invalid pilot_id in metadata: %s", pilot_id_raw)
        return

    pilot = db.get(Pilot, pilot_id)
    if pilot is None:
        logger.warning("Pilot not found for id=%s from Stripe webhook", pilot_id)
        return

    if pilot.status == PilotStatus.ACTIVE:
        logger.info("Pilot id=%s already ACTIVE; no change", pilot.id)
        return

    logger.info("Marking pilot id=%s as ACTIVE from Stripe webhook", pilot.id)
    pilot.status = PilotStatus.ACTIVE
    touch_pilot_for_update(pilot)
    db.add(pilot)
    db.commit()
    db.refresh(pilot)

    # 🔔 Hook for onboarding email:
    # You can import your email service and trigger a "pilot activated" email here.
    # Example (pseudo, assuming you have such a service):
    #
    # from backend_v2.email.service import send_pilot_activated_email
    # send_pilot_activated_email(pilot)
    #
    logger.info("Pilot id=%s activated successfully via Stripe webhook", pilot.id)
