import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from backend_v2.db import get_db
from backend_v2.ingestion.schemas import (
    BulkCSVIngestResponse,
    LeadResponse,
    LeadWebhookPayload,
)
from backend_v2.ingestion.services import (
    AuthenticationError,
    IngestionError,
    ingest_lead_from_webhook,
    ingest_leads_from_csv_content,
)

logger = logging.getLogger("backend_v2.routers.ingestion")

router = APIRouter(
    prefix="/ingestion",
    tags=["ingestion"],
)


@router.post(
    "/webhook",
    response_model=LeadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a lead via webhook",
    description=(
        "Ingest a single lead from a webhook payload. "
        "Requires X-INGESTION-KEY header if INGESTION_API_KEYS is configured."
    ),
)
def ingest_webhook_lead(
    payload: LeadWebhookPayload,
    db: Session = Depends(get_db),
    x_ingestion_key: Optional[str] = None,
) -> LeadResponse:
    try:
        lead = ingest_lead_from_webhook(
            payload=payload,
            db=db,
            api_key=x_ingestion_key,
        )
    except AuthenticationError as exc:
        logger.warning("Webhook ingestion authentication failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc
    except IngestionError as exc:
        logger.error("Webhook ingestion error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:  # pragma: no cover - safety net
        logger.exception("Unexpected error during webhook ingestion")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected error during webhook ingestion.",
        ) from exc

    return LeadResponse.from_orm(lead)


@router.post(
    "/csv",
    response_model=BulkCSVIngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Bulk ingest leads via CSV upload",
    description=(
        "Ingest multiple leads from a CSV file. "
        "CSV headers are mapped heuristically to canonical lead fields."
    ),
)
async def ingest_csv_leads(
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
) -> BulkCSVIngestResponse:
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files are supported for bulk ingestion.",
        )

    try:
        file_bytes = await file.read()
        result_counts = ingest_leads_from_csv_content(
            file_bytes=file_bytes,
            db=db,
            tenant_key=tenant_key,
            default_source=default_source,
        )
    except IngestionError as exc:
        logger.error("CSV ingestion error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:  # pragma: no cover - safety net
        logger.exception("Unexpected error during CSV ingestion")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected error during CSV ingestion.",
        ) from exc

    return BulkCSVIngestResponse(
        total_rows=result_counts["total_rows"],
        ingested_rows=result_counts["ingested_rows"],
        skipped_rows=result_counts["skipped_rows"],
        source=default_source,
        tenant_key=tenant_key,
    )
