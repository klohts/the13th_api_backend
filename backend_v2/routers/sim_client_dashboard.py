from __future__ import annotations

import logging
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from backend_v2.database import get_db
from backend_v2.services.auth_service import authenticated_admin
from backend_v2.services.render import render_template
from backend_v2.client_sim_all_in_one import (
    get_client_sim_overview,
    simulate_client_day,
)

logger = logging.getLogger("the13th.sim_client.dashboard")

router = APIRouter(prefix="/admin/sim-client", tags=["Client Simulation UI"])


@router.get("/dashboard", response_class=HTMLResponse)
def sim_client_dashboard_page(
    request: Request,
    admin=Depends(authenticated_admin),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    snapshot = get_client_sim_overview(db)

    context = {
        "active": "sim-client",
        "snapshot": snapshot,
    }

    html = render_template("admin_sim_client.html", context)
    return HTMLResponse(html)


@router.post("/run-day", response_class=HTMLResponse)
def sim_client_run_day(
    request: Request,
    admin=Depends(authenticated_admin),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    result = simulate_client_day(db)
    snapshot = get_client_sim_overview(db)

    context = {
        "active": "sim-client",
        "snapshot": snapshot,
        "result": result,
    }

    html = render_template("admin_sim_client_partial.html", context)
    return HTMLResponse(html)
