from __future__ import annotations

import logging
from pathlib import Path
from typing import Final, Any, Dict

from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi import Request

logger = logging.getLogger("the13th.backend_v2.services.render")

BACKEND_BASE_DIR: Final[Path] = Path(__file__).resolve().parent.parent
TEMPLATE_DIR: Final[Path] = BACKEND_BASE_DIR / "templates"
STATIC_DIR: Final[Path] = BACKEND_BASE_DIR / "static"

TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)

logger.debug("Template dir: %s", TEMPLATE_DIR)
logger.debug("Static dir: %s", STATIC_DIR)

templates = Jinja2Templates(directory=str(TEMPLATE_DIR))


def get_template_dir() -> Path:
    return TEMPLATE_DIR


def get_static_dir() -> Path:
    return STATIC_DIR

def render_template(name: str, context: Dict[str, Any]) -> HTMLResponse:
    """
    Thin wrapper around Starlette's TemplateResponse so routers can
    render Jinja templates with a consistent API.

    Expects `context` to include a `request` key.
    """
    request = context.get("request")
    if not isinstance(request, Request):
        raise ValueError("Context passed to render_template must include a 'request' key with a FastAPI Request instance.")
    return templates.TemplateResponse(name, context)