from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Lead(SQLModel, table=True):
    """Lead entity for brokerages."""

    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    brokerage_name: str = Field(index=True, max_length=255)
    first_name: str = Field(max_length=100)
    last_name: str = Field(max_length=100)
    email: str = Field(index=True, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=50)

    source: Optional[str] = Field(
        default=None,
        description="Lead source (portal, website, Facebook, etc.).",
        max_length=100,
        index=True,
    )
    status: str = Field(
        default="new",
        description="new, contacted, qualified, converted, lost, etc.",
        max_length=50,
        index=True,
    )
    assigned_agent: Optional[str] = Field(
        default=None,
        description="Name or identifier of the assigned agent.",
        max_length=255,
        index=True,
    )
    price_range: Optional[str] = Field(
        default=None,
        description="Textual price range or budget band.",
        max_length=100,
    )
    notes: Optional[str] = Field(
        default=None,
        description="Free-form notes.",
    )

    def touch(self) -> None:
        """Update the `updated_at` timestamp."""
        self.updated_at = datetime.utcnow()
