from __future__ import annotations

import logging
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

logger = logging.getLogger("the13th.backend_v2.routers.admin_lead_detail")

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter(tags=["admin-leads"])


@router.get("/admin/leads/{lead_id}", response_class=HTMLResponse)
def lead_detail(
    lead_id: int,
    request: Request,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Render the lead detail + journey timeline page.

    This view is read-only and uses IngestionEvent as the first version
    of the journey timeline (ingestion + processing).
    """
    lead: Optional[Lead] = db.get(Lead, lead_id)
    if lead is None:
        logger.warning("Lead not found for detail view: id=%s", lead_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found",
        )

    events_stmt = (
        select(IngestionEvent)
        .where(IngestionEvent.lead_id == lead_id)
        .order_by(IngestionEvent.created_at.asc())
    )
    events: List[IngestionEvent] = (
        db.execute(events_stmt).scalars().all()
    )

    logger.info(
        "Rendering lead detail (id=%s, tenant=%s, events=%s)",
        lead.id,
        getattr(lead, "tenant_key", None),
        len(events),
    )

    return templates.TemplateResponse(
        "admin_lead_detail.html",
        {
            "request": request,
            "lead": lead,
            "events": events,
        },
    )
