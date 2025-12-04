# backend_v2/routers/client_experience_sim.py

from __future__ import annotations

import json
import logging
from math import ceil
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from backend_v2.database import get_db
from backend_v2.services.auth_service import authenticated_admin
from backend_v2.services.render import render_template
from backend_v2.sim_client_engine import run_client_simulation, get_available_personas
from backend_v2.services.client_experience_insights import (
    build_revealable_insights,
    build_comparison_differences,
)
from backend_v2.services.client_experience_metrics import JourneyEvent

logger = logging.getLogger("the13th.client_experience_sim")

router = APIRouter(
    prefix="/admin/client-experience",
    tags=["Client Experience Simulation"],
)

# ---------------------------------------------------------------------------
# Engine wrapper (Option 3: support multiple signatures)
# ---------------------------------------------------------------------------


def _try_engine_call(
    persona: str,
    days: int,
    db: Optional[Session] = None,
) -> Dict[str, Any]:
    """
    Try multiple calling conventions for run_client_simulation in order:

    1. days=..., persona_key=..., db=db
    2. days=..., persona_key=...
    3. persona, days, db
    4. persona, days

    Returns {} on complete failure; logs the exception.
    """
    # 1) Newest: keyword-based with db
    try:
        if db is not None:
            return run_client_simulation(days=days, persona_key=persona, db=db)  # type: ignore[arg-type]
    except TypeError:
        logger.debug("run_client_simulation(days, persona_key, db) signature not supported")

    # 2) Keyword-based without db
    try:
        return run_client_simulation(days=days, persona_key=persona)  # type: ignore[arg-type]
    except TypeError:
        logger.debug("run_client_simulation(days, persona_key) signature not supported")

    # 3) Positional with db
    try:
        if db is not None:
            return run_client_simulation(persona, days, db)  # type: ignore[arg-type]
    except TypeError:
        logger.debug("run_client_simulation(persona, days, db) signature not supported")

    # 4) Positional without db
    try:
        return run_client_simulation(persona, days)  # type: ignore[arg-type]
    except TypeError as exc:
        logger.exception("run_client_simulation() incompatible with all tried signatures: %s", exc)

    return {}


def run_full_client_simulation(
    persona: str,
    days: int,
    db: Optional[Session] = None,
) -> Dict[str, Any]:
    """
    Unified entrypoint used by the router. Ensures we always return a dict
    and never propagate engine exceptions into the view layer.
    """
    try:
        sim = _try_engine_call(persona=persona, days=days, db=db)
        if not isinstance(sim, dict):
            logger.warning("Simulation engine returned non-dict payload, normalising…")
            return {"error": "invalid_sim_output", "raw": sim}
        return sim
    except Exception as exc:  # pragma: no cover
        logger.exception("Client experience simulation failed: %s", exc)
        return {
            "error": "engine_failure",
            "exception": str(exc),
            "persona": persona,
            "days": days,
        }


# ---------------------------------------------------------------------------
# Summary builder for the AI Agent Summary panel
# ---------------------------------------------------------------------------


def compute_client_experience_summary(simulation: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Cinematic KPI summary for THE13TH Client Experience page.

    Computes:
    - conversion_likelihood (%)
    - dropoff_risk (%)
    - engagement_intensity (0–100)
    - pipeline_depth_label (friendly stage label)
    """

    if not simulation or not isinstance(simulation, dict):
        return {
            "conversion_likelihood": "—",
            "dropoff_risk": "—",
            "engagement_intensity": "—",
            "pipeline_depth_label": "—",
        }

    # Extract events
    events = simulation.get("events", [])
    if not isinstance(events, list) or not events:
        return {
            "conversion_likelihood": "—",
            "dropoff_risk": "—",
            "engagement_intensity": "—",
            "pipeline_depth_label": "—",
        }

    # ---- PIPELINE DEPTH ----
    final_stage = simulation.get("final_stage", "Unknown")
    pipeline_depth_label = final_stage

    # ---- ENGAGEMENT INTENSITY ----
    stats = simulation.get("stats", {})
    client_msgs = stats.get("client_messages", 0)
    assistant_msgs = stats.get("assistant_messages", 0)

    # Scale by density per day
    days = simulation.get("days", 30)
    total_msgs = client_msgs + assistant_msgs
    intensity_raw = (total_msgs / max(days, 1)) * 10.0  # 10 msgs/day = 100 score
    engagement_intensity = min(100, round(intensity_raw, 1))

    # ---- CONVERSION / DROP-OFF ----
    converted = simulation.get("converted", False)

    if converted:
        conversion_likelihood = 95
        dropoff_risk = 5
    else:
        # Heuristic based on final stage & intensity
        stage = str(final_stage).lower()
        if "lost" in stage:
            conversion_likelihood = 15
            dropoff_risk = 70
        elif "warm" in stage or "active" in stage:
            conversion_likelihood = 55
            dropoff_risk = 30
        elif "hot" in stage or "high intent" in stage:
            conversion_likelihood = 75
            dropoff_risk = 15
        else:
            conversion_likelihood = 40
            dropoff_risk = 40

    return {
        "conversion_likelihood": conversion_likelihood,
        "dropoff_risk": dropoff_risk,
        "engagement_intensity": engagement_intensity,
        "pipeline_depth_label": pipeline_depth_label,
    }



# ---------------------------------------------------------------------------
# Narrative & decision tree
# ---------------------------------------------------------------------------


def build_narrative_summary(summary: Dict[str, Any]) -> str:
    lp = summary.get("lead_profile", {})
    ap = summary.get("assistant_pattern", {})
    jr = summary.get("journey", {})
    mt = summary.get("metrics", {})

    lead_label = lp.get("label", "the lead")
    rhythm = lp.get("rhythm", "")
    assist_label = ap.get("label", "the assistant")
    assist_summary = ap.get("summary", "")

    start_stage = jr.get("start_stage", "—")
    end_stage = jr.get("end_stage", "—")
    path = jr.get("path", "")
    days = jr.get("days", 0)

    convert_prob = mt.get("convert_prob", 0)
    drop_prob = mt.get("dropoff_prob", 0)
    intensity = mt.get("intensity_score", 0)

    narrative = (
        f"This simulated client exhibited **{lead_label.lower()}** behaviour over a "
        f"**{days}-day** journey. Their engagement rhythm can be described as: "
        f"_{rhythm}_.\n\n"
        f"The assistant demonstrated **{assist_label.lower()}**, with behaviour summarised as: "
        f"_{assist_summary}_\n\n"
    )

    if path:
        narrative += (
            f"The journey progressed through the stages: **{path}**, "
            f"starting from **{start_stage}** and ending in **{end_stage}**.\n\n"
        )

    narrative += (
        f"Engagement intensity for this lead was estimated at **{intensity}%**, "
        f"reflecting the density of interactions.\n\n"
        f"Based on the pattern and journey outcome, the client shows an approximate "
        f"**{convert_prob}% likelihood of conversion**, with a **{drop_prob}% probability of drop-off**."
    )

    return narrative


def build_decision_tree(simulation: Optional[Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    Convert simulation events into an interpretable reasoning chain.
    Returns a list of dicts:
      { "day": ..., "explanation": ... }
    """
    if not simulation or "events" not in simulation:
        return []

    events = simulation.get("events", [])
    decisions: List[Dict[str, str]] = []

    for ev_raw in events:
        if not isinstance(ev_raw, dict):
            continue

        ev: Dict[str, Any] = ev_raw
        day = ev.get("day") or ev.get("day_index") or 0
        sender = (ev.get("actor") or ev.get("sender") or ev.get("from") or "").lower()
        stage_after = ev.get("stage_after") or ev.get("stage") or "—"
        sentiment = ev.get("sentiment") or ev.get("tone") or ""
        action = ev.get("action") or ev.get("event_type") or ""

        parts: List[str] = []

        if "client" in sender or "lead" in sender or "buyer" in sender:
            parts.append("Client activity detected.")
        elif "assistant" in sender or "ai" in sender:
            parts.append("Assistant responded in this step.")

        if sentiment:
            parts.append(f"Sentiment registered as **{sentiment}**.")

        if action:
            parts.append(f"Key action/event: **{action}**.")

        parts.append(f"Pipeline stage is now **{stage_after}**.")

        explanation = " ".join(parts)
        decisions.append(
            {
                "day": str(day),
                "explanation": explanation,
            }
        )

    return decisions


# ---------------------------------------------------------------------------
# KPI strip builder (for partials/client_experience_kpi_strip.html)
# ---------------------------------------------------------------------------


def _extract_delay_values(events: List[Dict[str, Any]]) -> List[float]:
    delays: List[float] = []
    candidate_keys = [
        "reply_delay_hours",
        "delay_hours",
        "gap_hours",
        "response_gap_hours",
    ]

    for ev_raw in events:
        if not isinstance(ev_raw, dict):
            continue
        ev: Dict[str, Any] = ev_raw

        for key in candidate_keys:
            value = ev.get(key)
            if value is None:
                continue
            try:
                delays.append(float(value))
                break
            except (TypeError, ValueError):
                continue

    return delays


def build_kpi_strip(
    simulation: Optional[Dict[str, Any]],
    summary: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Build the lightweight KPI dict used by the mini-strip partial:

      kpi_strip = {
        "avg_response_delay_label": "2.3h",
        "avg_response_delay_hours": 2.3,
        "longest_gap_label": "18h",
        "longest_gap_hours": 18.0,
        "intensity_score_label": "High",
        "intensity_score": 82.1,
        "total_touchpoints": 23,
      }
    """
    k: Dict[str, Any] = {
        "avg_response_delay_label": "—",
        "avg_response_delay_hours": None,
        "longest_gap_label": "—",
        "longest_gap_hours": None,
        "intensity_score_label": "—",
        "intensity_score": None,
        "total_touchpoints": 0,
    }

    if not simulation or not isinstance(simulation, dict):
        return k

    events = simulation.get("events") or []
    if isinstance(events, list):
        k["total_touchpoints"] = len(events)

    delays = _extract_delay_values(events if isinstance(events, list) else [])
    if delays:
        avg_delay = sum(delays) / max(len(delays), 1)
        max_delay = max(delays)
        k["avg_response_delay_hours"] = round(avg_delay, 1)
        k["avg_response_delay_label"] = f"{round(avg_delay, 1)}h"
        k["longest_gap_hours"] = round(max_delay, 1)
        k["longest_gap_label"] = f"{round(max_delay, 1)}h"

    metrics = (summary or {}).get("metrics", {}) if isinstance(summary, dict) else {}
    intensity = metrics.get("intensity_score")
    if intensity is not None:
        try:
            intensity_val = float(intensity)
        except (TypeError, ValueError):
            intensity_val = None
    else:
        intensity_val = None

    if intensity_val is not None:
        k["intensity_score"] = intensity_val
        if intensity_val >= 80:
            k["intensity_score_label"] = "Very high"
        elif intensity_val >= 60:
            k["intensity_score_label"] = "High"
        elif intensity_val >= 40:
            k["intensity_score_label"] = "Moderate"
        else:
            k["intensity_score_label"] = "Low"

    return k


def convert_sim_events_to_timeline(simulation: Dict[str, Any]) -> List[Dict[str, Any]]:
    events = simulation.get("events", [])
    timeline = []

    for ev in events:
        day = ev.get("day") or ev.get("day_index") or 0
        actor = (ev.get("actor") or "").lower()

        if "client" in actor:
            event_type = "Client message"
        elif "assistant" in actor or "ai" in actor:
            event_type = "Assistant reply"
        else:
            event_type = "System update"

        timeline.append({
            "day": day,
            "day_label": str(day),
            "event_type_label": event_type,
            "headline": ev.get("message") or "Message exchanged",
            "meta": ev.get("time_label") or "",
            "email": None,
        })

    return timeline





# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("", response_class=HTMLResponse)
def client_experience_page(
    request: Request,
    persona: str = Query("ghosting_lead"),
    days: int = Query(30, ge=1, le=90),
    db: Session = Depends(get_db),
    admin: Any = Depends(authenticated_admin),
) -> HTMLResponse:
    """
    Client Journey Simulation page.

    - Runs the full client simulation
    - Computes summary + graphs
    - Exposes timeline_events, journey_points, etc. directly
      to the Jinja template (no build_full_context indirection).
    """

    try:
        personas = get_available_personas()
    except Exception as exc:
        logger.exception("Error fetching personas: %s", exc)
        personas = []

    persona_keys = {p.get("key") for p in personas if isinstance(p, dict)} if personas else set()
    if persona_keys and persona not in persona_keys:
        persona = next(iter(persona_keys))

    # ----- RUN SIMULATION -----
    simulation: Dict[str, Any] = run_full_client_simulation(persona=persona, days=days, db=db)

    # ----- TIMELINE EVENTS -----
    timeline_events: List[Dict[str, Any]] = convert_sim_events_to_timeline(simulation) or []
    logger.info("ClientExperience: built %d timeline events", len(timeline_events))

    # ----- JOURNEY GRAPH POINTS -----
    stage_timeline: List[Dict[str, Any]] = simulation.get("graphs", {}).get("stage_timeline", []) or []
    journey_points: List[Dict[str, Any]] = [
        {"x": item.get("day"), "y": item.get("stage_index")}
        for item in stage_timeline
        if item.get("day") is not None and item.get("stage_index") is not None
    ]

    # ----- STAGE LABELS -----
    journey_stage_labels: List[str] = [item.get("stage", "") for item in stage_timeline]

    # ----- EMAIL THREADS -----
    email_threads: List[Dict[str, Any]] = []  # engine not generating these yet

    # ----- SUMMARY -----
    summary: Dict[str, Any] = compute_client_experience_summary(simulation)

    # ----- FINAL CONTEXT (DIRECT) -----
    context: Dict[str, Any] = {
        "request": request,  # required by Starlette / Jinja
        "persona": persona,
        "persona_label": simulation.get("persona_label", "Lead"),
        "simulation_days": simulation.get("days", days),
        "summary": summary,
        "timeline_events": timeline_events,
        "journey_points": journey_points,
        "journey_stage_labels": journey_stage_labels,
        "email_threads": email_threads,
    }

    # Optional: debug snapshot
    try:
        import json

        logger.debug(
            "ClientExperience context snapshot:\n%s",
            json.dumps(
                {
                    "persona": context.get("persona"),
                    "simulation_days": context.get("simulation_days"),
                    "timeline_events_len": len(timeline_events),
                    "journey_points_len": len(journey_points),
                },
                indent=2,
                default=str,
            ),
        )
    except Exception:
        logger.debug("ClientExperience: context logging skipped (serialization error)")

    return render_template("admin_sim_client_experience.html", context)


@router.get("/compare", response_class=HTMLResponse)
def client_experience_compare_page(
    request: Request,
    persona_a: str = Query("ghosting_lead"),
    persona_b: str = Query("slow_nurture"),
    days: int = Query(30, ge=1, le=90),
    db: Session = Depends(get_db),
    admin: Any = Depends(authenticated_admin),
) -> HTMLResponse:
    """
    THE13TH — Client Experience Comparison Mode

    Compare two personas:
      - Activity curve / stage progression (provided by engine graphs)
      - Conversion likelihood heuristics
      - Assistant workload / intensity
    """
    try:
        personas = get_available_personas()
    except Exception as exc:
        logger.exception("Error fetching personas: %s", exc)
        personas = []

    sim_a = run_full_client_simulation(persona=persona_a, days=days, db=db)
    sim_b = run_full_client_simulation(persona=persona_b, days=days, db=db)

    summary_a = compute_client_experience_summary(sim_a)
    summary_b = compute_client_experience_summary(sim_b)

    kpi_a = build_kpi_strip(sim_a, summary_a)
    kpi_b = build_kpi_strip(sim_b, summary_b)

    try:
        comparison_differences = build_comparison_differences(
            sim_a, sim_b, summary_a, summary_b
        )
    except Exception as exc:
        logger.exception("Error building comparison differences: %s", exc)
        comparison_differences = []

    context: Dict[str, Any] = {
        "request": request,
        "personas": personas,
        "persona_a": persona_a,
        "persona_b": persona_b,
        "days": days,
        "simulation_a": sim_a,
        "simulation_b": sim_b,
        "summary_a": summary_a,
        "summary_b": summary_b,
        "kpi_a": kpi_a,
        "kpi_b": kpi_b,
        "comparison_differences": comparison_differences,
    }

    return render_template(
    "admin_sim_client_experience.html",
    {
        "request": request,
        **context
    }
)

