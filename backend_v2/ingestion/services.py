# backend_v2/ingestion/services.py
import csv
import io
import logging
from typing import Dict, Iterable, Optional

from sqlalchemy.orm import Session

from backend_v2.ingestion.config import ingestion_settings
from backend_v2.ingestion.schemas import LeadWebhookPayload
from backend_v2.models.lead import Lead
from backend_v2.models.ingestion_event import IngestionEvent
from backend_v2.automation.lead_automation import maybe_trigger_first_touch_email

logger = logging.getLogger("backend_v2.ingestion.services")


class IngestionError(Exception):
    """Base exception for ingestion-related failures."""


class AuthenticationError(IngestionError):
    """Raised when an ingestion request is not properly authenticated."""


def _validate_api_key(api_key: Optional[str]) -> None:
    """Validate the provided API key against configured ingestion keys."""
    if not ingestion_settings.ingestion_api_keys:
        logger.warning(
            "INGESTION_API_KEYS not configured. Accepting webhook without API key restriction."
        )
        return

    if not api_key:
        raise AuthenticationError("Missing ingestion API key.")

    if api_key not in ingestion_settings.ingestion_api_keys:
        raise AuthenticationError("Invalid ingestion API key.")


def _log_ingestion_event(
    db: Session,
    *,
    tenant_key: Optional[str],
    source: str,
    channel: str,
    status: str,
    message: str,
    lead_id: Optional[int] = None,
    raw_payload: Optional[Dict] = None,
) -> IngestionEvent:
    event = IngestionEvent(
        tenant_key=tenant_key,
        source=source,
        channel=channel,
        status=status,
        message=message,
        lead_id=lead_id,
        raw_payload=raw_payload or {},
    )
    db.add(event)
    return event


def ingest_lead_from_webhook(
    payload: LeadWebhookPayload,
    db: Session,
    api_key: Optional[str],
) -> Lead:
    """Ingest a single lead from a webhook payload with logging + automation."""
    _validate_api_key(api_key)

    source = payload.source.lower().strip()

    lead = Lead(
        tenant_key=payload.tenant_key,
        source=source,
        full_name=payload.full_name,
        email=payload.email,
        phone=payload.phone,
        assigned_agent=payload.assigned_agent,
        status="new",
        external_id=payload.external_id,
        raw_payload=payload.raw_payload or {},
    )

    db.add(lead)
    db.flush()  # assign PK for logging and automation

    _log_ingestion_event(
        db,
        tenant_key=payload.tenant_key,
        source=source,
        channel="webhook",
        status="success",
        message="Lead ingested via webhook.",
        lead_id=lead.id,
        raw_payload=payload.raw_payload or {},
    )

    maybe_trigger_first_touch_email(lead, db)

    db.commit()
    db.refresh(lead)

    logger.info(
        "Ingested lead via webhook (id=%s, tenant=%s, source=%s, email=%s)",
        lead.id,
        lead.tenant_key,
        lead.source,
        lead.email,
    )

    return lead


def _normalize_csv_row(row: Dict[str, str]) -> Dict[str, Optional[str]]:
    """Normalize a CSV row into canonical lead fields."""
    lower_keys = {k.lower().strip(): k for k in row.keys()}

    def pick(*candidates: str) -> Optional[str]:
        for c in candidates:
            if c in lower_keys:
                return row.get(lower_keys[c]) or None
        return None

    first_name = pick("first_name", "firstname", "fname")
    last_name = pick("last_name", "lastname", "lname")
    full_name = pick("full_name", "name", "contact_name")
    if not full_name and (first_name or last_name):
        parts = [p for p in [first_name, last_name] if p]
        full_name = " ".join(parts) if parts else None

    return {
        "full_name": (full_name or "").strip() or None,
        "email": pick("email", "email_address"),
        "phone": pick("phone", "phone_number", "mobile", "mobile_phone"),
        "assigned_agent": pick("agent", "agent_name", "assigned_agent"),
        "external_id": pick("id", "lead_id", "external_id"),
    }


def ingest_leads_from_csv_content(
    file_bytes: bytes,
    db: Session,
    tenant_key: Optional[str],
    default_source: str = "csv_import",
) -> Dict[str, int]:
    """Ingest leads from a CSV file with activity logging and automation."""
    max_bytes = ingestion_settings.max_csv_size_mb * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise IngestionError(
            f"CSV file too large. Max allowed is {ingestion_settings.max_csv_size_mb} MB."
        )

    try:
        text_stream = io.StringIO(file_bytes.decode("utf-8-sig"))
    except UnicodeDecodeError:
        text_stream = io.StringIO(file_bytes.decode("latin-1"))

    reader: Iterable[Dict[str, str]] = csv.DictReader(text_stream)
    total_rows = 0
    ingested_rows = 0
    source = default_source.lower().strip()

    for row in reader:
        total_rows += 1
        normalized = _normalize_csv_row(row)

        if not any(normalized.values()):
            logger.debug("Skipping empty CSV row: %s", row)
            _log_ingestion_event(
                db,
                tenant_key=tenant_key,
                source=source,
                channel="csv",
                status="skipped",
                message="Row skipped: no mappable lead fields.",
                raw_payload=row,
            )
            continue

        lead = Lead(
            tenant_key=tenant_key,
            source=source,
            full_name=normalized["full_name"],
            email=normalized["email"],
            phone=normalized["phone"],
            assigned_agent=normalized["assigned_agent"],
            status="new",
            external_id=normalized["external_id"],
            raw_payload=row,
        )
        db.add(lead)
        db.flush()

        _log_ingestion_event(
            db,
            tenant_key=tenant_key,
            source=source,
            channel="csv",
            status="success",
            message="Lead ingested via CSV.",
            lead_id=lead.id,
            raw_payload=row,
        )

        maybe_trigger_first_touch_email(lead, db)

        ingested_rows += 1

    db.commit()

    skipped_rows = max(total_rows - ingested_rows, 0)

    logger.info(
        "CSV ingest completed (tenant=%s, source=%s, total=%s, ingested=%s, skipped=%s)",
        tenant_key,
        source,
        total_rows,
        ingested_rows,
        skipped_rows,
    )

    return {
        "total_rows": total_rows,
        "ingested_rows": ingested_rows,
        "skipped_rows": skipped_rows,
    }
