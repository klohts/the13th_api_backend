from __future__ import annotations

import logging
from typing import Dict

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from backend_v2.config import settings
from backend_v2.db import init_db
from backend_v2.routers import admin as admin_router
from backend_v2.routers import api as api_router
from backend_v2.routers import tenant as tenant_router

from backend_v2.routers import client_experience_sim
from backend_v2.api import pilot as pilot_api
from backend_v2.routers import ingestion as ingestion_router
from backend_v2.routers import demo_experience as demo_experience_router
from backend_v2.routers import admin_ingestion as admin_ingestion_router
from .routers import leads  # import the router module


import backend_v2.routers.pilot_admin as pilot_admin_router
import backend_v2.routers.pilot_request as pilot_request_router
import backend_v2.routers.stripe_webhooks as stripe_webhooks_router
from backend_v2.services.render import STATIC_DIR
import backend_v2.routers.admin_leads as admin_leads_router

# Load env early
load_dotenv()

logger = logging.getLogger("backend_v2.main")

templates = Jinja2Templates(directory="backend_v2/templates")

def create_app() -> FastAPI:
    import backend_v2.routers.admin_ingestion as admin_ingestion_router
    import backend_v2.routers.admin_lead_detail as admin_lead_detail_router
    import backend_v2.routers.admin_automation as admin_automation_router
    app = FastAPI(title=settings.app_name, debug=settings.debug)

    # CORS
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

    # Routers
    app.include_router(admin_router.router)
    app.include_router(pilot_request_router.router)
    app.include_router(api_router.router)
    app.include_router(tenant_router.router)
    app.include_router(client_experience_sim.router)
    app.include_router(demo_experience_router.router)
    app.include_router(leads.router, prefix="/admin")
    
    app.include_router(pilot_api.router)
    app.include_router(pilot_admin_router.router)
    app.include_router(stripe_webhooks_router.router)
    app.include_router(ingestion_router.router)
    app.include_router(admin_ingestion_router.router)
    app.include_router(admin_leads_router.router)
    app.include_router(admin_lead_detail_router.router)
    app.include_router(admin_automation_router.router)
    
    # Static
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.on_event("startup")
    async def on_startup() -> None:
        logger.info("Starting THE13TH Backend v2 app...")
        init_db()
        logger.info("THE13TH Backend v2 app started.")

    @app.get("/healthz")
    async def healthcheck() -> Dict[str, str]:
        return {"status": "ok", "app": settings.app_name}

    return app


    app = create_app()

# Expose ASGI app for Uvicorn
app = create_app()
