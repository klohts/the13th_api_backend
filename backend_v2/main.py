from __future__ import annotations

from backend_v2.routers import pilot_admin, stripe_webhooks

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

    origins = [
    "http://localhost:5000",
    "http://127.0.0.1:5000",
    "https://the13thhq.com",
    "https://the13thhq-site.pages.dev",
]

    app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
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

# Pilot admin routes
app.include_router(
    pilot_admin.router,
    prefix="/admin/pilots",
    tags=["admin-pilots"],
)

# Stripe webhooks
app.include_router(
    stripe_webhooks.router,
    prefix="/stripe",
    tags=["stripe"],
)
