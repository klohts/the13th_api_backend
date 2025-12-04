from __future__ import annotations

import logging
from typing import Optional

from sqlmodel import Session, select

from ..models import Lead

logger = logging.getLogger("the13th.backend_v2.services.leads")


def list_leads(
    session: Session,
    *,
    limit: int = 100,
    offset: int = 0,
    status: Optional[str] = None,
    search: Optional[str] = None,
) -> list[Lead]:
    """Return a list of leads with optional filtering."""
    query = select(Lead)

    if status:
        query = query.where(Lead.status == status)

    if search:
        like = f"%{search}%"
        query = query.where(
            (Lead.first_name.ilike(like))
            | (Lead.last_name.ilike(like))
            | (Lead.email.ilike(like))
            | (Lead.brokerage_name.ilike(like))
        )

    query = query.order_by(Lead.created_at.desc()).offset(offset).limit(limit)

    leads = list(session.exec(query).all())
    logger.debug(
        "Fetched %d leads (status=%s, search=%s, limit=%d, offset=%d)",
        len(leads),
        status,
        search,
        limit,
        offset,
    )
    return leads


def create_lead(session: Session, lead_data: dict) -> Lead:
    """Create and persist a lead from dict data."""
    lead = Lead(**lead_data)
    session.add(lead)
    session.flush()  # ensure id is populated
    logger.info("Created lead id=%s email=%s", lead.id, lead.email)
    return lead
