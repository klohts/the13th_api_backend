from __future__ import annotations

import logging
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import SQLModel, Field

logger = logging.getLogger("the13th.backend_v2.models.pilot")


class PilotStatus(str, Enum):
    REQUESTED = "REQUESTED"
    APPROVAL_SENT = "APPROVAL_SENT"
    ACTIVE = "ACTIVE"


class PilotBase(SQLModel):
    """Shared fields for Pilot."""

    brokerage_name: str = Field(index=True, description="Brokerage / office name")
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

    # In the template we reference `pilot.agents or pilot.agents_count`,
    # so we store the true column as `agents_count`.
    agents_count: Optional[int] = Field(
        default=None,
        description="Approximate number of agents in this brokerage",
    )

    problem_notes: Optional[str] = Field(
        default=None,
        description="Free-text notes on their main bottlenecks / problems",
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
    """Pilot request record for THE13TH paid pilot workflow."""
    id: Optional[int] = Field(default=None, primary_key=True)


def touch_pilot_for_update(pilot: Pilot) -> None:
    """
    Helper to update the `updated_at` timestamp safely.
    Can be called by services or routers before commit.
    """
    pilot.updated_at = datetime.utcnow()
    logger.debug("Pilot %s touched for update at %s", pilot.id, pilot.updated_at)
