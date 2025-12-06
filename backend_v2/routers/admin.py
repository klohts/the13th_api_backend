from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse

from ..db import get_session
from ..services.leads import list_leads
from ..services.render import templates

logger = logging.getLogger("the13th.backend_v2.routers.admin")

router = APIRouter(prefix="/admin", tags=["admin"])


def build_admin_context(
    *,
    request: Request,
    active_nav: str,
    sidebar_counts: Optional[Dict[str, int]] = None,
    current_tenant: Optional[Any] = None,
    current_user_email: Optional[str] = None,
    **extra: Any,
) -> Dict[str, Any]:
    """
    Base context builder for all admin pages.

    Ensures admin_base.html always gets the keys it expects.
    """
    base: Dict[str, Any] = {
        "request": request,
        "active_nav": active_nav,
        "sidebar_counts": sidebar_counts or {},
        "current_tenant": current_tenant,
        "current_user_email": current_user_email or "admin@the13thhq.com",
    }
    base.update(extra)
    return base


@router.get("/", response_class=HTMLResponse)
def admin_overview(
    request: Request,
    session=Depends(get_session),
) -> HTMLResponse:
    """
    Admin command-center / overview page.
    """
    try:
        recent_leads = list_leads(
            session,
            limit=5,
            offset=0,
            status=None,
            search=None,
        )
    except Exception:
        logger.exception("Failed to load recent leads for admin overview")
        recent_leads = []

    metrics: Dict[str, Any] = {
        "new_leads_24h": len(recent_leads),
        "new_leads_delta": 0,
        "sla_minutes": 5,
        "sla_coverage": 0,
        "sla_delta": 0,
        "active_pilots": 0,
        "pilots_expiring_7d": 0,
        "mrr": 0,
        "mrr_delta": 0,
    }

    issues: list[Dict[str, Any]] = []
    activity: list[Dict[str, Any]] = []
    tenants: list[Dict[str, Any]] = []

    sidebar_counts = {
        "leads": len(recent_leads),
        "pilots": 0,
    }

    context = build_admin_context(
        request=request,
        active_nav="overview",
        sidebar_counts=sidebar_counts,
        metrics=metrics,
        issues=issues,
        activity=activity,
        tenants=tenants,
    )

    logger.info(
        "Rendering admin overview (recent_leads=%d)",
        len(recent_leads),
    )

    return templates.TemplateResponse("admin_overview.html", context)


@router.get("/leads", response_class=HTMLResponse)
def admin_leads_dashboard(
    request: Request,
    status: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    session=Depends(get_session),
) -> HTMLResponse:
    """
    Admin leads dashboard endpoint rendered inside THE13TH admin shell.
    """
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

    sidebar_counts = {
        "leads": len(leads),
        "pilots": 0,
    }

    context = build_admin_context(
        request=request,
        active_nav="leads",
        sidebar_counts=sidebar_counts,
        status=status,
        search=search,
        limit=limit,
        leads=leads,
    )

    return templates.TemplateResponse("admin/leads_dashboard.html", context)
