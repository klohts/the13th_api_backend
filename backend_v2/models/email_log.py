from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class EmailLog(SQLModel, table=True):
    """Simple log of simulated email traffic for THE13TH."""

    id: Optional[int] = Field(default=None, primary_key=True)
    lead_identifier: str = Field(index=True, max_length=255)
    direction: str = Field(
        max_length=32,
        description="outbound_ai | inbound_lead | outbound_agent | system",
    )
    sender_label: str = Field(max_length=64)
    subject: str = Field(default="", max_length=255)
    body: str
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        index=True,
    )
    meta: Optional[str] = Field(
        default=None,
        max_length=1024,
        description="Optional JSON/string metadata for debugging.",
    )
