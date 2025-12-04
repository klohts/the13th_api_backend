from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from backend_v2.database import get_db
from backend_v2.services.auth_service import authenticated_admin
from backend_v2.services.render import render_template
from backend_v2.services.sim_client_inspector_service import (
    fetch_companies_with_intel,
    fetch_global_overview,
    fetch_portfolio_intelligence,
)

logger = logging.getLogger("the13th.sim_client_inspector")

router = APIRouter(prefix="/admin/sim-client", tags=["Client Simulation Inspector"])


@router.get("/inspector", response_class=HTMLResponse)
def inspector_page(
    request: Request,
    admin: Any = Depends(authenticated_admin),
    db: Session = Depends(get_db)
):
    try:
        companies = fetch_companies_with_intel(db)
        overview = fetch_global_overview(db)
        portfolio = fetch_portfolio_intelligence(companies)

        context = {
            "companies": companies,
            "overview": overview,
            "portfolio": portfolio,
        }

        html = render_template("admin_sim_client_inspector.html", context)
        return HTMLResponse(content=html)

    except Exception as e:
        logger.error(f"Failed to load Client Simulation Inspector: {e}", exc_info=True)
        return HTMLResponse(
            content=f"<h1>Internal Server Error</h1><p>{e}</p>", status_code=500
        )


@router.post("/run-day")
def run_simulated_day(
    request: Request,
    admin: Any = Depends(authenticated_admin),
    db: Session = Depends(get_db),
):
    """
    Simulation Day Trigger (existing logic unchanged)
    """
    try:
        # your existing burst/sim-day logic
        db.execute("""
            UPDATE sim_client_leads
            SET score = MIN(100, score + (ABS(RANDOM()) % 4)),
                updated_at = CURRENT_TIMESTAMP
        """)
        db.commit()

        return HTMLResponse(
            "<script>location.href='/admin/sim-client/inspector'</script>"
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Simulation day failed: {e}", exc_info=True)
        return HTMLResponse(f"<h1>Error</h1><p>{e}</p>", status_code=500)
