from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend_v2.db import get_db
from backend_v2.models.lead import Lead
from backend_v2.models.ingestion_event import IngestionEvent
from backend_v2.models.automation_event import AutomationEvent

logger = logging.getLogger("the13th.backend_v2.routers.admin_lead_detail")

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter(tags=["admin-leads"])


@dataclass
class JourneyEntry:
    created_at: object
    kind: str  # 'ingestion' | 'automation'
    channel: str
    status: str
    source: str
    message: str
    raw_payload: Optional[object]


@router.get("/admin/leads/{lead_id}", response_class=HTMLResponse)
def lead_detail(
    lead_id: int,
    request: Request,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Render the lead detail + unified journey timeline page."""
    lead: Optional[Lead] = db.get(Lead, lead_id)
    if lead is None:
        logger.warning("Lead not found for detail view: id=%s", lead_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found",
        )

    ingestion_stmt = (
        select(IngestionEvent)
        .where(IngestionEvent.lead_id == lead_id)
        .order_by(IngestionEvent.created_at.asc())
    )
    ingestion_events: List[IngestionEvent] = (
        db.execute(ingestion_stmt).scalars().all()
    )

    automation_stmt = (
        select(AutomationEvent)
        .where(AutomationEvent.lead_id == lead_id)
        .order_by(AutomationEvent.created_at.asc())
    )
    automation_events: List[AutomationEvent] = (
        db.execute(automation_stmt).scalars().all()
    )

    journey: List[JourneyEntry] = []

    for ev in ingestion_events:
        journey.append(
            JourneyEntry(
                created_at=ev.created_at,
                kind="ingestion",
                channel=getattr(ev, "channel", "webhook"),
                status=getattr(ev, "status", "success"),
                source=getattr(ev, "source", "") or "Ingestion",
                message=getattr(ev, "message", "") or "",
                raw_payload=getattr(ev, "raw_payload", None),
            )
        )

    for ev in automation_events:
        journey.append(
            JourneyEntry(
                created_at=ev.created_at,
                kind="automation",
                channel=ev.channel,
                status=ev.status,
                source=ev.event_type,
                message=ev.message,
                raw_payload=None,
            )
        )

    journey.sort(key=lambda e: e.created_at or 0)

    logger.info(
        "Rendering lead detail (id=%s, tenant=%s, ingestion_events=%s, automation_events=%s)",
        lead.id,
        getattr(lead, "tenant_key", None),
        len(ingestion_events),
        len(automation_events),
    )

    return templates.TemplateResponse(
        "admin_lead_detail.html",
        {
            "request": request,
            "lead": lead,
            "journey": journey,
        },
    )
