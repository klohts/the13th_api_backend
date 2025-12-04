from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any

logger = logging.getLogger("the13th.client_experience_metrics")


@dataclass
class JourneyEvent:
    """
    Normalized event for KPI metrics.
    """
    timestamp: datetime
    direction: str  # "client" | "assistant"


@dataclass
class KPIResult:
    avg_response_delay_seconds: Optional[float]
    avg_response_delay_label: str
    longest_gap_seconds: Optional[float]
    longest_gap_label: str
    intensity_score: int
    total_touchpoints: int


def _format_gap(seconds: Optional[float]) -> str:
    if seconds is None:
        return "—"
    if seconds < 60:
        return f"{int(seconds)}s"
    if seconds < 3600:
        return f"{int(seconds // 60)}m"
    hours = seconds / 3600
    return f"{hours:.1f}h"


def compute_kpis(events: List[JourneyEvent]) -> KPIResult:
    """
    Compute KPI metrics based on the ordered list of client + assistant events.
    """
    if not events:
        return KPIResult(
            avg_response_delay_seconds=None,
            avg_response_delay_label="—",
            longest_gap_seconds=None,
            longest_gap_label="—",
            intensity_score=0,
            total_touchpoints=0,
        )

    events_sorted = sorted(events, key=lambda e: e.timestamp)

    # -------------------------------
    # 1. TOTAL TOUCHPOINTS
    # -------------------------------
    total_touchpoints = len(events_sorted)

    # -------------------------------
    # 2. LONGEST GAP
    # -------------------------------
    longest_gap = 0.0
    for prev, curr in zip(events_sorted[:-1], events_sorted[1:]):
        gap = (curr.timestamp - prev.timestamp).total_seconds()
        if gap > longest_gap:
            longest_gap = gap

    longest_gap_label = _format_gap(longest_gap or None)

    # -------------------------------
    # 3. AVERAGE RESPONSE DELAY
    # -------------------------------
    response_delays = []
    last_client_ts = None

    for e in events_sorted:
        if e.direction == "client":
            last_client_ts = e.timestamp
        elif e.direction == "assistant" and last_client_ts:
            delay = (e.timestamp - last_client_ts).total_seconds()
            if delay >= 0:
                response_delays.append(delay)
            last_client_ts = None  # reset

    if response_delays:
        avg_delay = sum(response_delays) / len(response_delays)
        avg_delay_label = _format_gap(avg_delay)
    else:
        avg_delay = None
        avg_delay_label = "—"

    # -------------------------------
    # 4. INTENSITY SCORE (simple, interpretable)
    # -------------------------------
    # Weighted combination:
    # - more messages → higher
    # - shorter gaps → higher
    # - frequent alternation → higher
    alternation_bonus = 0
    for prev, curr in zip(events_sorted[:-1], events_sorted[1:]):
        if prev.direction != curr.direction:
            alternation_bonus += 1

    base_score = total_touchpoints * 2
    gap_penalty = max(0, 50 - int((longest_gap or 0) / 360))  # 1 penalty per ~6 min

    intensity_raw = base_score + alternation_bonus + gap_penalty
    intensity_score = max(0, min(100, intensity_raw))

    return KPIResult(
        avg_response_delay_seconds=avg_delay,
        avg_response_delay_label=avg_delay_label,
        longest_gap_seconds=longest_gap or None,
        longest_gap_label=longest_gap_label,
        intensity_score=intensity_score,
        total_touchpoints=total_touchpoints,
    )
