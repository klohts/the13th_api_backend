from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend_v2.db import get_db
from backend_v2.models.pilot_model import Pilot
from backend_v2.schemas.pilot import PilotResponse

router = APIRouter(prefix="/admin/pilots", tags=["Admin - Pilots"])


@router.get("/", response_model=list[PilotResponse])
def list_pilots(db: Session = Depends(get_db)):
    pilots = db.query(Pilot).order_by(Pilot.created_at.desc()).all()
    return pilots


@router.post("/{pilot_id}/approve")
def approve_pilot(pilot_id: int, db: Session = Depends(get_db)):
    pilot = db.query(Pilot).filter(Pilot.id == pilot_id).first()
    if not pilot:
        raise HTTPException(status_code=404, detail="Pilot not found")

    # Placeholder business logic
    pilot.status = "approved"
    db.commit()

    return {"status": "approved", "pilot_id": pilot_id}
