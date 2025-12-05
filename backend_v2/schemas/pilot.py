from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from backend_v2.models.pilot import PilotStatus


class PilotRequest(BaseModel):
    """
    Public-facing payload when a brokerage requests a pilot
    (e.g., from landing/pilot.html).
    """

    contact_name: str = Field(..., max_length=255)
    contact_email: EmailStr
    brokerage_name: str = Field(..., max_length=255)
    website: Optional[str] = Field(default=None, max_length=255)
    pilot_days: int = Field(default=7, ge=1, le=30)


# For compatibility with any internal naming using "PilotCreateFromLead"
PilotCreateFromLead = PilotRequest


class PilotAdminView(BaseModel):
    """
    Admin view of a pilot record.
    """

    id: int
    created_at: datetime
    updated_at: datetime

    contact_name: str
    contact_email: EmailStr
    brokerage_name: str
    website: Optional[str]

    pilot_days: int
    pilot_start_date: Optional[date]
    pilot_end_date: Optional[date]

    status: PilotStatus
    stripe_checkout_session_id: Optional[str]
    stripe_customer_id: Optional[str]
    stripe_price_id: Optional[str]

    class Config:
        from_attributes = True


class PilotApproveRequest(BaseModel):
    """
    Admin payload to approve a pilot; may adjust pilot_days or start_date.
    """

    pilot_start_date: Optional[date] = None
    pilot_days: Optional[int] = Field(default=None, ge=1, le=30)


class PilotApproveResponse(BaseModel):
    """
    Response when a pilot is approved and a Stripe Checkout session is created.
    """

    pilot_id: int
    checkout_url: str


class StripeWebhookAck(BaseModel):
    """
    Simple ACK envelope for Stripe webhook endpoint.
    """

    received: bool
