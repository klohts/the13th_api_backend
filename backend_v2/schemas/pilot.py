from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from backend_v2.models.pilot_model import PilotStatus


class PilotRequest(BaseModel):
    """
    Incoming payload from the marketing /pilot form.

    Frontend sends:
    - email
    - full_name
    - brokerage_name
    - website
    - role
    - team_size
    - lead_volume
    - num_agents
    - problem
    - lead_context
    - notes
    - source
    """

    brokerage_name: str

    # Frontend: "email"  -> internal: contact_email
    contact_email: EmailStr = Field(alias="email")

    # Frontend: "full_name" -> internal: contact_name
    contact_name: str = Field(alias="full_name")

    website: Optional[str] = None
    role: Optional[str] = None

    team_size: Optional[str] = None
    lead_volume: Optional[str] = None
    num_agents: Optional[int] = None
    problem: Optional[str] = None
    lead_context: Optional[str] = None
    notes: Optional[str] = None
    source: Optional[str] = None

    @field_validator("website")
    @classmethod
    def normalize_website(cls, v: Optional[str]) -> Optional[str]:
        """Make website optional + auto-add https:// when missing."""
        if not v:
            return v
        v = v.strip()
        if not v:
            return None
        if not v.startswith(("http://", "https://")):
            v = "https://" + v
        return v

    # 🔁 Backwards-compat for existing email code expecting `work_email`
    @property
    def work_email(self) -> EmailStr:
        """
        Alias for legacy code that expects `pilot.work_email`.
        Uses the normalized contact_email field.
        """
        return self.contact_email


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
