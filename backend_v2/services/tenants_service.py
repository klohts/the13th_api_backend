from __future__ import annotations

import logging
from typing import List, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger("backend_v2.tenants")

def fetch_all_tenants(db: Session) -> List[Dict[str, Any]]:
    """Return all tenants as list of dicts.

    We don't assume exact column schema; we just SELECT *.
    """
    try:
        rows = db.execute(text("SELECT * FROM tenants ORDER BY rowid DESC")).mappings().all()
        return [dict(r) for r in rows]
    except Exception as exc:
        logger.exception("Failed to fetch tenants: %s", exc)
        return []
