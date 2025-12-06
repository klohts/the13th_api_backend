# backend_v2/routers/admin_ingestion.py
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend_v2.db import get_db
from backend_v2.ingestion.services import IngestionError, ingest_leads_from_csv_content
from backend_v2.models.ingestion_event import IngestionEvent

logger = logging.getLogger("the13th.backend_v2.routers.admin_ingestion")

router = APIRouter(tags=["admin-ingestion"])

templates = Jinja2Templates(directory="backend_v2/templates")


@router.get(
    "/admin/ingestion/csv",
    response_class=HTMLResponse,
    summary="Admin CSV ingestion page",
)
def admin_csv_ingestion_form(
    request: Request,
    tenant_key: Optional[str] = None,
) -> HTMLResponse:
    context: Dict[str, Any] = {
        "request": request,
        "tenant_key": tenant_key or "",
        "default_source": "csv_import",
        "result": None,
        "error": None,
    }
    return templates.TemplateResponse("admin_ingestion_csv.html", context)


@router.post(
    "/admin/ingestion/csv",
    response_class=HTMLResponse,
    summary="Handle admin CSV ingestion",
)
async def admin_csv_ingestion_submit(
    request: Request,
    file: UploadFile = File(..., description="CSV file containing leads."),
    tenant_key: Optional[str] = Form(
        default=None,
        description="Tenant/brokerage identifier to associate with all leads.",
    ),
    default_source: str = Form(
        default="csv_import",
        description="Lead source label to assign to all ingested rows.",
    ),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    context: Dict[str, Any] = {
        "request": request,
        "tenant_key": tenant_key or "",
        "default_source": default_source,
        "result": None,
        "error": None,
    }

    if not file.filename.lower().endswith(".csv"):
        logger.warning("Admin attempted to upload non-CSV file: %s", file.filename)
        context["error"] = "Only CSV files are supported. Please upload a .csv file."
        return templates.TemplateResponse(
            "admin_ingestion_csv.html",
            context,
            status_code=400,
        )

    try:
        file_bytes = await file.read()
        result_counts = ingest_leads_from_csv_content(
            file_bytes=file_bytes,
            db=db,
            tenant_key=tenant_key,
            default_source=default_source,
        )
        context["result"] = {
            "total_rows": result_counts["total_rows"],
            "ingested_rows": result_counts["ingested_rows"],
            "skipped_rows": result_counts["skipped_rows"],
            "source": default_source,
            "tenant_key": tenant_key,
            "filename": file.filename,
        }
    except IngestionError as exc:
        logger.error("CSV ingestion error: %s", exc, exc_info=True)
        context["error"] = f"CSV ingestion error: {exc}"
        return templates.TemplateResponse(
            "admin_ingestion_csv.html",
            context,
            status_code=400,
        )
    except Exception as exc:
        logger.exception("Unexpected error during admin CSV ingestion")
        context["error"] = f"Unexpected error during CSV ingestion: {exc}"
        return templates.TemplateResponse(
            "admin_ingestion_csv.html",
            context,
            status_code=500,
        )

    return templates.TemplateResponse("admin_ingestion_csv.html", context)


@router.get(
    "/admin/ingestion/logs",
    response_class=HTMLResponse,
    summary="Ingestion activity log",
)
def admin_ingestion_logs(
    request: Request,
    db: Session = Depends(get_db),
    tenant_key: Optional[str] = None,
    source: Optional[str] = None,
    channel: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 200,
) -> HTMLResponse:
    """View recent ingestion events for debugging and trust."""
    limit = max(1, min(limit, 500))

    query = db.query(IngestionEvent).order_by(desc(IngestionEvent.created_at))

    if tenant_key:
        query = query.filter(IngestionEvent.tenant_key == tenant_key)
    if source:
        query = query.filter(IngestionEvent.source == source)
    if channel:
        query = query.filter(IngestionEvent.channel == channel)
    if status:
        query = query.filter(IngestionEvent.status == status)

    events = query.limit(limit).all()

    context: Dict[str, Any] = {
        "request": request,
        "tenant_key": tenant_key or "",
        "source": source or "",
        "channel": channel or "",
        "status": status or "",
        "limit": limit,
        "events": events,
    }
    return templates.TemplateResponse("admin_ingestion_logs.html", context)
