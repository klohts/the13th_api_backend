import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, EmailStr, Field, ConfigDict


class LeadWebhookPayload(BaseModel):
    """Canonical payload for webhook-based lead ingestion."""

    tenant_key: Optional[str] = Field(
        default=None,
        description="Identifier for the brokerage/tenant (external or internal key).",
    )
    source: str = Field(
        ...,
        description="Lead source identifier (e.g., 'facebook', 'website', 'google').",
    )
    full_name: Optional[str] = Field(
        default=None,
        description="Lead full name, if available.",
    )
    email: Optional[EmailStr] = Field(
        default=None,
        description="Lead email address.",
    )
    phone: Optional[str] = Field(
        default=None,
        description="Lead phone number (raw string).",
    )
    assigned_agent: Optional[str] = Field(
        default=None,
        description="Optional agent identifier or name, if routing is handled upstream.",
    )
    external_id: Optional[str] = Field(
        default=None,
        description="External lead ID from upstream source (if provided).",
    )
    raw_payload: Dict[str, Any] = Field(
        default_factory=dict,
        description="Original raw payload as provided by the source (for audit/debug).",
    )


class LeadResponse(BaseModel):
    """Response model for a single ingested lead."""

    id: int
    tenant_key: Optional[str]
    source: str
    full_name: Optional[str]
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    assigned_agent: Optional[str]
    status: str
    external_id: Optional[str] = None
    created_at: datetime.datetime

    # Pydantic v2: enable from_orm / from_attributes
    model_config = ConfigDict(from_attributes=True)


class BulkCSVIngestResponse(BaseModel):
    """Response for CSV bulk ingestion."""

    total_rows: int
    ingested_rows: int
    skipped_rows: int
    source: str
    tenant_key: Optional[str]
