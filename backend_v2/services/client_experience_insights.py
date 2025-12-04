from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger("the13th.client_experience_insights")


@dataclass
class InsightEvent:
    ts: datetime
    sender: str
    text: str
    stage_before: str
    stage_after: str
    day_index: int


def _parse_ts(ev: Dict[str, Any], base_dt: datetime, idx: int) -> datetime:
    """Parse or synthesise a timestamp for an event."""
    ts = ev.get("timestamp") or ev.get("ts")
    if isinstance(ts, datetime):
        return ts
    if isinstance(ts, str):
        try:
            return datetime.fromisoformat(ts)
        except Exception:
            pass

    raw_day = ev.get("day") or ev.get("day_index") or ev.get("d") or 0
    try:
        d = int(raw_day)
    except Exception:
        d = 0
    return base_dt + timedelta(days=d, minutes=idx * 10)


def _normalise_events(simulation: Optional[Dict[str, Any]]) -> List[InsightEvent]:
    if not simulation or "events" not in simulation:
        return []

    base_dt = datetime.utcnow()
    events: List[InsightEvent] = []

    for idx, ev in enumerate(simulation.get("events") or []):
        if not isinstance(ev, dict):
            continue

        ts = _parse_ts(ev, base_dt=base_dt, idx=idx)
        sender = (ev.get("actor") or ev.get("sender") or ev.get("from") or "").lower()
        text = (ev.get("text") or ev.get("message") or "").strip()
        stage_before = str(ev.get("stage_before") or ev.get("stage") or "")
        stage_after = str(ev.get("stage_after") or stage_before)
        raw_day = ev.get("day") or ev.get("day_index") or ev.get("d") or 0
        try:
            day_index = int(raw_day)
        except Exception:
            day_index = 0

        events.append(
            InsightEvent(
                ts=ts,
                sender=sender,
                text=text,
                stage_before=stage_before,
                stage_after=stage_after,
                day_index=day_index,
            )
        )

    events.sort(key=lambda e: e.ts)
    return events


def _compute_gap_stats(events: List[InsightEvent]) -> Dict[str, Optional[float]]:
    if len(events) < 2:
        return {"avg_gap_h": None, "longest_gap_h": None}

    gaps: List[float] = []
    longest = 0.0

    for prev, curr in zip(events[:-1], events[1:]):
        delta = (curr.ts - prev.ts).total_seconds()
        if delta < 0:
            continue
        hours = delta / 3600.0
        gaps.append(hours)
        if hours > longest:
            longest = hours

    if not gaps:
        return {"avg_gap_h": None, "longest_gap_h": None}

    avg_gap = sum(gaps) / len(gaps)
    return {"avg_gap_h": avg_gap, "longest_gap_h": longest or None}


def _format_hours(h: Optional[float]) -> str:
    if h is None:
        return "—"
    if h < 1:
        return f"{int(h * 60)} min"
    if h < 24:
        return f"{h:.1f} h"
    days = h / 24
    return f"{days:.1f} days"


def build_revealable_insights(
    simulation: Optional[Dict[str, Any]],
    summary: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:
    """
    Build three revealable insight blocks:

    - why: Why this lead converted / stalled
    - hesitations: Key hesitations detected
    - timing: Optimal follow-up timing window
    """
    insights = {
        "why": {
            "title": "Why this lead converted",
            "subtitle": "A quick explanation of what likely drove this outcome.",
            "bullets": [
                "Run a simulation to generate a full explanation of this journey."
            ],
        },
        "hesitations": {
            "title": "Key hesitations detected",
            "subtitle": "Moments where the client showed friction or uncertainty.",
            "bullets": [
                "No strong hesitations detected yet. Most messages were neutral or positive."
            ],
        },
        "timing": {
            "title": "Optimal follow-up timing window",
            "subtitle": "How tight your follow-up should be to stay in the conversion zone.",
            "bullets": [
                "Run a simulation to see recommended follow-up timing for this persona."
            ],
        },
    }

    events = _normalise_events(simulation)
    if not events:
        return insights

    journey = summary.get("journey", {})
    metrics = summary.get("metrics", {})

    end_stage = str(journey.get("end_stage", "")).lower()
    path = str(journey.get("path", ""))
    days = journey.get("days", 0)
    intensity = metrics.get("intensity_score", 0)
    convert_prob = metrics.get("convert_prob", 0)
    drop_prob = metrics.get("dropoff_prob", 0)

    gap_stats = _compute_gap_stats(events)
    avg_gap_h = gap_stats["avg_gap_h"]
    longest_gap_h = gap_stats["longest_gap_h"]

    # WHY
    client_msgs = sum(1 for e in events if e.sender in {"lead", "client", "buyer", "prospect"})
    assistant_msgs = sum(1 for e in events if e.sender in {"assistant", "agent", "ai", "system"})
    active_days = len({e.day_index for e in events})

    converted = ("convert" in end_stage) or ("won" in end_stage)

    if converted:
        title = "Why this lead converted"
        bullets = [
            f"Strong engagement: {client_msgs} client messages over {active_days or days} active day(s).",
            f"Consistent follow-up: {assistant_msgs} assistant messages kept the conversation moving.",
            f"Pipeline journey: {path or 'steady progression through the pipeline.'}",
            f"Modelled conversion likelihood: {convert_prob:.0f}% with a drop-off risk of {drop_prob:.0f}%.",
        ]
        if intensity >= 70:
            bullets.append("High engagement intensity score — this lead behaved like a strong-fit buyer.")
        else:
            bullets.append("Moderate engagement intensity — conversion driven more by follow-up consistency than volume.")
    else:
        title = "Why this lead did not convert (yet)"
        bullets = [
            f"Engagement volume: {client_msgs} client messages across {active_days or days} active day(s).",
            "Stage progression stalled before reaching a committed stage.",
        ]
        if longest_gap_h and longest_gap_h > 48:
            bullets.append("Long silent gaps between touchpoints likely cooled the opportunity.")
        if intensity < 40:
            bullets.append("Low–medium engagement intensity — this persona requires a tighter follow-up rhythm.")
        bullets.append("Consider a targeted re-engagement sequence focused on objections and next steps.")

    insights["why"]["title"] = title
    insights["why"]["bullets"] = bullets

    # HESITATIONS
    hesitation_keywords = [
        "not sure",
        "think about",
        "later",
        "maybe",
        "too expensive",
        "price",
        "budget",
        "cost",
        "busy",
        "no time",
        "overwhelmed",
    ]

    hesitation_points: List[str] = []
    for e in events:
        if e.sender not in {"lead", "client", "buyer", "prospect"}:
            continue
        text_lower = e.text.lower()
        for kw in hesitation_keywords:
            if kw in text_lower:
                hesitation_points.append(
                    f"Day {e.day_index}: client raised a '{kw}'-style concern."
                )
                break

    if hesitation_points:
        deduped: List[str] = []
        for h in hesitation_points:
            if h not in deduped:
                deduped.append(h)
        insights["hesitations"]["bullets"] = deduped[:5]
    else:
        insights["hesitations"]["bullets"] = [
            "No strong objection phrases detected in this journey.",
            "Most client language was either neutral or positively oriented.",
        ]

    # TIMING
    timing_bullets: List[str] = []

    if avg_gap_h is not None:
        timing_bullets.append(
            f"Typical gap between touchpoints in this simulation: {_format_hours(avg_gap_h)}."
        )
    if longest_gap_h is not None:
        timing_bullets.append(
            f"Longest silence in this journey: {_format_hours(longest_gap_h)}."
        )

    if intensity >= 70:
        timing_bullets.append(
            "This persona responds well to a tight cadence — aim to follow up within 12–24 hours after each client message."
        )
    elif intensity >= 40:
        timing_bullets.append(
            "Balanced cadence works here — following up within 24–48 hours keeps the lead warm without overwhelming them."
        )
    else:
        timing_bullets.append(
            "Engagement is fragile — when the client does respond, make sure your follow-up lands within 24 hours."
        )

    insights["timing"]["bullets"] = timing_bullets

    return insights


# ---------------------------------------------------------------------------
# COMPARISON DIFFERENCE ENGINE
# ---------------------------------------------------------------------------
def build_comparison_differences(
    sim_a: Optional[Dict[str, Any]],
    summary_a: Dict[str, Any],
    sim_b: Optional[Dict[str, Any]],
    summary_b: Dict[str, Any],
    label_a: str,
    label_b: str,
) -> Dict[str, Any]:
    """
    Build a unified comparison narrative between two personas.
    Returns:
      {
        "title": ...,
        "subtitle": ...,
        "bullets": [...],
      }
    """
    events_a = _normalise_events(sim_a)
    events_b = _normalise_events(sim_b)

    journey_a = summary_a.get("journey", {})
    metrics_a = summary_a.get("metrics", {})

    journey_b = summary_b.get("journey", {})
    metrics_b = summary_b.get("metrics", {})

    # Message volumes
    ca = sum(1 for e in events_a if e.sender in {"lead", "client", "buyer", "prospect"})
    aa = sum(1 for e in events_a if e.sender in {"assistant", "agent", "ai", "system"})

    cb = sum(1 for e in events_b if e.sender in {"lead", "client", "buyer", "prospect"})
    ab = sum(1 for e in events_b if e.sender in {"assistant", "agent", "ai", "system"})

    # Intensity + probabilities
    ia = metrics_a.get("intensity_score", 0)
    ib = metrics_b.get("intensity_score", 0)
    pa = metrics_a.get("convert_prob", 0)
    pb = metrics_b.get("convert_prob", 0)

    # Stages
    end_a = journey_a.get("end_stage", "")
    end_b = journey_b.get("end_stage", "")
    path_a = journey_a.get("path", "")
    path_b = journey_b.get("path", "")

    # Gaps
    gaps_a = _compute_gap_stats(events_a)
    gaps_b = _compute_gap_stats(events_b)

    bullets: List[str] = []

    bullets.append(
        f"{label_a} saw {ca} client messages and {aa} assistant touches; "
        f"{label_b} saw {cb} client messages and {ab} assistant touches."
    )

    bullets.append(
        f"Engagement intensity: {label_a} at {ia:.0f} vs {label_b} at {ib:.0f} (0–100 scale)."
    )

    bullets.append(
        f"Modelled conversion likelihood: {label_a} at {pa:.0f}% vs {label_b} at {pb:.0f}%."
    )

    if end_a and end_b:
        bullets.append(
            f"Pipeline outcome: {label_a} finished at **{end_a}**, "
            f"while {label_b} finished at **{end_b}**."
        )

    if path_a and path_b:
        bullets.append(
            f"{label_a} journey: {path_a}. {label_b} journey: {path_b}."
        )

    a_gap = _format_hours(gaps_a.get("longest_gap_h"))
    b_gap = _format_hours(gaps_b.get("longest_gap_h"))

    bullets.append(
        f"Longest silence window: {label_a} at {a_gap}, {label_b} at {b_gap}."
    )

    title = "Why these personas behave differently"
    subtitle = "A quick comparison of engagement, pipeline progression, and likelihood to convert."

    return {
        "title": title,
        "subtitle": subtitle,
        "bullets": bullets,
    }
