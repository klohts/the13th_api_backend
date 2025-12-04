# backend_v2/routers/sim_lab.py

from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from backend_v2.database import get_db
from backend_v2.services.auth_service import authenticated_admin
from backend_v2.services.render import render_template
from backend_v2.services.sim_lab_service import (
    SIM_DEFAULT_COMPANIES,
    SIM_LEADS_PER_COMPANY,
    get_simulation_overview,
    reset_simulation_lab,
    run_multiple_bursts,
    seed_simulation_lab,
)

logger = logging.getLogger("the13th.sim_lab.router")

router = APIRouter(prefix="/admin/sim-lab", tags=["Simulation Lab"])


@router.post("/seed", response_class=JSONResponse)
def sim_lab_seed(
    request: Request,
    admin: Any = Depends(authenticated_admin),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """
    Seed the Simulation Lab with companies + leads.
    Idempotent: does nothing if already at target volume.
    """
    payload: Dict[str, Any] = seed_simulation_lab(
        db,
        company_count=SIM_DEFAULT_COMPANIES,
        leads_per_company=SIM_LEADS_PER_COMPANY,
    )
    return JSONResponse(content=payload)


@router.post("/burst", response_class=JSONResponse)
def sim_lab_burst(
    request: Request,
    admin: Any = Depends(authenticated_admin),
    db: Session = Depends(get_db),
    count: int = Query(1, ge=1, le=50, description="Number of bursts to run"),
) -> JSONResponse:
    """
    Run one or more bursts.

    - count = 1 → single burst (default)
    - count > 1 → multi-burst load driver (Step C)
    """
    if count == 1:
        payload = run_multiple_bursts(db, burst_count=1)
    else:
        payload = run_multiple_bursts(db, burst_count=count)

    return JSONResponse(content=payload)


@router.post("/reset", response_class=JSONResponse)
def sim_lab_reset(
    request: Request,
    admin: Any = Depends(authenticated_admin),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """
    Hard reset Simulation Lab to baseline.

    Deletes:
      - sim_leads
      - sim_bursts
      - sim_companies
    Does NOT touch production models.
    """
    payload: Dict[str, Any] = reset_simulation_lab(db)
    return JSONResponse(content=payload)


@router.get("/overview-data", response_class=JSONResponse)
def sim_lab_overview_data(
    request: Request,
    admin: Any = Depends(authenticated_admin),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """
    Returns JSON metrics for the Simulation Master Dashboard.
    """
    overview: Dict[str, Any] = get_simulation_overview(db)
    return JSONResponse(content=overview)


@router.get("/overview", response_class=HTMLResponse)
def sim_lab_overview_page(
    request: Request,
    admin: Any = Depends(authenticated_admin),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """
    HTML Simulation Lab dashboard page.
    """

    # Main simulation metrics
    overview: Dict[str, Any] = get_simulation_overview(db)

    # Email intel — safe delayed import
    try:
        from backend_v2.services.sim_email_service import get_email_overview
        email_stats = get_email_overview(db)
    except Exception:
        email_stats = {"status": "error"}

    # Pass overview AS ONE OBJECT (not flattened)
    context: Dict[str, Any] = {
        "request": request,
        "admin": admin,
        "active": "sim-lab",
        "overview": {**overview, "email": email_stats},
    }

    html = render_template("admin_sim_lab.html", context)
    return HTMLResponse(content=html)

