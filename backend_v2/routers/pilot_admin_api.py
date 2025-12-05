from __future__ import annotations

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend_v2.db import get_session
from backend_v2.models.pilot_model import Pilot

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Admin – Pilots"])


def _pilot_to_dict(pilot: Pilot) -> Dict[str, Any]:
    """Convert ORM object → JSON dict for Admin UI."""
    return {
        "id": pilot.id,
        "pilot_id": pilot.id,
        "email": pilot.email,
        "first_name": getattr(pilot, "first_name", None),
        "last_name": getattr(pilot, "last_name", None),
        "full_name": getattr(pilot, "full_name", None),
        "brokerage_name": pilot.brokerage_name,
        "role": pilot.role,
        "num_agents": pilot.num_agents,
        "notes": pilot.notes,
        "lead_volume": getattr(pilot, "lead_volume", None),
        "status": getattr(pilot, "status", None) or getattr(pilot, "pilot_status", None),
        "created_at": pilot.created_at,
        "source": pilot.source,
    }


@router.get("/admin/pilots/")
def list_pilots(db: Session = Depends(get_session)) -> List[Dict[str, Any]]:
    """Return all pilot requests for the Admin Dashboard."""
    pilots = db.query(Pilot).order_by(Pilot.created_at.desc()).all()
    return [_pilot_to_dict(p) for p in pilots]


@router.post("/admin/pilots/{pilot_id}/approve")
def approve_pilot(pilot_id: int, db: Session = Depends(get_session)) -> Dict[str, Any]:
    pilot = db.query(Pilot).filter(Pilot.id == pilot_id).first()
    if not pilot:
        raise HTTPException(status_code=404, detail="Pilot not found")

    # Normalize available status field
    if hasattr(pilot, "status"):
        pilot.status = "APPROVAL_SENT"
    elif hasattr(pilot, "pilot_status"):
        pilot.pilot_status = "APPROVAL_SENT"

    db.add(pilot)
    db.commit()
    db.refresh(pilot)

    return {"ok": True, "pilot_id": pilot_id, "status": "APPROVAL_SENT"}
