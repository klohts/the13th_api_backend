from __future__ import annotations

import logging
from typing import List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..models import Lead

logger = logging.getLogger("the13th.backend_v2.services.leads")


def list_leads(
    session: Session,
    *,
    limit: int = 100,
    offset: int = 0,
    status: Optional[str] = None,
    search: Optional[str] = None,
) -> List[Lead]:
    """
    Return a list of leads with optional filtering.

    Uses SQLAlchemy ORM query API to avoid SQLModel select()
    coercion issues when Lead is a classic ORM model.
    """
    try:
        query = session.query(Lead)

        if status:
            query = query.filter(Lead.status == status)

        if search:
            like = f"%{search}%"
            query = query.filter(
                or_(
                    Lead.first_name.ilike(like),
                    Lead.last_name.ilike(like),
                    Lead.email.ilike(like),
                    Lead.brokerage_name.ilike(like),
                )
            )

        query = (
            query.order_by(Lead.created_at.desc())
            .offset(offset)
            .limit(limit)
        )

        leads: List[Lead] = query.all()

        logger.debug(
            "Fetched %d leads (status=%s, search=%s, limit=%d, offset=%d)",
            len(leads),
            status,
            search,
            limit,
            offset,
        )
        return leads

    except Exception:
        logger.exception(
            "Error while fetching leads (status=%s, search=%s, limit=%d, offset=%d)",
            status,
            search,
            limit,
            offset,
        )
        raise


def create_lead(session: Session, lead_data: dict) -> Lead:
    """
    Create and persist a lead from dict data.
    """
    try:
        lead = Lead(**lead_data)
        session.add(lead)
        session.flush()  # ensure id is populated before returning

        logger.info("Created lead id=%s email=%s", lead.id, getattr(lead, "email", None))
        return lead

    except Exception:
        logger.exception("Failed to create lead from data: %r", lead_data)
        raise
