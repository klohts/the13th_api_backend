from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from backend_v2.database import get_db
from backend_v2.services.email_automation_service import EmailAutomationService
from backend_v2.services.render import render_template

logger = logging.getLogger("the13th.sim_email_router")

router = APIRouter(
    prefix="/admin/sim-email",
    tags=["Simulation Email"],
)


@router.get("/feed", response_class=HTMLResponse)
def email_feed_panel(
    request: Request,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Render the email bubble stream for the current simulation context.

    For now we aggregate the most recent events across the demo lead(s).
    Later we can filter by specific simulation or lead id.
    """
    # === AUTO-REFRESH GUARD: block HTMX polling / unintended refresh ===
    hx_req = request.headers.get("HX-Request")
    hx_trigger = request.headers.get("HX-Trigger")
    hx_trigger_name = request.headers.get("HX-Trigger-Name")

    # Block if this is ANY HTMX-driven refresh attempt
    if hx_req == "true" and (hx_trigger or hx_trigger_name):
        return Response(status_code=204)
    # ================================================================

    service = EmailAutomationService(db)
    emails = service.list_recent(limit=40)
    if not emails:
        service.seed_demo_thread()
        emails = service.list_recent(limit=40)

    context: Dict[str, Any] = {
        "request": request,
        "emails": emails,
    }
    return render_template("components/email_feed_bubbles.html", context)
