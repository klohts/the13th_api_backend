from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend_v2.models.sim_reports_log import SimReportLog

logger = logging.getLogger("the13th.report_viewer_service")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_get(obj: Any, name: str, default: Any = None) -> Any:
    return getattr(obj, name, default)


def _format_dt(dt: Optional[datetime]) -> str:
    if not dt:
        return ""
    try:
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(dt)


def _detect_timestamp_field() -> str:
    """
    Determine which timestamp field exists on SimReportLog.
    Returns the attribute name.
    """
    candidates = [
        "created_at",
        "generated_at",
        "created",
        "timestamp",
        "ts",
        "run_at",
    ]
    for c in candidates:
        if hasattr(SimReportLog, c):
            return c
    # Fallback to first column
    return "id"


TIMESTAMP_FIELD = _detect_timestamp_field()
logger.info(f"[ReportViewer] Using timestamp field: {TIMESTAMP_FIELD}")


# ---------------------------------------------------------------------------
# Query list
# ---------------------------------------------------------------------------

def list_reports(db: Session, limit: int = 200) -> List[Dict[str, Any]]:
    """
    Fetch all reports using a tolerant, schema-flexible approach.
    """

    try:
        timestamp_col = getattr(SimReportLog, TIMESTAMP_FIELD)
        rows = (
            db.query(SimReportLog)
            .order_by(timestamp_col.desc())
            .limit(limit)
            .all()
        )
    except SQLAlchemyError as exc:
        logger.exception("Failed to query SimReportLog: %r", exc)
        return []

    items: List[Dict[str, Any]] = []

    for row in rows:
        timestamp_val = _safe_get(row, TIMESTAMP_FIELD)

        company = (
            _safe_get(row, "company_name")
            or _safe_get(row, "tenant_name")
            or _safe_get(row, "account_name")
            or _safe_get(row, "org_name")
            or "-"
        )

        report_type = (
            _safe_get(row, "report_type")
            or _safe_get(row, "kind")
            or "simulation"
        )

        title = (
            _safe_get(row, "title")
            or _safe_get(row, "summary")
            or f"Report #{_safe_get(row, 'id', '—')}"
        )

        summary = (
            _safe_get(row, "summary")
            or _safe_get(row, "short_summary")
            or _safe_get(row, "title")
        )

        items.append({
            "id": _safe_get(row, "id"),
            "company": company,
            "report_type": report_type,
            "title": str(title),
            "summary": str(summary or ""),
            "created_at_human": _format_dt(timestamp_val),
        })

    return items


# ---------------------------------------------------------------------------
# Query detail
# ---------------------------------------------------------------------------

def get_report_detail(db: Session, report_id: int) -> Optional[Dict[str, Any]]:
    try:
        row = (
            db.query(SimReportLog)
            .filter(SimReportLog.id == report_id)
            .one_or_none()
        )
    except SQLAlchemyError as exc:
        logger.exception("Failed to load SimReportLog id=%s: %r", report_id, exc)
        return None

    if row is None:
        return None

    timestamp_val = _safe_get(row, TIMESTAMP_FIELD)

    company = (
        _safe_get(row, "company_name")
        or _safe_get(row, "tenant_name")
        or _safe_get(row, "account_name")
        or _safe_get(row, "org_name")
        or "-"
    )

    report_type = (
        _safe_get(row, "report_type")
        or _safe_get(row, "kind")
        or "simulation"
    )

    title = (
        _safe_get(row, "title")
        or _safe_get(row, "summary")
        or f"Report #{_safe_get(row, 'id', '—')}"
    )

    # Try to find an HTML body
    html_candidates = [
        "html_body",
        "report_html",
        "rendered_html",
        "html",
        "body_html",
    ]
    html_body = None
    for field in html_candidates:
        v = _safe_get(row, field)
        if v:
            html_body = str(v)
            break

    # Raw metadata for debugging
    raw_dict = {}
    try:
        raw_dict = {
            k: v
            for k, v in row.__dict__.items()
            if not k.startswith("_sa_")
        }
    except Exception:
        pass

    try:
        raw_json = json.dumps(raw_dict, indent=2, default=str)
    except Exception:
        raw_json = str(raw_dict)

    return {
        "id": _safe_get(row, "id"),
        "company": company,
        "report_type": report_type,
        "title": str(title),
        "created_at_human": _format_dt(timestamp_val),
        "html_body": html_body,
        "raw_meta_json": raw_json,
    }
