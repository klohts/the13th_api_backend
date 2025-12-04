
"""
client_experience_context.py
Normalizes and completes the context dictionary for the cinematic
Client Journey Studio page so that the UI never receives missing values.
"""

from typing import Any, Dict, List


def safe_val(value, default):
    """Return value if truthy, else default."""
    return value if value not in (None, "", [], {}, "null", "None") else default


def build_persona_label(persona: str) -> str:
    mapping = {
        "hot_lead": "Hot Buyer",
        "warm_lead": "Warm Buyer",
        "cold_lead": "Cold Buyer",
    }
    return mapping.get(persona, "Hot Buyer")


def normalize_summary(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure summary dict has ALL fields required by the cinematic UI."""

    raw = raw or {}

    return {
        # Core stats
        "conversion_likelihood": safe_val(raw.get("conversion_likelihood"), "—"),
        "dropoff_risk": safe_val(raw.get("dropoff_risk"), "—"),
        "engagement_intensity": safe_val(raw.get("engagement_intensity"), "—"),
        "pipeline_depth_label": safe_val(raw.get("pipeline_depth_label"), "—"),

        # Persona & behavior descriptors
        "reply_pattern_label": safe_val(raw.get("reply_pattern_label"), "Fast, consistent follow-up"),
        "risk_profile_label": safe_val(raw.get("risk_profile_label"), "Medium risk, high upside"),
        "intent_label": safe_val(raw.get("intent_label"), "Actively shopping"),
        "delay_sensitivity_label": safe_val(raw.get("delay_sensitivity_label"), "High — slow replies increase risk"),
        "channel_mix_label": safe_val(raw.get("channel_mix_label"), "Email-first, then phone/video"),
        "key_risk_label": safe_val(raw.get("key_risk_label"), "If ignored for 48–72 hours, they move on"),

        # Outcome
        "outcome_raw": safe_val(raw.get("outcome_raw"), "open"),
        "outcome_label": safe_val(raw.get("outcome_label"), "Likely to convert"),
        "outcome_headline": safe_val(
            raw.get("outcome_headline"),
            "This lead is on track to close if you maintain current reply patterns."
        ),
        "outcome_copy": safe_val(
            raw.get("outcome_copy"),
            "THE13TH projects a strong probability this client will buy or sign within 14–30 days."
        ),

        # GTM impact stats
        "saved_leads_label": safe_val(raw.get("saved_leads_label"), "2–4 per 100 leads"),
        "avg_reply_time_label": safe_val(raw.get("avg_reply_time_label"), "Under 20 minutes"),
        "extra_deals_label": safe_val(raw.get("extra_deals_label"), "+1–3 per team"),
        "forecast_accuracy_label": safe_val(raw.get("forecast_accuracy_label"), "Within 8–12% of reality"),

        # Story steps
        "initial_score": safe_val(raw.get("initial_score"), "82"),
        "median_reply_time_label": safe_val(raw.get("median_reply_time_label"), "17 minutes"),
        "engagement_intensity_label": safe_val(raw.get("engagement_intensity_label"), "High"),
        "story_step_1": safe_val(raw.get("story_step_1"), "They click on a listing and show strong intent."),
        "story_step_2": safe_val(raw.get("story_step_2"), "Assistant acknowledges, qualifies, and narrows next steps."),
        "story_step_3": safe_val(raw.get("story_step_3"), "Model keeps nudging and preventing them from going cold."),
        "story_step_4": safe_val(raw.get("story_step_4"), "Outcome feeds back to forecasting."),
    }


def normalize_timeline(raw: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Ensure timeline events always exist and have safe defaults."""
    if not raw:
        return [{
            "day": 0,
            "day_label": "0",
            "event_type": "info",
            "event_type_label": "Event",
            "headline": "Simulation initialized",
            "meta": "Run simulation to populate timeline.",
            "email": None,
        }]

    out = []
    for item in raw:
        out.append({
            "day": item.get("day", 0),
            "day_label": str(item.get("day_label", item.get("day", 0))),
            "event_type": item.get("event_type", "info"),
            "event_type_label": item.get("event_type_label", "Touchpoint"),
            "headline": item.get("headline", "Message exchanged"),
            "meta": item.get("meta", ""),
            "email": item.get("email") or None,
        })
    return out


def normalize_journey_points(points: Any) -> List[Dict[str, Any]]:
    """Ensure journey points exist."""
    if not points:
        return []
    fixed = []
    for p in points:
        fixed.append({
            "x": p.get("x", 0),
            "y": p.get("y", 0),
        })
    return fixed


def normalize_labels(labels: Any) -> List[str]:
    """Ensure stage labels exist."""
    if not labels:
        return []
    return [str(x) for x in labels]


def normalize_email_threads(raw: Any) -> List[Dict[str, Any]]:
    """Ensure email intelligence threads are always defined."""
    if not raw:
        return []
    out = []
    for t in raw:
        out.append({
            "channel_label": t.get("channel_label", "Email"),
            "subject": t.get("subject", "Follow-up"),
            "summary": t.get("summary", ""),
            "preview": t.get("preview", ""),
        })
    return out


def build_full_context(
    persona: str,
    simulation_days: int,
    summary: Dict[str, Any],
    timeline_events: List[Dict[str, Any]],
    journey_points: List[Dict[str, Any]],
    journey_stage_labels: List[str],
    email_threads: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Produce the complete context dictionary for the cinematic UI.
    """

    return {
        "active_nav": "client-experience",
        "persona": persona,
        "persona_label": build_persona_label(persona),
        "simulation_days": simulation_days,

        "summary": normalize_summary(summary),
        "timeline_events": normalize_timeline(timeline_events),
        "journey_points": normalize_journey_points(journey_points),
        "journey_stage_labels": normalize_labels(journey_stage_labels),
        "email_threads": normalize_email_threads(email_threads),
    }
