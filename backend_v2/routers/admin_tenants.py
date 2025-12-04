from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from backend_v2.database import get_db
from backend_v2.services.auth_service import authenticated_admin
from backend_v2.services.tenants_service import fetch_all_tenants
from backend_v2.services.render import render_template

router = APIRouter(prefix="/admin", tags=["Admin → Tenants"])

@router.get("/tenants", response_class=HTMLResponse)
def admin_tenants_page(
    request: Request,
    db: Session = Depends(get_db),
    admin = Depends(authenticated_admin),
):
    tenants = fetch_all_tenants(db)
    context = {
        "request": request,
        "user": admin,
        "tenants": tenants,
        "active": "tenants",
    }
    html = render_template("admin/admin_tenants.html", context)
    return HTMLResponse(html)
