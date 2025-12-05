from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from backend_v2.database import get_db
from backend_v2.services.auth_service import authenticated_admin
from backend_v2.services.sim_email_service import (
    auto_reply_to_threads,
    get_email_overview,
    simulate_inbound_emails,
)

logger = logging.getLogger("the13th.sim_email.router")

router = APIRouter(
    prefix="/admin/sim-lab/email",
    tags=["Simulation Lab Email"],
)


@router.post("/simulate-inbound", response_class=JSONResponse)
def simulate_inbound(
    request: Request,
    admin: Any = Depends(authenticated_admin),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """
    Generate simulated inbound emails for a random slice of leads.
    """
    payload: Dict[str, Any] = simulate_inbound_emails(db)
    return JSONResponse(content=payload)


@router.post("/auto-reply", response_class=JSONResponse)
def simulate_auto_reply(
    request: Request,
    admin: Any = Depends(authenticated_admin),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """
    Generate simulated outbound replies for open inbound threads.
    """
    payload: Dict[str, Any] = auto_reply_to_threads(db)
    return JSONResponse(content=payload)


@router.get("/overview-data", response_class=JSONResponse)
def email_overview(
    request: Request,
    admin: Any = Depends(authenticated_admin),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """
    Return email simulation metrics for dashboards.
    """
    payload: Dict[str, Any] = get_email_overview(db)
    return JSONResponse(content=payload)

@router.get("/email/test")
def test_email(db: Session = Depends(get_db)):
    from backend_v2.email.service import send_email

    send_email(
        to="rhettlohts@gmail.com",
        subject="THE13TH Email Test",
        html="<p>Your THE13TH email system is working successfully 🎉</p>"
    )

    return {"status": "ok"}
