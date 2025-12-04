from __future__ import annotations
import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend_v2.database import get_db
from backend_v2.services.intel_service import get_today_intel, get_live_feed

router = APIRouter(prefix="/public/ai-intel", tags=["Public Intelligence"])

@router.get("/today")
def today_intel(db: Session = Depends(get_db)):
    return get_today_intel(db)

@router.get("/feed")
def live_feed(db: Session = Depends(get_db)):
    return get_live_feed(db)
