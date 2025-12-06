from __future__ import annotations

"""
Models package for THE13TH backend_v2.

Imports and exposes ORM models so they are registered with SQLModel.metadata.
"""

import logging

from backend_v2.db import Base  # SQLModel alias, keeps external imports consistent
from .lead import Lead  # noqa: F401
from .pilot import Pilot, PilotStatus  # noqa: F401

logger = logging.getLogger("the13th.backend_v2.models")

__all__ = [
    "Base",
    "Lead",
    "Pilot",
    "PilotStatus",
]
