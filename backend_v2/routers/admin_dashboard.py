from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend_v2.database import get_db
from backend_v2.services.auth_service import authenticated_admin
from backend_v2.services.render import render_template

router = APIRouter(prefix="/admin", tags=["Admin → Dashboard"])


def _count_safe(db: Session, table: str) -> int:
    """
    Safely count rows in a table. Returns 0 if table or query fails.
    """
    try:
        row = db.execute(text(f"SELECT COUNT(*) AS c FROM {table}")).mappings().first()
        return int(row["c"]) if row and "c" in row else 0
    except Exception:
        return 0


def _get_recent_users(db: Session, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Fetch a small list of recent users for the admin dashboard.
    """
    try:
        rows = (
            db.execute(
                text(
                    """
                    SELECT id, email, created_at
                    FROM users
                    ORDER BY datetime(created_at) DESC
                    LIMIT :limit
                    """
                ),
                {"limit": limit},
            )
            .mappings()
            .all()
        )
        return [dict(r) for r in rows]
    except Exception:
        return []


def _get_recent_incoming_leads(db: Session, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Fetch recent live ingested leads from incoming_leads for the dashboard.
    """
    try:
        rows = (
            db.execute(
                text(
                    """
                    SELECT
                        id,
                        email,
                        company,
                        primary_focus,
                        team_size,
                        source,
                        created_at
                    FROM incoming_leads
                    ORDER BY datetime(created_at) DESC
                    LIMIT :limit
                    """
                ),
                {"limit": limit},
            )
            .mappings()
            .all()
        )
        return [dict(r) for r in rows]
    except Exception:
        return []


@router.get("/dashboard")
def admin_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    admin=Depends(authenticated_admin),
):
    """
    Admin Command Center – platform overview + live signals.
    Supports both legacy 'metrics' and newer 'stats' contexts.
    """

    total_users = _count_safe(db, "users")
    active_subs = _count_safe(db, "subscriptions")
    total_tenants = _count_safe(db, "tenants")
    total_invoices = _count_safe(db, "invoice")

    # Legacy-style metrics (for older admin_dashboard.html templates)
    metrics: Dict[str, Any] = {
        "total_tenants": total_tenants,
        "total_users": total_users,
        "active_subscriptions": active_subs,
        "mrr_30": 0,
        "mrr_30_display": "$0",
    }

    # Newer cinematic stats object
    stats: Dict[str, Any] = {
        "total_users": total_users,
        "active_subscriptions": active_subs,
        "total_plans": 0,
        "mrr_30_display": "$0",
        "total_invoices": total_invoices,
        "new_users_7d": 0,  # placeholder until wired
    }

    webhook_stats: Dict[str, Any] = {
        "total_24h": 0,
        "errors_24h": 0,
        "last_event_at": None,
    }

    automation_stats: Dict[str, Any] = {
        "total": 0,
        "success_rate": 100,
        "error": 0,
    }

    users = _get_recent_users(db, limit=12)
    recent_live_leads = _get_recent_incoming_leads(db, limit=10)

    # Billing + signals (empty placeholders for now)
    recent_invoices: List[Dict[str, Any]] = []
    recent_webhooks: List[Dict[str, Any]] = []
    recent_automations: List[Dict[str, Any]] = []

    context = {
        "request": request,
        "user": admin,
        "active": "dashboard",
        "metrics": metrics,
        "stats": stats,
        "webhook_stats": webhook_stats,
        "automation_stats": automation_stats,
        "users": users,
        "recent_invoices": recent_invoices,
        "recent_webhooks": recent_webhooks,
        "recent_automations": recent_automations,
        "recent_live_leads": recent_live_leads,
    }

    # render_template ALREADY RETURNS a TemplateResponse → return it directly
    return render_template("admin/admin_dashboard.html", context)

