from __future__ import annotations

import logging
from typing import Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend_v2.config import settings
from backend_v2.db import init_db
from backend_v2.routers import admin as admin_router
from backend_v2.routers import api as api_router
from backend_v2.routers import tenant as tenant_router
from backend_v2.routers import client_experience_sim
from backend_v2.api import pilot as pilot_api
import backend_v2.routers.pilot_admin_ui as pilot_admin_ui
import backend_v2.routers.pilot_admin_api as pilot_admin_api
from backend_v2.services.render import STATIC_DIR

logger = logging.getLogger("backend_v2.main")

def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, debug=settings.debug)

    # CORS for marketing + local dev
    origins = [
        "http://localhost:5000",
        "http://127.0.0.1:5000",
        "https://the13thhq.com",
        "https://www.the13thhq.com",
        "https://the13thhq-site.pages.dev",
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    # Core routers
    app.include_router(admin_router.router)
    app.include_router(api_router.router)
    app.include_router(tenant_router.router)
    app.include_router(client_experience_sim.router)
    app.include_router(pilot_api.router)
    app.include_router(pilot_admin_api.router)  # ← JSON API

    # Admin Pilot Dashboard UI
    app.include_router(pilot_admin_ui.router)

    # Static files
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.on_event("startup")
    async def on_startup() -> None:
        """Initialize resources on startup."""
        logger.info("Starting THE13TH Backend v2 app...")
        init_db()
        logger.info("THE13TH Backend v2 app started.")

    @app.get("/healthz")
    async def healthcheck() -> Dict[str, str]:
        return {"status": "ok", "app": settings.app_name}

    return app


app = create_app()
