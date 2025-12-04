from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend_v2.database import get_db

logger = logging.getLogger("backend_v2.auth")

def _load_user_by_id(db: Session, user_id: int) -> Optional[Dict[str, Any]]:
    try:
        row = db.execute(
            text("SELECT * FROM users WHERE id = :id"),
            {{ "id": user_id }},
        ).mappings().first()
        if row:
            return dict(row)
    except Exception as exc:
        logger.exception("Failed to load user %s: %s", user_id, exc)
    return None

def _load_any_admin_or_first_user(db: Session) -> Optional[Dict[str, Any]]:
    # Try admin-like user
    try:
        row = db.execute(
            text("SELECT * FROM users WHERE role = 'admin' LIMIT 1")
        ).mappings().first()
        if row:
            return dict(row)
    except Exception:
        pass
    # Fallback: any user
    try:
        row = db.execute(
            text("SELECT * FROM users LIMIT 1")
        ).mappings().first()
        if row:
            return dict(row)
    except Exception as exc:
        logger.exception("Failed to load fallback user: %s", exc)
    return None

def get_current_user_from_request(
    request: Request,
    db: Session = Depends(get_db),
) -> Optional[Dict[str, Any]]:
    """Read user from cookie if present; otherwise fallback to first user.

    For now this is deliberately lenient so your local admin views always work.
    """
    cookie_val = request.cookies.get("session_user_id")
    if cookie_val:
        try:
            uid = int(cookie_val)
            user = _load_user_by_id(db, uid)
            if user:
                return user
        except Exception:
            logger.warning("Invalid session_user_id cookie: %r", cookie_val)

    # Fallback: pick any admin/first user
    user = _load_any_admin_or_first_user(db)
    if user:
        return user

    # As a last resort, synthesize a fake admin user
    return {{
        "id": 0,
        "email": "admin@local",
        "full_name": "Local Admin",
        "role": "admin",
    }}

def authenticated_user(
    request: Request,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    user = get_current_user_from_request(request, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated.",
        )
    return user

def authenticated_admin(
    request: Request,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    user = get_current_user_from_request(request, db)
    role = str(user.get("role", "")).lower()
    if role != "admin":
        # In local dev, still allow but log it; for now we don't block you.
        logger.warning("Non-admin user accessing admin route: %s", user)
    return user
