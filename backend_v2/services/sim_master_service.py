from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

logger = logging.getLogger("the13th.sim_master.service")

try:  # Soft dependency on sim_lab_service
    from backend_v2.services.sim_lab_service import get_simulation_overview
except Exception:  # pragma: no cover - defensive only
    get_simulation_overview = None  # type: ignore[misc]


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except Exception:
        return default


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def build_sim_master_context(db: Session) -> Dict[str, Any]:
    """
    Build a robust context for the Simulation Master Dashboard.

    This function is intentionally defensive: if the underlying sim_lab_service
    changes shape, we fall back to sane defaults instead of breaking the UI.
    """
    raw_overview: Dict[str, Any] = {}
    try:
        if get_simulation_overview is not None:
            data = get_simulation_overview(db)  # type: ignore[call-arg]
            if isinstance(data, dict):
                raw_overview = data
            else:
                logger.warning(
                    "Unexpected type from get_simulation_overview: %s", type(data)
                )
        else:
            logger.warning("get_simulation_overview not available.")
    except Exception:
        logger.exception("Error while calling get_simulation_overview")
        raw_overview = {}

    # Company + lead counts --------------------------------------------------
    companies = raw_overview.get("companies") or raw_overview.get("company_stats") or []
    if not isinstance(companies, list):
        companies = []

    company_count = _safe_int(
        raw_overview.get("company_count")
        or raw_overview.get("companies_count")
        or len(companies)
    )

    total_leads = _safe_int(
        raw_overview.get("total_leads")
        or raw_overview.get("lead_count")
        or raw_overview.get("leads_total")
    )

    seeded_leads = _safe_int(
        raw_overview.get("seeded_leads")
        or raw_overview.get("simulated_leads")
        or total_leads
    )

    # Bursts / runs ---------------------------------------------------------
    bursts = raw_overview.get("bursts") or raw_overview.get("burst_runs") or []
    if not isinstance(bursts, list):
        bursts = []
    burst_runs = len(bursts)

    last_seeded_at: Optional[str] = None
    last_burst_at: Optional[str] = None

    try:
        if companies:
            # look for a 'seeded_at' field on companies if present
            timestamps = [
                c.get("seeded_at")
                for c in companies
                if isinstance(c, dict) and c.get("seeded_at")
            ]
            if timestamps:
                last_seeded_at = max(_safe_str(t) for t in timestamps)
    except Exception:
        logger.debug("Could not compute last_seeded_at", exc_info=True)

    try:
        timestamps = [
            b.get("ran_at") or b.get("created_at")
            for b in bursts
            if isinstance(b, dict) and (b.get("ran_at") or b.get("created_at"))
        ]
        if timestamps:
            last_burst_at = max(_safe_str(t) for t in timestamps)
    except Exception:
        logger.debug("Could not compute last_burst_at", exc_info=True)

    # Messages breakdown ----------------------------------------------------
    msg_stats = raw_overview.get("message_stats") or raw_overview.get("messages") or {}
    if not isinstance(msg_stats, dict):
        msg_stats = {}

    client_messages = _safe_int(
        msg_stats.get("client")
        or msg_stats.get("client_messages")
        or raw_overview.get("client_messages")
    )
    assistant_messages = _safe_int(
        msg_stats.get("assistant")
        or msg_stats.get("assistant_messages")
        or raw_overview.get("assistant_messages")
    )
    system_messages = _safe_int(
        msg_stats.get("system")
        or msg_stats.get("system_messages")
        or raw_overview.get("system_messages")
    )
    total_messages = client_messages + assistant_messages + system_messages

    # Persona distribution --------------------------------------------------
    persona_breakdown: List[Dict[str, Any]] = []
    pb_source = raw_overview.get("persona_breakdown") or raw_overview.get("personas")
    if isinstance(pb_source, list):
        for item in pb_source:
            if not isinstance(item, dict):
                continue
            persona_breakdown.append(
                {
                    "key": item.get("key") or item.get("id") or "",
                    "label": item.get("label") or item.get("name") or "Persona",
                    "leads": _safe_int(
                        item.get("lead_count")
                        or item.get("leads")
                        or item.get("count")
                    ),
                    "converted": _safe_int(
                        item.get("converted")
                        or item.get("wins")
                        or item.get("converted_count")
                    ),
                    "lost": _safe_int(
                        item.get("lost")
                        or item.get("losses")
                        or item.get("lost_count")
                    ),
                    "conversion_rate": _safe_int(
                        item.get("conversion_rate") or item.get("convert_pct")
                    ),
                }
            )

    # Recent activity / events ----------------------------------------------
    recent_activity: List[Dict[str, Any]] = []
    events_source = raw_overview.get("recent_events") or raw_overview.get("events")
    if isinstance(events_source, list):
        for ev in events_source[:20]:
            if not isinstance(ev, dict):
                continue
            recent_activity.append(
                {
                    "when": _safe_str(ev.get("when") or ev.get("created_at")),
                    "kind": _safe_str(ev.get("kind") or ev.get("type") or "event"),
                    "company": _safe_str(ev.get("company") or ev.get("tenant") or ""),
                    "summary": _safe_str(
                        ev.get("summary") or ev.get("description") or ""
                    ),
                }
            )

    overview = {
        "company_count": company_count,
        "total_leads": total_leads,
        "seeded_leads": seeded_leads,
        "burst_runs": burst_runs,
        "last_seeded_at": last_seeded_at,
        "last_burst_at": last_burst_at,
        "client_messages": client_messages,
        "assistant_messages": assistant_messages,
        "system_messages": system_messages,
        "total_messages": total_messages,
        "raw_overview": raw_overview,
    }

    return {
        "overview": overview,
        "persona_breakdown": persona_breakdown,
        "recent_activity": recent_activity,
        "generated_at": datetime.utcnow(),
    }
