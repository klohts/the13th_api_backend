"""
Router for Admin Pilot Dashboard UI.

Provides an HTML dashboard at:
  GET /admin/pilots/ui

The template's JS calls JSON endpoints:
  GET  /admin/pilots/
  POST /admin/pilots/{pilot_id}/approve
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

logger = logging.getLogger(__name__)

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@router.get("/admin/pilots/ui", response_class=HTMLResponse)
async def admin_pilot_dashboard(request: Request) -> HTMLResponse:
    """
    Render the Full Admin Pilot Dashboard UI.

    The template's JS is responsible for calling the JSON APIs:
      - GET /admin/pilots/
      - POST /admin/pilots/{pilot_id}/approvecle
    """
    logger.info("Rendering Admin Pilot Dashboard UI")
    return templates.TemplateResponse("admin_pilots.html", {"request": request})
