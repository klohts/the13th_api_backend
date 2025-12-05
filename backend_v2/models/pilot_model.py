from __future__ import annotations

import enum
from datetime import datetime, date
from typing import Optional

from sqlmodel import SQLModel, Field


class PilotStatus(str, enum.Enum):
    REQUESTED = "REQUESTED"
    APPROVED_PENDING_PAYMENT = "APPROVED_PENDING_PAYMENT"
    ACTIVE = "ACTIVE"
    CANCELLED = "CANCELLED"


class Pilot(SQLModel, table=True):
    """
    Pilot record created when a brokerage requests a pilot.

    This model is SQLModel-based so it plays nicely with the existing
    backend_v2.db engine + metadata setup.
    """

    id: Optional[int] = Field(default=None, primary_key=True, index=True)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    contact_name: str = Field(max_length=255)
    contact_email: str = Field(max_length=255, index=True)
    brokerage_name: str = Field(max_length=255)
    website: Optional[str] = Field(default=None, max_length=255)

    pilot_days: int = Field(default=7, ge=1)
    pilot_start_date: Optional[date] = None
    pilot_end_date: Optional[date] = None

    status: PilotStatus = Field(default=PilotStatus.REQUESTED, index=True)

    stripe_checkout_session_id: Optional[str] = Field(default=None, max_length=255)
    stripe_customer_id: Optional[str] = Field(default=None, max_length=255)
    stripe_price_id: Optional[str] = Field(default=None, max_length=255)

    def mark_approved(self) -> None:
        self.status = PilotStatus.APPROVED_PENDING_PAYMENT

    def mark_active(
        self,
        *,
        customer_id: Optional[str],
        price_id: Optional[str],
        start_date: Optional[date],
        end_date: Optional[date],
    ) -> None:
        self.status = PilotStatus.ACTIVE
        self.stripe_customer_id = customer_id
        self.stripe_price_id = price_id
        self.pilot_start_date = start_date
        self.pilot_end_date = end_date
