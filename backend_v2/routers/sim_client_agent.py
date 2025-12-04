from __future__ import annotations
import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from backend_v2.database import get_db
from backend_v2.services.auth_service import authenticated_admin
from backend_v2.services.render import render_template
from backend_v2.services.sim_client_inspector_service import fetch_agent_drilldown

logger = logging.getLogger("the13th.sim_client_agent.router")

router = APIRouter(prefix="/admin/sim-client/agent", tags=["Simulation Client – Agent"])


@router.get("/drilldown/{agent_id}", response_class=HTMLResponse)
def agent_drilldown_modal(
    request: Request,
    agent_id: int,
    admin: Any = Depends(authenticated_admin),
    db: Session = Depends(get_db),
):
    """
    Returns the drilldown modal for a single agent.
    Includes:
      - agent profile
      - performance metrics
      - assigned leads (segmented)
      - recent activity
    """

    payload = fetch_agent_drilldown(db, agent_id)
    html = render_template("partials/agent_drilldown_modal.html", payload)
    return HTMLResponse(content=html)
