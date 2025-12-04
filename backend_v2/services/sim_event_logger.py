
import logging
from sqlalchemy.orm import Session
from backend_v2.models.sim_activity_log import SimActivityLog

log = logging.getLogger("the13th.sim_event")

def log_sim_event(
    db: Session,
    *,
    company_id: int,
    agent_id: int | None = None,
    lead_id: int | None = None,
    event_type: str,
    score_delta: float | None = None
):
    try:
        entry = SimActivityLog(
            company_id=company_id,
            agent_id=agent_id,
            lead_id=lead_id,
            event_type=event_type,
            score_change=score_delta,
        )
        db.add(entry)
        db.commit()
    except Exception as exc:
        log.error(f"Failed to log event: {exc}")
