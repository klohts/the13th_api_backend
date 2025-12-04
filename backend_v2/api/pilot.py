# backend_v2/api/pilot.py
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from backend_v2.schemas.pilot import PilotRequest
from backend_v2.email.service import send_pilot_confirmation

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pilot", tags=["pilot"])


@router.post("/request", response_class=JSONResponse)
async def create_pilot_request(payload: PilotRequest) -> JSONResponse:
    """
    Receive 7-day pilot request from landing/pilot.html form
    and send confirmation email.
    """
    try:
        # TODO: persist payload to DB / leads table if desired.
        send_pilot_confirmation(payload)
    except Exception as exc:
        logger.exception("Failed to process pilot request: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to send confirmation email at this time.",
        ) from exc

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"ok": True, "message": "Pilot request received."},
    )
