# backend_v2/sim_client_engine.py

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Literal

logger = logging.getLogger("the13th.client_sim_engine")

Stage = Literal[
    "New",
    "Inquiry",
    "Engaged",
    "Warm",
    "Active",
    "Hot",
    "High Intent",
    "Under Contract",
    "Converted",
    "Won",
    "Lost",
]
Actor = Literal["client", "assistant", "system"]


# =========================================================
# PERSONA DEFINITIONS (Option A – unified)
# =========================================================

@dataclass
class PersonaConfig:
    key: str
    label: str
    description: str
    starting_stage: Stage
    reply_chance: float
    proactive_chance: float
    drop_off_chance: float
    revive_chance: float


@dataclass
class SimEvent:
    day_index: int
    actor: Actor
    stage_before: Stage
    stage_after: Stage
    message: str
    time_label: str


_PERSONAS: Dict[str, PersonaConfig] = {
    # 1) Hot Buyer (key kept as hot_lead for compatibility with router default)
    "hot_lead": PersonaConfig(
        key="hot_lead",
        label="Hot Buyer",
        description="Highly responsive lead with strong signals, quick replies, and rapid stage progression.",
        starting_stage="Engaged",
        reply_chance=0.85,
        proactive_chance=0.60,
        drop_off_chance=0.05,
        revive_chance=0.15,
    ),
    # 2) Ghosting Lead
    "ghosting_lead": PersonaConfig(
        key="ghosting_lead",
        label="Ghosting Lead",
        description="Engages early but goes silent for long stretches. Assistant must follow nurture cadences.",
        starting_stage="Warm",
        reply_chance=0.25,
        proactive_chance=0.65,
        drop_off_chance=0.12,
        revive_chance=0.30,
    ),
    # 3) Slow Nurture Lead
    "slow_nurture": PersonaConfig(
        key="slow_nurture",
        label="Slow Nurture Lead",
        description="Replies every few days with smaller messages, moving slowly through the funnel.",
        starting_stage="New",
        reply_chance=0.40,
        proactive_chance=0.50,
        drop_off_chance=0.06,
        revive_chance=0.25,
    ),
    # 4) Impatient Buyer
    "impatient_buyer": PersonaConfig(
        key="impatient_buyer",
        label="Impatient Buyer",
        description="Demands fast answers, sends long and urgent messages, escalates quickly.",
        starting_stage="Engaged",
        reply_chance=0.80,
        proactive_chance=0.70,
        drop_off_chance=0.03,
        revive_chance=0.12,
    ),
    # 5) Research-Heavy Buyer
    "research_heavy": PersonaConfig(
        key="research_heavy",
        label="Research-Heavy Buyer",
        description="Provides detailed replies, asks many questions, and takes time to evaluate options.",
        starting_stage="Inquiry",
        reply_chance=0.55,
        proactive_chance=0.55,
        drop_off_chance=0.05,
        revive_chance=0.15,
    ),
    # 6) Negative-Cues Lead
    "negative_cues": PersonaConfig(
        key="negative_cues",
        label="Negative-Cues Lead",
        description="Short replies, longer delays, subtle hints of disengagement or uncertainty.",
        starting_stage="Warm",
        reply_chance=0.30,
        proactive_chance=0.45,
        drop_off_chance=0.15,
        revive_chance=0.10,
    ),
}


def get_available_personas() -> List[Dict[str, str]]:
    """
    Personas exposed to the Client Experience Simulation UI.
    """
    return [
        {
            "key": p.key,
            "label": p.label,
            "description": p.description,
        }
        for p in _PERSONAS.values()
    ]


def _get_persona(key: str) -> PersonaConfig:
    if key in _PERSONAS:
        return _PERSONAS[key]
    logger.warning("Unknown persona %s; defaulting to hot_lead", key)
    return _PERSONAS["hot_lead"]


# =========================================================
# CANONICAL STAGE FLOW
# =========================================================

_STAGE_FLOW: List[Stage] = [
    "New",
    "Inquiry",
    "Engaged",
    "Warm",
    "Active",
    "Hot",
    "High Intent",
    "Under Contract",
    "Converted",
    "Won",
    "Lost",
]


# =========================================================
# STAGE TRANSITION LOGIC
# =========================================================

def _next_stage(current: Stage, positive: bool, rnd: random.Random) -> Stage:
    if current in ("Converted", "Lost", "Won"):
        return current

    if not positive:
        if rnd.random() < 0.40:
            return "Lost"
        return current

    try:
        idx = _STAGE_FLOW.index(current)
    except ValueError:
        return current

    if idx >= len(_STAGE_FLOW) - 1:
        return "Converted"

    if rnd.random() < 0.70:
        return _STAGE_FLOW[idx + 1]

    return current


# =========================================================
# MESSAGE GENERATORS
# =========================================================

def _client_message_for(stage: Stage, persona: PersonaConfig, rnd: random.Random) -> str:
    messages: Dict[str, List[str]] = {
        "New": [
            "Hi, I saw one of your listings and wanted more details.",
            "I'm early in the process and just exploring options.",
        ],
        "Inquiry": [
            "I’m curious — can you help me compare some options?",
            "What would you recommend for my situation?",
        ],
        "Engaged": [
            "Thanks — can we dig deeper on neighborhoods?",
            "This is useful. Could you refine options for my budget?",
        ],
        "Warm": [
            "A couple of these look promising. What should I focus on?",
            "Can you break down the tradeoffs clearly?",
        ],
        "Active": [
            "I’m close to deciding. What’s realistic next?",
            "This week works — what’s the next step?",
        ],
        "Hot": [
            "I’m ready to move if the numbers work.",
            "This looks strong — what would you do in my position?",
        ],
        "High Intent": [
            "Let's move forward. Can we prep next steps?",
            "This aligns well. Let’s discuss numbers plus timing.",
        ],
        "Converted": [
            "Appreciate everything — this feels like the right move.",
            "Thanks for the guidance, I’m moving ahead.",
        ],
        "Lost": [
            "Thanks — I’m going to pause for now.",
            "I’ve decided to go another direction.",
        ],
    }
    return rnd.choice(messages.get(stage, ["Just checking in…"]))


def _assistant_message_for(stage: Stage, persona: PersonaConfig, rnd: random.Random) -> str:
    messages: Dict[str, List[str]] = {
        "New": [
            "Here’s a quick overview of the process plus a few tailored options.",
            "I’ve prepared a shortlist based on what most buyers like you prefer.",
        ],
        "Inquiry": [
            "Here are three clear paths that could fit your needs.",
            "I’ve mapped pros and cons so you can compare quickly.",
        ],
        "Engaged": [
            "Based on your feedback, I refined the best-matching options.",
            "Here’s a cleaner breakdown of the strongest fits.",
        ],
        "Warm": [
            "Here’s a focused shortlist to make decisions easier.",
            "I’ve summarized the best next actions.",
        ],
        "Active": [
            "Here’s a plan for the next 7–10 days.",
            "Timing-wise, this is the window where decisions work best.",
        ],
        "Hot": [
            "Here’s a numbers + timing breakdown.",
            "Based on your criteria, here’s the move I’d prioritize.",
        ],
        "High Intent": [
            "Here’s a precise breakdown of terms so you can commit comfortably.",
            "I’ve structured a path that balances risk, timing, and upside.",
        ],
        "Converted": [
            "I’ll keep everything organized in the background.",
            "Here are the next important dates and milestones.",
        ],
        "Lost": [
            "If timing changes, I can resume instantly from where we left off.",
            "I’ll track new opportunities quietly in case things reopen.",
        ],
    }
    return rnd.choice(messages.get(stage, ["I’ve summarized logical next steps."]))


def _system_summary_for(day: int, stage: Stage, converted: bool, lost: bool) -> str:
    if converted:
        return f"Day {day}: Lead converted; assistant will maintain structured follow-through."
    if lost:
        return f"Day {day}: Lead is Lost; assistant remains on light-touch watch."
    if stage in ("High Intent", "Hot", "Active"):
        return f"Day {day}: Lead is highly engaged; focused, time-sensitive communication recommended."
    if stage in ("Warm", "Engaged"):
        return f"Day {day}: Lead warming steadily with consistent engagement."
    return f"Day {day}: Early-stage nurture continuing; assistant keeps friction low."


# =========================================================
# CONVERSATION GRAPH ENGINE
# =========================================================

def build_conversation_graph(events: List[SimEvent], days: int) -> Dict[str, Any]:
    """
    Produces template-ready keys:

      - stage_timeline: [
            {day: 1, stage: "Warm", stage_index: 3},
            ...
        ]

      - message_timeline: [
            {day:1, client: X, assistant: Y, system: Z},
            ...
        ]
    """

    # Stage timeline
    stage_timeline: List[Dict[str, Any]] = []
    last_stage: Stage = "New"

    stage_order: List[Stage] = []
    stage_to_idx: Dict[Stage, int] = {}

    for d in range(1, days + 1):
        todays = [e for e in events if e.day_index == d]
        if todays:
            last_stage = todays[-1].stage_after

        if last_stage not in stage_to_idx:
            stage_to_idx[last_stage] = len(stage_order)
            stage_order.append(last_stage)

        stage_timeline.append(
            {
                "day": d,
                "stage": last_stage,
                "stage_index": stage_to_idx[last_stage],
            }
        )

    # Message timeline
    message_timeline: List[Dict[str, Any]] = []

    for d in range(1, days + 1):
        counts = {"client": 0, "assistant": 0, "system": 0}
        for e in events:
            if e.day_index != d:
                continue
            counts[e.actor] += 1

        message_timeline.append(
            {
                "day": d,
                "client": counts["client"],
                "assistant": counts["assistant"],
                "system": counts["system"],
            }
        )

    return {
        "stage_timeline": stage_timeline,
        "message_timeline": message_timeline,
    }


# =========================================================
# MAIN SIMULATION FUNCTION
# =========================================================

def run_client_simulation(
    *,
    days: int = 30,
    persona_key: str = "hot_lead",
    seed: int | None = None,
) -> Dict[str, Any]:
    """
    Run a persona-driven simulation over N days.
    This is the engine backing the Client Experience Simulation page.
    """

    if days < 7:
        days = 7
    if days > 90:
        days = 90

    persona = _get_persona(persona_key)
    rnd = random.Random(seed or int(datetime.utcnow().timestamp()))

    current_stage: Stage = persona.starting_stage
    events: List[SimEvent] = []

    client_msg_count = 0
    assistant_msg_count = 0
    system_msg_count = 0

    for day in range(1, days + 1):
        day_label = f"Day {day}"
        dt = datetime.utcnow() - timedelta(days=(days - day))

        # 1) Client reply (if not terminal)
        if current_stage not in ("Converted", "Lost"):
            if rnd.random() < persona.reply_chance:
                msg = _client_message_for(current_stage, persona, rnd)
                new_stage = _next_stage(current_stage, positive=True, rnd=rnd)

                events.append(
                    SimEvent(
                        day_index=day,
                        actor="client",
                        stage_before=current_stage,
                        stage_after=new_stage,
                        message=msg,
                        time_label=f"{day_label} — {dt.strftime('%I:%M %p')}",
                    )
                )
                client_msg_count += 1
                current_stage = new_stage

        # 2) Drop-off logic
        if current_stage not in ("Converted", "Lost"):
            if rnd.random() < persona.drop_off_chance:
                msg = _client_message_for("Lost", persona, rnd)
                events.append(
                    SimEvent(
                        day_index=day,
                        actor="client",
                        stage_before=current_stage,
                        stage_after="Lost",
                        message=msg,
                        time_label=f"{day_label} — {dt.strftime('%I:%M %p')}",
                    )
                )
                client_msg_count += 1
                current_stage = "Lost"

        # 3) Assistant proactive follow-up
        if current_stage not in ("Converted", "Lost"):
            if rnd.random() < persona.proactive_chance:
                msg = _assistant_message_for(current_stage, persona, rnd)
                maybe_new = (
                    _next_stage(current_stage, positive=True, rnd=rnd)
                    if rnd.random() < 0.30
                    else current_stage
                )

                events.append(
                    SimEvent(
                        day_index=day,
                        actor="assistant",
                        stage_before=current_stage,
                        stage_after=maybe_new,
                        message=msg,
                        time_label=f"{day_label} — {(dt + timedelta(hours=6)).strftime('%I:%M %p')}",
                    )
                )
                assistant_msg_count += 1
                current_stage = maybe_new

        # 4) Revival from Lost
        if current_stage == "Lost" and rnd.random() < persona.revive_chance:
            events.append(
                SimEvent(
                    day_index=day,
                    actor="client",
                    stage_before="Lost",
                    stage_after="Warm",
                    message="Replied after going quiet — revived.",
                    time_label=f"{day_label} — {(dt + timedelta(hours=9)).strftime('%I:%M %p')}",
                )
            )
            client_msg_count += 1
            current_stage = "Warm"

        # 5) System summary event
        converted = current_stage == "Converted"
        lost = current_stage == "Lost"
        summary = _system_summary_for(day, current_stage, converted, lost)

        events.append(
            SimEvent(
                day_index=day,
                actor="system",
                stage_before=current_stage,
                stage_after=current_stage,
                message=summary,
                time_label=f"{day_label} — {(dt + timedelta(hours=20)).strftime('%I:%M %p')}",
            )
        )
        system_msg_count += 1

    converted_flag = any(e.stage_after == "Converted" for e in events)

    events_payload = [asdict(e) for e in events]
    graphs = build_conversation_graph(events, days)

    return {
        "persona_key": persona.key,
        "persona_label": persona.label,
        "persona_description": persona.description,
        "days": days,
        "final_stage": current_stage,
        "converted": converted_flag,
        "events": events_payload,
        "graphs": graphs,
        "stats": {
            "client_messages": client_msg_count,
            "assistant_messages": assistant_msg_count,
            "system_messages": system_msg_count,
            "total_messages": client_msg_count
            + assistant_msg_count
            + system_msg_count,
        },
    }
