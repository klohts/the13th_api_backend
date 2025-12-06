from __future__ import annotations

from sqlalchemy.orm import declarative_base

Base = declarative_base()

# Core models
from backend_v2.models.lead import Lead  # noqa: F401,E402
from backend_v2.models.pilot import Pilot  # noqa: F401,E402

# Ingestion / automation models
from backend_v2.models.ingestion_event import IngestionEvent  # noqa: F401,E402
from backend_v2.models.tenant_automation import TenantAutomationSettings  # noqa: F401,E402
from backend_v2.models.automation_event import AutomationEvent  # noqa: F401,E402

__all__ = [
    "Base",
    "Lead",
    "Pilot",
    "IngestionEvent",
    "TenantAutomationSettings",
    "AutomationEvent",
]
