from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Session
from backend_v2.services.sim_email_service import SimEmailMessage, relationship

from backend_v2.sim_base import SimBase as Base
from backend_v2.database import engine

# Lazy import to avoid circular dependencies
def _get_email_overview(db):
    from backend_v2.services.sim_email_service import get_email_overview
    return get_email_overview(db)

logger = logging.getLogger("the13th.sim_lab.service")


# ============================================================
# ORM MODELS
# ============================================================

class SimCompany(Base):
    __tablename__ = "sim_companies"

    id: int = Column(Integer, primary_key=True, index=True)
    name: str = Column(String(255), nullable=False)
    segment: str = Column(String(100), nullable=True)
    region: str = Column(String(100), nullable=True)
    target_volume: int = Column(Integer, nullable=True)
    created_at: datetime = Column(DateTime, default=datetime.utcnow, nullable=False)

    leads = relationship("SimLead", back_populates="company", cascade="all, delete-orphan")


class SimLead(Base):
    __tablename__ = "sim_leads"

    id: int = Column(Integer, primary_key=True, index=True)
    company_id: int = Column(Integer, ForeignKey("sim_companies.id"), nullable=False)
    full_name: str = Column(String(255), nullable=False)
    email: str = Column(String(255), nullable=False)
    status: str = Column(String(50), nullable=False)
    stage: str = Column(String(50), nullable=False)
    score: int = Column(Integer, nullable=False)
    deal_value: int = Column(Integer, nullable=False)
    created_at: datetime = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: datetime = Column(DateTime, default=datetime.utcnow, nullable=False)

    company = relationship("SimCompany", back_populates="leads")


class SimBurst(Base):
    __tablename__ = "sim_bursts"

    id: int = Column(Integer, primary_key=True, index=True)
    run_at: datetime = Column(DateTime, default=datetime.utcnow, nullable=False)
    leads_created: int = Column(Integer, default=0, nullable=False)
    events_generated: int = Column(Integer, default=0, nullable=False)
    notes: str = Column(String(255), nullable=True)


# ============================================================
# CONSTANTS
# ============================================================

SIM_DEFAULT_COMPANIES = 5
SIM_LEADS_PER_COMPANY = 250

COMPANY_PROFILES = [
    {
        "name": "Northstar Realty Group",
        "segment": "High-volume buyer leads",
        "region": "US West",
        "target_volume": 250,
    },
    {
        "name": "Skyline Estates Collective",
        "segment": "Luxury listings & VIP buyers",
        "region": "US East",
        "target_volume": 250,
    },
    {
        "name": "Horizon Home Advisors",
        "segment": "First-time buyers & relocation",
        "region": "US South",
        "target_volume": 250,
    },
    {
        "name": "PrimeCity Realty Partners",
        "segment": "Urban condos & investors",
        "region": "US Northeast",
        "target_volume": 250,
    },
    {
        "name": "Evergreen Property Lab",
        "segment": "Suburban family homes",
        "region": "US Midwest",
        "target_volume": 250,
    },
]

LEAD_STATUSES = ["new", "nurturing", "won", "lost"]
LEAD_STAGES = ["top", "middle", "bottom"]


# ============================================================
# SCHEMA INIT
# ============================================================

def ensure_sim_schema() -> None:
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as exc:
        logger.exception("Failed to create Simulation Lab tables: %s", exc)
        raise


# ============================================================
# HELPERS
# ============================================================

def _generate_lead_name(idx: int, company_name: str) -> str:
    base = company_name.split()[0] if company_name else "Lead"
    return f"{base} Lead {idx}"


def _generate_lead_email(idx: int, company_name: str) -> str:
    slug = company_name.lower().replace(" ", "").replace("&", "and")
    return f"lead{idx}@{slug}.sim.the13th.io"


def _random_status_and_stage() -> Tuple[str, str]:
    status = random.choices(LEAD_STATUSES, weights=[0.45, 0.35, 0.1, 0.1], k=1)[0]
    stage = random.choices(LEAD_STAGES, weights=[0.5, 0.3, 0.2], k=1)[0]
    return status, stage


def _random_score_and_value(status: str) -> Tuple[int, int]:
    if status == "won":
        return random.randint(75, 100), random.randint(8000, 25000)
    if status == "nurturing":
        return random.randint(40, 85), random.randint(5000, 18000)
    if status == "lost":
        return random.randint(10, 60), random.randint(3000, 15000)
    return random.randint(20, 70), random.randint(3000, 12000)


# ============================================================
# SEED
# ============================================================

def seed_simulation_lab(
    db: Session,
    company_count: int = SIM_DEFAULT_COMPANIES,
    leads_per_company: int = SIM_LEADS_PER_COMPANY,
) -> Dict[str, Any]:

    ensure_sim_schema()

    existing_companies = db.query(SimCompany).count()
    existing_leads = db.query(SimLead).count()
    target_leads = company_count * leads_per_company

    if existing_companies >= company_count and existing_leads >= target_leads:
        return {
            "status": "ok",
            "message": "Simulation Lab already seeded; no changes.",
            "companies_existing": existing_companies,
            "leads_existing": existing_leads,
            "companies_created": 0,
            "leads_created": 0,
            "email": _get_email_overview(db),
        }

    companies_created = 0
    leads_created = 0

    companies = []

    if existing_companies == 0:
        profiles = COMPANY_PROFILES[:company_count]
        for profile in profiles:
            company = SimCompany(
                name=profile["name"],
                segment=profile["segment"],
                region=profile["region"],
                target_volume=profile["target_volume"],
            )
            db.add(company)
            companies.append(company)
            companies_created += 1

        for idx in range(len(companies) + 1, company_count + 1):
            company = SimCompany(
                name=f"Simulation Company {idx}",
                segment="General real estate",
                region="US",
                target_volume=leads_per_company,
            )
            db.add(company)
            companies.append(company)
            companies_created += 1

        db.flush()
    else:
        companies = db.query(SimCompany).all()

    # Create leads
    for company in companies:
        current_count = (
            db.query(SimLead).filter(SimLead.company_id == company.id).count()
        )
        to_create = max(0, leads_per_company - current_count)

        for i in range(current_count + 1, current_count + to_create + 1):
            status, stage = _random_status_and_stage()
            score, value = _random_score_and_value(status)
            created_at = datetime.utcnow() - timedelta(days=random.randint(0, 60))

            lead = SimLead(
                company_id=company.id,
                full_name=_generate_lead_name(i, company.name),
                email=_generate_lead_email(i, company.name),
                status=status,
                stage=stage,
                score=score,
                deal_value=value,
                created_at=created_at,
                updated_at=created_at,
            )
            db.add(lead)
            leads_created += 1

    if companies_created or leads_created:
        db.commit()

    return {
        "status": "ok",
        "message": "Simulation Lab seeded or topped up successfully.",
        "companies_created": companies_created,
        "leads_created": leads_created,
    }


# ============================================================
# SINGLE BURST
# ============================================================

def run_simulation_burst(
    db: Session,
    leads_per_company: int = 25,
) -> Dict[str, Any]:

    ensure_sim_schema()

    companies = db.query(SimCompany).all()
    if not companies:
        return {"status": "error", "message": "No companies. Seed first."}

    new_leads = 0
    updated_leads = 0

    for company in companies:
        current_count = (
            db.query(SimLead).filter(SimLead.company_id == company.id).count()
        )

        # Create new leads
        for i in range(current_count + 1, current_count + leads_per_company + 1):
            status, stage = _random_status_and_stage()
            score, value = _random_score_and_value(status)

            lead = SimLead(
                company_id=company.id,
                full_name=_generate_lead_name(i, company.name),
                email=_generate_lead_email(i, company.name),
                status=status,
                stage=stage,
                score=score,
                deal_value=value,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(lead)
            new_leads += 1

        # Update slice of existing leads
        sample_size = min(50, current_count)
        if sample_size > 0:
            sample = (
                db.query(SimLead)
                .filter(SimLead.company_id == company.id)
                .order_by(func.random())
                .limit(sample_size)
                .all()
            )

            for lead in sample:
                status, stage = _random_status_and_stage()
                score, value = _random_score_and_value(status)
                lead.status = status
                lead.stage = stage
                lead.score = score
                lead.deal_value = value
                lead.updated_at = datetime.utcnow()
                updated_leads += 1

    # Create a burst log entry (correct schema)
    burst = SimBurst(
        run_at=datetime.utcnow(),
        leads_created=new_leads,
        events_generated=updated_leads,
        notes="Standard simulation burst",
    )
    db.add(burst)

    db.commit()

    return {
        "status": "ok",
        "message": "Simulation burst completed.",
        "leads_created": new_leads,
        "leads_updated": updated_leads,
    }


# ============================================================
# MULTIPLE BURSTS
# ============================================================

def run_multiple_bursts(
    db: Session,
    burst_count: int,
    leads_per_company: int = 25,
) -> Dict[str, Any]:

    burst_count = max(1, min(burst_count, 50))

    total_new = 0
    total_updated = 0

    for i in range(burst_count):
        result = run_simulation_burst(db, leads_per_company=leads_per_company)
        if result.get("status") != "ok":
            return {
                "status": "error",
                "message": f"Stopped at burst {i+1}",
                "leads_created": total_new,
                "leads_updated": total_updated,
            }

        total_new += result["leads_created"]
        total_updated += result["leads_updated"]

    return {
        "status": "ok",
        "message": f"{burst_count} bursts completed.",
        "leads_created": total_new,
        "leads_updated": total_updated,
        "bursts_completed": burst_count,
    }


# ============================================================
# RESET
# ============================================================

def reset_simulation_lab(db: Session) -> Dict[str, Any]:

    ensure_sim_schema()

    leads_deleted = db.query(SimLead).delete()
    bursts_deleted = db.query(SimBurst).delete()
    companies_deleted = db.query(SimCompany).delete()

    db.commit()

    return {
        "status": "ok",
        "message": "Simulation Lab reset.",
        "companies_deleted": companies_deleted,
        "leads_deleted": leads_deleted,
        "bursts_deleted": bursts_deleted,
    }


# ============================================================
# OVERVIEW DASHBOARD
# ============================================================


def get_simulation_overview(db: Session) -> Dict[str, Any]:
    """
    Enhanced Simulation Overview powering the Simulation Master Dashboard.
    Backwards compatible with all previous callers.
    """

    ensure_sim_schema()

    # -------------------------------------------------------
    # LAB HEALTH
    # -------------------------------------------------------
    companies_count = db.query(SimCompany).count()
    leads_count = db.query(SimLead).count()

    # Burst metadata
    burst_count = db.query(SimBurst).count()
    leads_from_bursts, events_generated = db.query(
        func.coalesce(func.sum(SimBurst.leads_created), 0),
        func.coalesce(func.sum(SimBurst.events_generated), 0),
    ).one()

    # -------------------------------------------------------
    # PIPELINE STATUS BREAKDOWN
    # -------------------------------------------------------
    status_rows = (
        db.query(SimLead.status, func.count(SimLead.id))
        .group_by(SimLead.status)
        .all()
    )
    deal_distribution = {status: count for status, count in status_rows}

    # -------------------------------------------------------
    # SCORING BUCKETS
    # -------------------------------------------------------
    scoring_buckets = {"0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0}
    for score, cnt in (
        db.query(SimLead.score, func.count(SimLead.id))
        .group_by(SimLead.score)
        .all()
    ):
        if score <= 20:
            scoring_buckets["0-20"] += cnt
        elif score <= 40:
            scoring_buckets["21-40"] += cnt
        elif score <= 60:
            scoring_buckets["41-60"] += cnt
        elif score <= 80:
            scoring_buckets["61-80"] += cnt
        else:
            scoring_buckets["81-100"] += cnt

    # -------------------------------------------------------
    # MESSAGE MIX (client/assistant/system) via SimEmailMessage
    # -------------------------------------------------------
    try:
        msg_rows = (
            db.query(SimEmailMessage.direction, func.count(SimEmailMessage.id))
            .group_by(SimEmailMessage.direction)
            .all()
        )
    except Exception:
        msg_rows = []

    message_mix = {"client": 0, "assistant": 0, "system": 0}
    for direction, cnt in msg_rows:
        d = (direction or "").lower()
        if "inbound" in d:
            message_mix["client"] += cnt
        elif "outbound" in d:
            message_mix["assistant"] += cnt
        else:
            message_mix["system"] += cnt

    # Conversation volume (sum of all messages)
    conversation_volume = sum(message_mix.values())

    
    # -------------------------------------------------------
    # PERSONA BREAKDOWN — safe buckets
    # -------------------------------------------------------
    try:
        persona_rows = (
            db.query(SimLead.persona, func.count(SimLead.id))
            .group_by(SimLead.persona)
            .all()
        )
        persona_map = {p or "unknown": int(c) for p, c in persona_rows}
    except Exception:
        persona_map = {}

    # Guarantee buckets for frontend
    persona_breakdown_safe = {
        "buyer": persona_map.get("buyer", 0),
        "seller": persona_map.get("seller", 0),
        "investor": persona_map.get("investor", 0),
        "renter": persona_map.get("renter", 0),
        "unknown": persona_map.get("unknown", 0),
    }

    # -------------------------------------------------------
    # RECENT ACTIVITY
    # (Hybrid: last 24h or fallback)
    # -------------------------------------------------------
    recent = []

    # 1) Bursts
    for b in db.query(SimBurst).order_by(getattr(SimBurst, 'created_at', SimBurst.id).desc()).limit(50).all():
        recent.append({
            "ts": getattr(b, 'created_at', None),
            "kind": "burst",
            "label": f"Burst created {b.leads_created} leads, {b.events_generated} events"
        })

    # 2) Messages
    try:
        for m in db.query(SimMessageLog).order_by(getattr(SimMessageLog, 'created_at', SimMessageLog.id).desc()).limit(50).all():
            recent.append({
                "ts": getattr(m, 'created_at', None),
                "kind": "message",
                "label": f"{m.role}: {m.summary or '(no text)'}"
            })
    except Exception:
        pass

    # 3) Lead updates
    for lead in db.query(SimLead).order_by(getattr(SimLead, 'updated_at', SimLead.id).desc()).limit(50).all():
        recent.append({
            "ts": getattr(lead, 'updated_at', None),
            "kind": "lead",
            "label": f"Lead {lead.id} status → {lead.status}"
        })

    # Hybrid filtering
    import datetime
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
    last_24h = [e for e in recent if e["ts"] and e["ts"] >= cutoff]

    if last_24h:
        recent_final = sorted(last_24h, key=lambda x: x["ts"], reverse=True)[:25]
    else:
        recent_final = sorted(recent, key=lambda x: x["ts"], reverse=True)[:25]

    # -------------------------------------------------------
    # FORECAST ACCURACY (preserved from your implementation)
    # -------------------------------------------------------
    won = db.query(SimLead).filter(SimLead.status == "won").all()
    deviations = [abs(float(lead.score) - 85.0) for lead in won]
    forecast_accuracy_deviation = sum(deviations) / len(deviations) if deviations else 0.0

# -------------------------------------------------------
# RETURN MERGED INTELLIGENCE
# -------------------------------------------------------

    return {
        "status": "ok",
        "companies_seeded": companies_count,
        "lead_count": leads_count,

        # previously returned keys (kept intact)
        "deal_distribution": deal_distribution,
        "scoring_distribution": scoring_buckets,
        "event_throughput": {
            "bursts": burst_count,
            "leads_created_in_bursts": int(leads_from_bursts or 0),
            "events_generated": int(events_generated or 0),
        },
        "forecast_accuracy_deviation": round(float(forecast_accuracy_deviation), 2),
        "simulation_bursts_processed": burst_count,

        # NEW INTELLIGENCE
        "burst_runs": burst_count,
        "conversation_volume": conversation_volume,
        "client_messages": message_mix["client"],
        "assistant_messages": message_mix["assistant"],
        "system_messages": message_mix["system"],
        "persona_breakdown": persona_breakdown_safe,
        "pipeline_breakdown": deal_distribution,
        "recent_activity": recent_final,
    }
