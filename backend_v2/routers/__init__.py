from __future__ import annotations

import logging
from importlib import import_module
from types import ModuleType
from typing import List

logger = logging.getLogger(__name__)

# List router submodules that can be lazily imported.
# It's safe if some of these do not exist; we just won't touch them unless accessed.
_ROUTER_MODULES: List[str] = [
    "health",
    "admin",
    "admin_dashboard",
    "admin_leads",
    "admin_reports",
    "admin_tenants",
    "api",
    "billing",
    "client_dashboard",
    "client_experience_sim",
    "demo_experience",
    "ingestion",
    "pilot_admin",
    "pilot_admin_api",
    "pilot_admin_ui",
    "pilot_request",
    "public",
    "public_intel",
    "sim_client_agent",
    "sim_client_dashboard",
    "sim_client_inspector",
    "sim_email",
    "sim_email_router",
    "sim_lab",
    "sim_master",
    "tenant",
]

__all__ = _ROUTER_MODULES


def __getattr__(name: str) -> ModuleType:
    """
    Lazy import router submodules so that:

        from backend_v2.routers import admin as admin_router

    works without eagerly importing everything (and avoids circular imports).
    """
    if name not in _ROUTER_MODULES:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    full_name = f"{__name__}.{name}"
    logger.debug("Lazy-importing router module %s", full_name)
    module = import_module(full_name)
    return module
