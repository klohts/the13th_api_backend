from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from sqlmodel import Session

from ..db import get_session
from ..services.leads import list_leads
from ..services.render import templates

logger = logging.getLogger("the13th.backend_v2.routers.tenant")

router = APIRouter(prefix="/tenant", tags=["tenant"])


@router.get("/leads", response_class=HTMLResponse)
def tenant_leads_dashboard(
    request: Request,
    brokerage_name: str = Query(..., min_length=1, description="Exact brokerage name"),
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    session: Session = Depends(get_session),
) -> HTMLResponse:
    """
    Tenant-facing leads dashboard.

    - Filters leads to a single brokerage_name (exact match, case-insensitive).
    - Optional status filter.
    - Intended to be embedded/linked from broker-facing UX.
    """
    all_leads = list_leads(
        session,
        limit=limit,
        offset=0,
        status=status,
        search=None,
    )

    brokerage_key = brokerage_name.lower().strip()
    leads = [
        lead
        for lead in all_leads
        if (lead.brokerage_name or "").lower().strip() == brokerage_key
    ]

    logger.info(
        "Rendering tenant leads dashboard for brokerage=%s (status=%s, count=%d)",
        brokerage_name,
        status,
        len(leads),
    )

    context = {
        "request": request,
        "brokerage_name": brokerage_name,
        "leads": leads,
        "status": status,
        "limit": limit,
    }
    return templates.TemplateResponse("tenant/leads_dashboard.html", context)
