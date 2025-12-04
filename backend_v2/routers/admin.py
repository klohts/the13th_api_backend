from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse

from ..db import get_session
from ..services.leads import list_leads
from ..services.render import templates

logger = logging.getLogger("the13th.backend_v2.routers.admin")

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/leads", response_class=HTMLResponse)
def admin_leads_dashboard(
    request: Request,
    status: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    session=Depends(get_session),
) -> HTMLResponse:
    """Admin leads dashboard endpoint."""
    leads = list_leads(
        session,
        limit=limit,
        offset=0,
        status=status,
        search=search,
    )
    logger.info(
        "Rendering admin leads dashboard with %d leads (status=%s, search=%s)",
        len(leads),
        status,
        search,
    )
    context = {
        "request": request,
        "leads": leads,
        "status": status,
        "search": search,
        "limit": limit,
    }
    return templates.TemplateResponse("admin/leads_dashboard.html", context)
