from __future__ import annotations

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend_v2.db import get_db
from backend_v2.models.pilot_model import Pilot

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Admin – Pilots"])


def _pilot_to_dict(pilot: Pilot) -> Dict[str, Any]:
    """Convert a Pilot ORM object into a JSON-serializable dict."""

    # Try to reconstruct a full name
    full_name = getattr(pilot, "full_name", None)
    if not full_name:
        first = getattr(pilot, "first_name", "") or ""
        last = getattr(pilot, "last_name", "") or ""
        full_name = f"{first} {last}".strip() or None

    # Status may be stored as status or pilot_status enum/string
    status = getattr(pilot, "status", None) or getattr(pilot, "pilot_status", None)

    return {
        "id": getattr(pilot, "id", None),
        "pilot_id": getattr(pilot, "id", None),
        "email": getattr(pilot, "email", None),
        "first_name": getattr(pilot, "first_name", None),
        "last_name": getattr(pilot, "last_name", None),
        "full_name": full_name,
        "brokerage_name": getattr(pilot, "brokerage_name", None),
        "role": getattr(pilot, "role", None),
        "num_agents": getattr(pilot, "num_agents", None),
        "notes": getattr(pilot, "notes", None),
        "lead_volume": getattr(pilot, "lead_volume", None),
        "status": status,
        "created_at": getattr(pilot, "created_at", None),
        "source": getattr(pilot, "source", None),
    }


@router.get("/admin/pilots/")
def list_pilots(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """
    Return all pilot requests for the Admin UI.

    The Admin Pilot Dashboard calls this endpoint to populate the table.
    """
    logger.info("Admin listing pilots")
    pilots = db.query(Pilot).order_by(Pilot.created_at.desc()).all()
    return [_pilot_to_dict(p) for p in pilots]


@router.post("/admin/pilots/{pilot_id}/approve")
def approve_pilot(pilot_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Approve a pilot and mark it as pending checkout / active.

    The Admin Pilot Dashboard 'Approve & Send Checkout' button calls this.
    Later we can extend this to:
      - create Stripe Checkout session
      - send email to broker
    """
    pilot = db.query(Pilot).filter(Pilot.id == pilot_id).first()
    if not pilot:
        raise HTTPException(status_code=404, detail="Pilot not found")

    # Decide which field to use for status
    if hasattr(pilot, "status"):
        setattr(pilot, "status", "APPROVAL_SENT")
    elif hasattr(pilot, "pilot_status"):
        setattr(pilot, "pilot_status", "APPROVAL_SENT")

    db.add(pilot)
    db.commit()
    db.refresh(pilot)

    logger.info("Approved pilot id=%s", pilot_id)

    return {
        "ok": True,
        "pilot_id": pilot_id,
        "status": "APPROVAL_SENT",
    }
