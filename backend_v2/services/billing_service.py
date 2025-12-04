# backend_v2/services/billing_service.py

from __future__ import annotations

import logging
from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

logger = logging.getLogger("the13th.admin.billing")


@dataclass
class BillingMetrics:
    """
    Safe-mode billing metrics.

    All fields are defined with sane defaults so that Jinja templates can
    safely access and format them (including with `|round(2)`).
    """

    total_mrr: float = 0.0
    active_subscriptions: int = 0
    active_trials: int = 0
    payment_failures: int = 0

    revenue_7d: float = 0.0
    revenue_30d: float = 0.0
    revenue_90d: float = 0.0

    # For tables / lists on the billing page
    subscriptions: List[Dict[str, Any]] = field(default_factory=list)
    invoices: List[Dict[str, Any]] = field(default_factory=list)


def _empty_metrics() -> Dict[str, Any]:
    """
    Internal helper to construct a default metrics dict.
    """
    return asdict(BillingMetrics())


def get_billing_metrics_safe(db: Optional[Session] = None) -> Dict[str, Any]:
    """
    SAFE MODE IMPLEMENTATION.

    This deliberately does NOT query the database and instead returns
    static zero / empty metrics, so that the admin Billing page can render
    without ever breaking the rest of the admin console.

    Later (after launch), a real DB-backed implementation can be swapped in
    here without touching templates or routers.
    """
    try:
        # We still accept `db` in the signature so that swapping in a real
        # implementation later is trivial.
        logger.info(
            "Billing metrics running in SAFE MODE (no DB queries; returning zero metrics)."
        )

        metrics = _empty_metrics()
        return metrics

    except Exception as exc:
        # Extremely defensive: even if something goes wrong, never let this
        # break the admin UI.
        logger.exception(
            "Unexpected error in get_billing_metrics_safe; falling back to zero metrics: %s",
            exc,
        )
        return _empty_metrics()
