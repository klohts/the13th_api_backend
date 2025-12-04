from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from backend_v2.services.render import render_template

router = APIRouter(tags=["Public"])

@router.get("/", response_class=HTMLResponse)
def landing_page(request: Request):
    context = {
        "request": request,
        "active": "home",
    }
    html = render_template("landing.html", context)
    return HTMLResponse(html)

@router.get("/demo", response_class=HTMLResponse)
def demo_page(request: Request):
    context = {
        "request": request,
        "active": "demo",
    }
    # Uses your existing demo.html
    html = render_template("demo.html", context)
    return HTMLResponse(html)
