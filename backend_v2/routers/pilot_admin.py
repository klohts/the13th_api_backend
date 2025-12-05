# backend_v2/routers/pilot_admin.py
import logging
from typing import Any, Dict, List

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Request,
)
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from backend_v2.auth import authenticated_admin
from backend_v2.db import get_db
from backend_v2.models.pilot import Pilot, PilotStatus
from backend_v2.services.pilot_approval import (
    PilotApprovalError,
    approve_pilot_and_create_checkout,
)
from backend_v2.email.pilot_notifications import schedule_pilot_approval_email

logger = logging.getLogger(__name__)

router = APIRouter(tags=["admin-pilots"])

templates = Jinja2Templates(directory="the13th/templates")


@router.get("/admin/pilots/ui", response_class=HTMLResponse)
def admin_pilots_ui(
    request: Request,
    db: Session = Depends(get_db),
    admin: Any = Depends(authenticated_admin),
) -> HTMLResponse:
    """
    Admin · Pilot Command Center UI.
    Shows all pilot requests and their statuses.
    """
    pilots: List[Pilot] = (
        db.query(Pilot)
        .order_by(getattr(Pilot, "requested_at", Pilot.id).desc())
        .all()
    )

    context: Dict[str, Any] = {
        "request": request,
        "admin": admin,
        "pilots": pilots,
    }
    return templates.TemplateResponse("admin_pilots.html", context)


@router.post("/admin/pilots/{pilot_id}/approve")
def approve_pilot(
    pilot_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    admin: Any = Depends(authenticated_admin),
) -> JSONResponse:
    """
    One-click Approve & Send Checkout.
    - Creates Stripe Checkout Session
    - Moves pilot to APPROVAL_SENT
    - Schedules email with checkout link
    """
    try:
        pilot, checkout_url = approve_pilot_and_create_checkout(db=db, pilot_id=pilot_id)
    except PilotApprovalError as exc:
        logger.warning("Pilot approval failed for id=%s: %s", pilot_id, exc)
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Unexpected error approving pilot %s", pilot_id)
        raise HTTPException(status_code=500, detail="Unable to approve pilot.")

    schedule_pilot_approval_email(background_tasks, pilot, checkout_url)

    payload = {
        "ok": True,
        "pilot_id": pilot.id,
        "status": pilot.status.name
        if hasattr(pilot.status, "name")
        else str(pilot.status),
        "checkout_url": checkout_url,
    }

    return JSONResponse(payload)
