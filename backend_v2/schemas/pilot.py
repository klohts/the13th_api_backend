# backend_v2/schemas/pilot.py
from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class PilotRequest(BaseModel):
    """Fields coming from the 7-day pilot request form."""

    work_email: EmailStr = Field(..., alias="email")
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    brokerage_name: str = Field(..., min_length=1, max_length=200)
    website: str | None = Field(None, max_length=255)
    agents_on_team: str | None = Field(None, alias="agents")
    monthly_online_leads: str | None = Field(None, alias="monthly_leads")
    primary_focus: str | None = None
    main_problem: str | None = None
    anything_special: str | None = None

    class Config:
        allow_population_by_field_name = True
