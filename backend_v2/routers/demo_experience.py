from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend_v2.db import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["demo-experience"])


# ---------------------------------------------------------------------------
# Demo data models
# ---------------------------------------------------------------------------

class DemoStage(BaseModel):
    """
    Matches what the Jinja template expects:
    - stage.name
    - stage.value
    """
    name: str
    value: str


class DemoBrokerage(BaseModel):
    name: str
    city: str
    state: str
    agent_count: int
    monthly_lead_volume: int


class DemoLead(BaseModel):
    id: int
    full_name: str
    city: str
    budget: int
    source: str
    stage: DemoStage
    intent_score: int = Field(ge=0, le=100)
    probability_to_close: int = Field(ge=0, le=100)
    is_primary_demo: bool = False
    notes: Optional[str] = None


class DemoTimelineEvent(BaseModel):
    day_offset: int = Field(ge=0)
    day: Optional[int] = None
    title: str
    description: str
    channel: str
    actor: str  # "Lead", "Agent", "AI-admin"
    event_type: str  # "lead_created", "email_outbound", etc.
    sentiment: str = "neutral"  # "positive", "neutral", "negative"
    risk_flag: bool = False
    risk_label: Optional[str] = None
    system_generated: bool = False


# ---------------------------------------------------------------------------
# Demo data factory
# ---------------------------------------------------------------------------

def _stage(code: str) -> DemoStage:
    """
    Helper so we never mistype stages.

    Template checks:
      - stage.value == 'decision_window' | 'active_search' | 'engaged'
      - stage.name.replace("_", " ") | title
    """
    return DemoStage(name=code, value=code)


def _build_demo_brokerage() -> DemoBrokerage:
    return DemoBrokerage(
        name="Harborline Realty Group",
        city="Austin",
        state="TX",
        agent_count=26,
        monthly_lead_volume=180,
    )


def _build_demo_leads() -> List[DemoLead]:
    return [
        DemoLead(
            id=1,
            full_name="Sarah Miller",
            city="Austin, TX",
            budget=850_000,
            source="Google PPC",
            stage=_stage("decision_window"),
            intent_score=92,
            probability_to_close=78,
            is_primary_demo=True,
            notes=(
                "Relocating from out of state, time-sensitive move tied to new role."
            ),
        ),
        DemoLead(
            id=2,
            full_name="James Rodriguez",
            city="Austin, TX",
            budget=650_000,
            source="Zillow",
            stage=_stage("active_search"),
            intent_score=81,
            probability_to_close=64,
            notes="Prefers email, shopping between 3 brokerages.",
        ),
        DemoLead(
            id=3,
            full_name="Lisa Thompson",
            city="Round Rock, TX",
            budget=520_000,
            source="Facebook Lead Form",
            stage=_stage("engaged"),
            intent_score=74,
            probability_to_close=52,
            notes="Raised hand on Facebook, needs guidance on pre-approval.",
        ),
    ]


def _build_demo_timeline(selected: DemoLead) -> List[DemoTimelineEvent]:
    """
    Roughly:

    - Day 0: inbound
    - Day 0: AI-admin first touch
    - Day 1: lead reply
    - Day 2: agent follow-up (AI-assisted)
    - Day 7: lull + risk alert
    - Day 8: AI-admin re-engagement
    - Day 9: lead returns
    - Day 15: tours + mortgage step
    - Day 21: decision-window risk
    - Day 23: context-aware check-in
    """
    name = selected.full_name

    events: List[DemoTimelineEvent] = [
        DemoTimelineEvent(
            day_offset=0,
            day=0,
            title="New lead captured",
            description=(
                f"{name} lands on the site from Google PPC and submits a relocation "
                "inquiry."
            ),
            channel="Web form",
            actor="Lead",
            event_type="lead_created",
            sentiment="neutral",
            risk_flag=False,
            system_generated=False,
        ),
        DemoTimelineEvent(
            day_offset=0,
            day=0,
            title="Instant AI-admin reply",
            description=(
                "THE13TH sends an intelligent first-touch email with 3 tailored "
                "questions and a soft call-to-action."
            ),
            channel="Email",
            actor="AI-admin",
            event_type="email_outbound",
            sentiment="positive",
            risk_flag=False,
            system_generated=True,
        ),
        DemoTimelineEvent(
            day_offset=1,
            day=1,
            title="Lead reply with context",
            description=(
                f"{name} replies with timing, budget, and preferred neighborhoods; "
                "mentions strict relocation deadline."
            ),
            channel="Email",
            actor="Lead",
            event_type="email_inbound",
            sentiment="positive",
            risk_flag=False,
            system_generated=False,
        ),
        DemoTimelineEvent(
            day_offset=2,
            day=2,
            title="Agent follow-up scheduled by AI-admin",
            description=(
                "AI-admin drafts a reply and proposes 2 appointment slots; agent "
                "approves with one click."
            ),
            channel="Email",
            actor="AI-admin",
            event_type="email_draft",
            sentiment="positive",
            risk_flag=False,
            system_generated=True,
        ),
        DemoTimelineEvent(
            day_offset=7,
            day=7,
            title="Momentum drop detected",
            description=(
                "No response for 5 days after the last touch. THE13TH flags the lead "
                "as at risk."
            ),
            channel="System",
            actor="AI-admin",
            event_type="risk_alert",
            sentiment="neutral",
            risk_flag=True,
            risk_label="Stalled after high-intent reply",
            system_generated=True,
        ),
        DemoTimelineEvent(
            day_offset=8,
            day=8,
            title="Re-engagement nudge sent",
            description=(
                "AI-admin sends a concise nudge email summarizing the last "
                "conversation and asking for a quick yes/no on availability."
            ),
            channel="Email",
            actor="AI-admin",
            event_type="email_outbound",
            sentiment="positive",
            risk_flag=False,
            system_generated=True,
        ),
        DemoTimelineEvent(
            day_offset=9,
            day=9,
            title="Buyer re-engages",
            description=(
                f"{name} confirms urgency and books a virtual consult via the "
                "scheduling link in the email."
            ),
            channel="Email",
            actor="Lead",
            event_type="email_inbound",
            sentiment="positive",
            risk_flag=False,
            system_generated=False,
        ),
        DemoTimelineEvent(
            day_offset=15,
            day=15,
            title="Tour + pre-approval milestone",
            description=(
                "Agent logs two property tours and marks pre-approval as in "
                "progress; THE13TH updates the journey and forecast."
            ),
            channel="CRM",
            actor="Agent",
            event_type="status_update",
            sentiment="positive",
            risk_flag=False,
            system_generated=False,
        ),
        DemoTimelineEvent(
            day_offset=21,
            day=21,
            title="Decision window risk spike",
            description=(
                "Seven days without new activity in the decision window. THE13TH "
                "surfaces a risk alert and suggests a check-in script."
            ),
            channel="System",
            actor="AI-admin",
            event_type="risk_alert",
            sentiment="neutral",
            risk_flag=True,
            risk_label="Silent during decision window",
            system_generated=True,
        ),
        DemoTimelineEvent(
            day_offset=23,
            day=23,
            title="Context-aware check-in sent",
            description=(
                "AI-admin drafts a concise check-in email referencing the tours and "
                "mortgage status, asking for a go/no-go."
            ),
            channel="Email",
            actor="AI-admin",
            event_type="email_outbound",
            sentiment="positive",
            risk_flag=False,
            system_generated=True,
        ),
    ]

    return events


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------

@router.get("/demo-experience", response_class=HTMLResponse)
def demo_experience(
    request: Request,
    lead_id: Optional[int] = Query(
        default=None,
        description="Optional demo lead id (1, 2, 3...)",
    ),
    db: Session = Depends(get_db),  # reserved for future real-data wiring
):
    """
    Cinematic client-facing demo page.

    Backed by curated demo data for now so the experience is stable for
    sales calls and recordings.
    """
    from backend_v2.main import templates  # local import to avoid circulars

    try:
        brokerage = _build_demo_brokerage()
        leads = _build_demo_leads()

        # Pick selected lead
        selected_lead: DemoLead | None = None
        if lead_id is not None:
            for lead in leads:
                if lead.id == lead_id:
                    selected_lead = lead
                    break

        if selected_lead is None:
            selected_lead = next((l for l in leads if l.is_primary_demo), leads[0])

        timeline_events = _build_demo_timeline(selected_lead)

        logger.info(
            "Rendering demo experience page",
            extra={
                "lead_id": selected_lead.id,
                "lead_name": selected_lead.full_name,
                "brokerage": brokerage.name,
            },
        )

        return templates.TemplateResponse(
            "demo_client_experience.html",
            {
                "request": request,
                # Pydantic -> dict so Jinja can do brokerage.city, etc.
                "brokerage": brokerage.model_dump(),
                "leads": [l.model_dump() for l in leads],
                "selected_lead": selected_lead.model_dump(),
                "timeline": [e.model_dump() for e in timeline_events],
            },
        )
    except Exception as exc:
        logger.exception("Error rendering demo experience page: %s", exc)

        # Safe, minimal fallback so page doesn't crash in front of a client
        return templates.TemplateResponse(
            "demo_client_experience.html",
            {
                "request": request,
                "brokerage": {
                    "name": "Demo Brokerage",
                    "city": "Austin",
                    "state": "TX",
                    "agent_count": 10,
                    "monthly_lead_volume": 120,
                },
                "leads": [],
                "selected_lead": None,
                "timeline": [],
            },
            status_code=200,
        )
