from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlmodel import Session

from ..db import get_session
from ..services.leads import create_lead

logger = logging.getLogger("the13th.backend_v2.routers.api")

router = APIRouter(prefix="/api", tags=["api"])


class LeadIn(BaseModel):
    brokerage_name: str
    first_name: str
    last_name: str
    email: EmailStr
    phone: Optional[str] = None
    source: Optional[str] = None
    status: Optional[str] = "new"
    assigned_agent: Optional[str] = None
    price_range: Optional[str] = None
    notes: Optional[str] = None


@router.post(
    "/leads",
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a new lead into THE13TH.",
)
def ingest_lead(
    payload: LeadIn,
    session: Session = Depends(get_session),
) -> dict:
    """
    Ingest a new lead.

    This is what your demo funnel / web forms will call.
    """
    try:
        lead_data = payload.dict()
        if not lead_data.get("status"):
            lead_data["status"] = "new"

        lead = create_lead(session, lead_data)
        logger.info(
            "Ingested lead id=%s brokerage=%s email=%s",
            lead.id,
            lead.brokerage_name,
            lead.email,
        )
        return {
            "id": lead.id,
            "status": lead.status,
            "brokerage_name": lead.brokerage_name,
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to ingest lead: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to ingest lead.",
        ) from exc
