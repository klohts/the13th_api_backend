import logging
from typing import Any, Dict, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Request,
    UploadFile,
)
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from backend_v2.db import get_db
from backend_v2.ingestion.services import (
    IngestionError,
    ingest_leads_from_csv_content,
)

logger = logging.getLogger("the13th.backend_v2.routers.admin_ingestion")

router = APIRouter(tags=["admin-ingestion"])

# Same templates root as the rest of your admin
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
    """
    Render the admin CSV upload page.

    Lets an internal admin upload a CSV for a given tenant/brokerage.
    """
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
    """
    Handle CSV upload from the admin UI and display ingestion results.
    """
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
    except Exception as exc:  # safety net
        logger.exception("Unexpected error during admin CSV ingestion")
        context["error"] = f"Unexpected error during CSV ingestion: {exc}"
        return templates.TemplateResponse(
            "admin_ingestion_csv.html",
            context,
            status_code=500,
        )

    return templates.TemplateResponse("admin_ingestion_csv.html", context)
