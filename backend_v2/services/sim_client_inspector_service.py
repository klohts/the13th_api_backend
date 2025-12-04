import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger("the13th.sim_client_inspector_service")


def parse_dt(value):
    """Normalize DB timestamp values to datetime objects."""
    if isinstance(value, datetime):
        return value
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        try:
            # fallback: common SQLite format
            return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        except Exception:
            return None


# ---------------------------------------------------------------------------
# Utility: convert raw SQL row to dict
# ---------------------------------------------------------------------------
def row_to_dict(row):
    """Convert SQLAlchemy Row object to dict safely (SQLAlchemy 2.0)."""
    try:
        return dict(row._mapping)
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# SEGMENTATION LOGIC
# ---------------------------------------------------------------------------
STAGE_NEW = {"New", "Uncontacted", "Inquiry"}
STAGE_NURTURE = {"Nurturing", "Long-term", "Cold"}
STAGE_PIPELINE = {"Showing Scheduled", "Offer Sent", "Under Contract"}
STAGE_WON = {"Closed Won"}
STAGE_LOST = {"Closed Lost"}


# ---------------------------------------------------------------------------
# Fetch all companies + intelligence
# ---------------------------------------------------------------------------
def fetch_companies_with_intel(db: Session) -> List[Dict[str, Any]]:
    companies: List[Dict[str, Any]] = []

    company_rows = db.execute(
        text(
            """
            SELECT id, name, segment, region, agent_count,
                   monthly_target, is_active, created_at, updated_at
            FROM sim_client_companies
            ORDER BY name ASC
        """
        )
    ).fetchall()

    for row in company_rows:
        c = row_to_dict(row)
        cid = c["id"]

        # NOTE: include agent_id so we can map leads → agents
        leads = db.execute(
            text(
                """
                SELECT id,
                       company_id,
                       agent_id,
                       full_name,
                       email,
                       phone,
                       source,
                       stage,
                       score,
                       budget_min,
                       budget_max,
                       timeline,
                       city,
                       state,
                       created_at,
                       updated_at
                FROM sim_client_leads
                WHERE company_id = :cid
                ORDER BY updated_at DESC
            """
            ),
            {"cid": cid},
        ).fetchall()

        lead_dicts: List[Dict[str, Any]] = []
        for r in leads:
            d = row_to_dict(r)
            d["created_at"] = parse_dt(d.get("created_at"))
            d["updated_at"] = parse_dt(d.get("updated_at"))
            lead_dicts.append(d)

        # -------------------------------------------------------------------
        # SEGMENT LEADS
        # -------------------------------------------------------------------
        segments: Dict[str, List[Dict[str, Any]]] = {
            "new": [],
            "nurturing": [],
            "pipeline": [],
            "won": [],
            "lost": [],
        }

        for lead in lead_dicts:
            st = lead["stage"]
            if st in STAGE_NEW:
                segments["new"].append(lead)
            elif st in STAGE_NURTURE:
                segments["nurturing"].append(lead)
            elif st in STAGE_PIPELINE:
                segments["pipeline"].append(lead)
            elif st in STAGE_WON:
                segments["won"].append(lead)
            elif st in STAGE_LOST:
                segments["lost"].append(lead)
            else:
                segments["nurturing"].append(lead)

        # -------------------------------------------------------------------
        # COMPANY METRICS
        # -------------------------------------------------------------------
        lead_count = len(lead_dicts)
        high_intent = sum(1 for l in lead_dicts if (l.get("score") or 0) >= 80)
        won_deals = len(segments["won"])
        lost_deals = len(segments["lost"])
        active_deals = len(segments["pipeline"])
        avg_score = (
            round(
                sum((l.get("score") or 0) for l in lead_dicts) / lead_count,
                2,
            )
            if lead_count > 0
            else 0.0
        )

        latest_update_dt = (
            max((l.get("updated_at") for l in lead_dicts if l.get("updated_at")), default=None)
            if lead_dicts
            else None
        )
        latest_update = latest_update_dt or "—"

        # -------------------------------------------------------------------
        # TREND & ALERTS
        # -------------------------------------------------------------------
        now = datetime.utcnow()
        dt7 = now - timedelta(days=7)
        dt30 = now - timedelta(days=30)

        new_7d = sum(
            1
            for l in lead_dicts
            if l.get("created_at") and l["created_at"] >= dt7
        )
        new_30d = sum(
            1
            for l in lead_dicts
            if l.get("created_at") and l["created_at"] >= dt30
        )
        active_7d = sum(
            1
            for l in lead_dicts
            if l.get("updated_at") and l["updated_at"] >= dt7
        )

        trend_label = "Flat"
        trend_delta = (active_7d / lead_count * 100) if lead_count else 0

        if trend_delta > 10:
            trend_label = "Upward"
        elif trend_delta < 3:
            trend_label = "Downward"

        # Alerts
        alerts: List[str] = []
        if len(segments["pipeline"]) == 0 and lead_count > 0:
            alerts.append("No active deals in pipeline.")
        if high_intent > 15 and active_deals < 3:
            alerts.append("High-intent leads not converting.")

        # Next Actions
        next_actions: List[str] = []
        if high_intent > 5:
            next_actions.append("Prioritize contacting high-intent leads today.")
        if active_deals > 10:
            next_actions.append("Review pipeline for bottlenecks.")
        if lost_deals > won_deals:
            next_actions.append("Review recent Closed Lost reasons.")

        # -------------------------------------------------------------------
        # AGENTS
        # -------------------------------------------------------------------
        agents_raw = db.execute(
            text(
                """
                SELECT id,
                       full_name,
                       role,
                       company_id,
                       created_at,
                       updated_at
                FROM sim_client_agents
                WHERE company_id = :cid
            """
            ),
            {"cid": cid},
        ).fetchall()

        agents: List[Dict[str, Any]] = []
        for arow in agents_raw:
            a = row_to_dict(arow)
            aid = a["id"]

            # Attach leads belonging to this agent
            agent_leads = [
                l for l in lead_dicts if l.get("agent_id") == aid
            ]

            lead_count_agent = len(agent_leads)
            active_deals_agent = sum(
                1 for l in agent_leads if l["stage"] in STAGE_PIPELINE
            )
            won_deals_agent = sum(
                1 for l in agent_leads if l["stage"] in STAGE_WON
            )
            lost_deals_agent = sum(
                1 for l in agent_leads if l["stage"] in STAGE_LOST
            )
            avg_score_agent = (
                round(
                    sum((l.get("score") or 0) for l in agent_leads)
                    / lead_count_agent,
                    2,
                )
                if lead_count_agent
                else 0.0
            )
            last_activity_dt = max(
                (l.get("updated_at") for l in agent_leads if l.get("updated_at")),
                default=None,
            )
            last_activity = last_activity_dt or "—"

            try:
                win_rate_agent = (
                    (won_deals_agent / max(1, won_deals_agent + lost_deals_agent))
                    * 100
                )
            except ZeroDivisionError:
                win_rate_agent = 0.0

            a.update(
                {
                    "lead_count": lead_count_agent,
                    "active_deals": active_deals_agent,
                    "won_deals": won_deals_agent,
                    "lost_deals": lost_deals_agent,
                    "avg_score": avg_score_agent,
                    "last_activity": last_activity,
                    "win_rate": win_rate_agent,
                }
            )
            agents.append(a)

        # -------------------------------------------------------------------
        # FINAL COMPANY OBJECT
        # -------------------------------------------------------------------
        c.update(
            {
                "lead_count": lead_count,
                "high_intent": high_intent,
                "won_deals": won_deals,
                "lost_deals": lost_deals,
                "active_deals": active_deals,
                "avg_score": avg_score,
                "latest_update": latest_update,
                "trend": {
                    "new_leads_7d": new_7d,
                    "new_leads_30d": new_30d,
                    "active_7d": active_7d,
                    "trend_label": trend_label,
                    "trend_delta": trend_delta,
                },
                "alerts": alerts,
                "next_actions": next_actions,
                "agents": agents,
                "segments": segments,
            }
        )

        companies.append(c)

    return companies


# ---------------------------------------------------------------------------
# GLOBAL OVERVIEW + PORTFOLIO INTELLIGENCE
# ---------------------------------------------------------------------------
def fetch_global_overview(db: Session) -> Dict[str, Any]:
    now = datetime.utcnow()
    dt7 = now - timedelta(days=7)
    dt30 = now - timedelta(days=30)

    total_leads = db.execute(
        text("SELECT COUNT(*) FROM sim_client_leads")
    ).scalar()

    active_deals = db.execute(
        text(
            """
            SELECT COUNT(*)
            FROM sim_client_leads
            WHERE stage IN ('Showing Scheduled', 'Offer Sent', 'Under Contract')
        """
        )
    ).scalar()

    won_deals = db.execute(
        text(
            "SELECT COUNT(*) FROM sim_client_leads WHERE stage = 'Closed Won'"
        )
    ).scalar()

    new_leads_7d = db.execute(
        text(
            "SELECT COUNT(*) FROM sim_client_leads WHERE created_at >= :dt"
        ),
        {"dt": dt7},
    ).scalar()

    new_leads_30d = db.execute(
        text(
            "SELECT COUNT(*) FROM sim_client_leads WHERE created_at >= :dt"
        ),
        {"dt": dt30},
    ).scalar()

    forecast_accuracy = 60 + (active_deals % 25)

    trend_delta = (active_deals / max(1, total_leads)) * 100
    trend_label = (
        "Upward"
        if trend_delta > 10
        else "Downward"
        if trend_delta < 3
        else "Flat"
    )

    return {
        "total_leads": total_leads,
        "active_deals": active_deals,
        "won_deals": won_deals,
        "new_leads_7d": new_leads_7d,
        "new_leads_30d": new_leads_30d,
        "active_7d": total_leads // 7,
        "forecast_accuracy": forecast_accuracy,
        "trend_label": trend_label,
        "trend_delta": trend_delta,
    }


def fetch_portfolio_intelligence(
    companies: List[Dict[str, Any]]
) -> Dict[str, Any]:
    if not companies:
        return {}

    best_opportunity = max(
        companies, key=lambda c: c.get("high_intent", 0)
    )
    most_at_risk = max(
        companies, key=lambda c: len(c.get("alerts", []))
    )
    top_conversion = max(
        companies, key=lambda c: c.get("won_deals", 0)
    )
    largest_pipeline = max(
        companies,
        key=lambda c: len(c.get("segments", {}).get("pipeline", [])),
    )

    return {
        "best_opportunity": best_opportunity,
        "most_at_risk": most_at_risk,
        "top_conversion": top_conversion,
        "largest_pipeline": largest_pipeline,
    }


# ---------------------------------------------------------------------------
# AGENT OVERVIEW (SUMMARY)
# ---------------------------------------------------------------------------
def fetch_agent_overview(db: Session, agent_id: int) -> Dict[str, Any]:
    row = db.execute(
        text(
            """
            SELECT id, full_name, role, company_id, created_at, updated_at
            FROM sim_client_agents
            WHERE id = :aid
            """
        ),
        {"aid": agent_id},
    ).fetchone()

    if not row:
        return {"error": "Agent not found"}

    agent = row_to_dict(row)

    lead_rows = db.execute(
        text(
            """
            SELECT id, full_name, stage, score, updated_at
            FROM sim_client_leads
            WHERE agent_id = :aid
            """
        ),
        {"aid": agent_id},
    ).fetchall()

    leads = []
    for lr in lead_rows:
        d = row_to_dict(lr)
        d["updated_at"] = parse_dt(d.get("updated_at"))
        leads.append(d)

    lead_count = len(leads)
    won = sum(1 for l in leads if l["stage"] in STAGE_WON)
    lost = sum(1 for l in leads if l["stage"] in STAGE_LOST)
    active = sum(1 for l in leads if l["stage"] in STAGE_PIPELINE)

    avg_score = (
        round(sum((l.get("score") or 0) for l in leads) / lead_count, 2)
        if lead_count
        else 0.0
    )

    last_activity_dt = max(
        (l.get("updated_at") for l in leads if l.get("updated_at")),
        default=None,
    )

    try:
        win_rate = (won / max(1, won + lost)) * 100
    except ZeroDivisionError:
        win_rate = 0.0

    return {
        "agent": agent,
        "metrics": {
            "lead_count": lead_count,
            "active_deals": active,
            "won_deals": won,
            "lost_deals": lost,
            "avg_score": avg_score,
            "win_rate": win_rate,
            "last_activity": last_activity_dt or "—",
        },
    }


# ---------------------------------------------------------------------------
# AGENT DRILLDOWN (EVENT LOG)
# ---------------------------------------------------------------------------
def fetch_agent_drilldown(db: Session, agent_id: int) -> Dict[str, Any]:
    rows = db.execute(
        text(
            """
            SELECT id,
                   lead_id,
                   event_type,
                   score_delta,
                   notes,
                   created_at
            FROM sim_client_events
            WHERE agent_id = :aid
            ORDER BY created_at DESC
            """
        ),
        {"aid": agent_id},
    ).fetchall()

    events = []
    for r in rows:
        d = row_to_dict(r)
        d["created_at"] = parse_dt(d.get("created_at"))
        events.append(d)

    return {
        "agent_id": agent_id,
        "events": events,
    }


# ---------------------------------------------------------------------------
# LEAD DRILLDOWN (EVENTS FOR ONE LEAD)
# ---------------------------------------------------------------------------
def fetch_lead_drilldown(db: Session, lead_id: int) -> Dict[str, Any]:
    lead_row = db.execute(
        text(
            """
            SELECT id, full_name, stage, score, updated_at
            FROM sim_client_leads
            WHERE id = :lid
            """
        ),
        {"lid": lead_id},
    ).fetchone()

    if not lead_row:
        return {"error": "Lead not found"}

    lead = row_to_dict(lead_row)

    event_rows = db.execute(
        text(
            """
            SELECT id,
                   agent_id,
                   event_type,
                   score_delta,
                   notes,
                   created_at
            FROM sim_client_events
            WHERE lead_id = :lid
            ORDER BY created_at DESC
            """
        ),
        {"lid": lead_id},
    ).fetchall()

    events = []
    for r in event_rows:
        d = row_to_dict(r)
        d["created_at"] = parse_dt(d.get("created_at"))
        events.append(d)

    return {
        "lead": lead,
        "events": events,
    }

