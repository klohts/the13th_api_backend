from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .db import init_db
from .routers import admin as admin_router
from .routers import api as api_router
from .routers import tenant as tenant_router
from .services.render import STATIC_DIR
from .routers import client_experience_sim
from backend_v2.api import pilot as pilot_api

logger = logging.getLogger("the13th.backend_v2.main")


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, debug=settings.debug)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    app.include_router(admin_router.router)
    app.include_router(api_router.router)
    app.include_router(tenant_router.router)
    app.include_router(client_experience_sim.router)
    app.include_router(pilot_api.router)

    # Static files
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    app.mount(
        "/static",
        StaticFiles(directory=str(STATIC_DIR)),
        name="static",
    )

    @app.on_event("startup")
    async def on_startup() -> None:  # noqa: D401
        """Initialize resources on startup."""
        logger.info("Starting THE13TH Backend v2 app...")
        init_db()
        logger.info("THE13TH Backend v2 app started.")

    @app.get("/healthz")
    async def healthcheck() -> dict:
        return {"status": "ok", "app": settings.app_name}

    return app


app = create_app()
