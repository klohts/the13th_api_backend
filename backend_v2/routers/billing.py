# backend_v2/routers/billing.py

from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from backend_v2.services.render import render_template
from backend_v2.services.billing_service import get_billing_metrics_safe
from backend_v2.services.auth_service import authenticated_admin
from backend_v2.database import get_db

logger = logging.getLogger("the13th.admin.billing.router")

router = APIRouter(prefix="/admin", tags=["Admin Billing"])


@router.get("/billing", response_class=HTMLResponse)
def admin_billing_page(
    request: Request,
    admin: Any = Depends(authenticated_admin),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """
    Billing page (SAFE MODE)
    Always returns stable metrics with no database queries.
    """

    metrics: Dict[str, Any] = get_billing_metrics_safe(db)

    context: Dict[str, Any] = {
        "request": request,
        "admin": admin,
        "active": "billing",

        # Ensures template banners render safely
        "stripe_enabled": False,
        "demo_mode": True,

        # Safe-mode billing metrics
        **metrics,
    }

    html = render_template("admin_billing.html", context)
    return HTMLResponse(content=html)
