from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from backend_v2.services.auth_service import authenticated_user
from backend_v2.services.render import render_template

router = APIRouter(prefix="/client", tags=["Client → Dashboard"])

@router.get("/dashboard", response_class=HTMLResponse)
def client_dashboard(
    request: Request,
    user = Depends(authenticated_user),
):
    # Try a likely template; if missing, fallback HTML
    try:
        context = {
            "request": request,
            "user": user,
            "active": "client-dashboard",
        }
        html = render_template("client_dashboard.html", context)
    except Exception:
        html = "<h1>Client Dashboard</h1><p>Template not found.</p>"
    return HTMLResponse(html)
