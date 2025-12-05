# backend_v2/auth.py

"""
Admin authentication helpers for THE13TH backend.

Currently uses a simple header-based admin secret:
- Set ADMIN_DASHBOARD_SECRET in your environment.
- Include `X-Admin-Secret: <that_value>` on admin requests.

If ADMIN_DASHBOARD_SECRET is not set, authenticated_admin()
will allow all requests (useful for local dev).
"""

import logging
import os
from typing import Any

from fastapi import Depends, HTTPException, Request, status

logger = logging.getLogger("backend_v2.auth")


def _get_admin_secret() -> str | None:
    """Return the configured admin secret, or None if not set."""
    secret = os.getenv("ADMIN_DASHBOARD_SECRET")
    if not secret:
        logger.warning(
            "ADMIN_DASHBOARD_SECRET is not set; admin endpoints are effectively unprotected. "
            "Set this env var in production."
        )
    return secret


def authenticated_admin(request: Request) -> Any:
    """
    Dependency used on admin routes.

    - If ADMIN_DASHBOARD_SECRET is set:
        Require header `X-Admin-Secret` to match that value.
    - If not set:
        Allow all requests (dev mode).
    """
    admin_secret = _get_admin_secret()
    if not admin_secret:
        # Dev / local mode – no secret configured
        return {"admin": True, "mode": "unprotected"}

    provided = request.headers.get("X-Admin-Secret")
    if provided != admin_secret:
        logger.warning("Unauthorized admin access attempt from %s", request.client.host if request.client else "unknown")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized admin access",
        )

    return {"admin": True, "mode": "header-secret"}
