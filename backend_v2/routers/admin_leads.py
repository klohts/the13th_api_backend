from __future__ import annotations

import logging
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend_v2.db import get_db
from backend_v2.models.lead import Lead

logger = logging.getLogger("the13th.backend_v2.routers.admin_leads")

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter(tags=["admin-leads"])


@router.get("/admin/leads/", response_class=HTMLResponse)
def admin_leads_board(
    request: Request,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """
    THE13TH Admin Leads Board.

    Shows:
    - Overall lead count
    - Breakdown by tenant_key and source
    - Latest leads table
    """

    leads: List[Lead] = (
        db.execute(select(Lead).order_by(Lead.created_at.desc()))
        .scalars()
        .all()
    )

    total_leads: int = len(leads)

    leads_by_tenant: Dict[str, int] = defaultdict(int)
    leads_by_source: Dict[str, int] = defaultdict(int)

    for lead in leads:
        tenant_label = lead.tenant_key or "Unassigned"
        leads_by_tenant[tenant_label] += 1
        leads_by_source[lead.source] += 1

    logger.info(
        "Rendering admin leads board with %s leads, %s tenants, %s sources",
        total_leads,
        len(leads_by_tenant),
        len(leads_by_source),
    )

    return templates.TemplateResponse(
        "admin_leads.html",
        {
            "request": request,
            "total_leads": total_leads,
            "leads_by_tenant": dict(leads_by_tenant),
            "leads_by_source": dict(leads_by_source),
            "leads": leads,
        },
    )
