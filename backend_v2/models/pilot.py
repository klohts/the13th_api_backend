from __future__ import annotations

import logging
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import SQLModel, Field

logger = logging.getLogger("the13th.backend_v2.models.pilot")


class PilotStatus(str, Enum):
    """
    Lifecycle states for a THE13TH paid pilot.
    These map directly to the admin dashboard and Stripe flow.
    """

    REQUESTED = "REQUESTED"          # User submitted pilot request
    APPROVAL_SENT = "APPROVAL_SENT"  # Stripe checkout link sent
    ACTIVE = "ACTIVE"                # Payment received / pilot live


class PilotBase(SQLModel):
    """Shared fields for Pilot requests."""

    brokerage_name: str = Field(
        index=True,
        description="Brokerage / office name",
    )

    contact_name: Optional[str] = Field(
        default=None,
        description="Primary contact name at the brokerage",
    )

    contact_email: str = Field(
        index=True,
        description="Primary contact email for this pilot",
    )

    role: Optional[str] = Field(
        default=None,
        description="Role of the contact (Owner, Broker, Ops Manager, etc.)",
    )

    agents_count: Optional[int] = Field(
        default=None,
        description="Approximate number of agents in this brokerage",
    )

    problem_notes: Optional[str] = Field(
        default=None,
        description="Free-text notes on main bottlenecks / problems",
    )

    status: PilotStatus = Field(
        default=PilotStatus.REQUESTED,
        description="Lifecycle status of the pilot",
        index=True,
    )

    requested_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the pilot was requested (admin-facing timestamp)",
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Row creation timestamp",
    )

    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Row last-updated timestamp",
    )


class Pilot(PilotBase, table=True):
    """
    Pilot request record for THE13TH paid pilot workflow.

    Uses a dedicated table name 'pilot_requests' to avoid clashing with
    any legacy tables or future analytics tables.
    """

    __tablename__ = "pilot_requests"

    id: Optional[int] = Field(default=None, primary_key=True)


def touch_pilot_for_update(pilot: Pilot) -> None:
    """
    Helper to update the `updated_at` timestamp safely.
    Should be called before any commit that mutates a Pilot row.
    """
    pilot.updated_at = datetime.utcnow()
    logger.debug(
        "Pilot %s touched for update at %s",
        pilot.id,
        pilot.updated_at,
    )
