from __future__ import annotations

import logging
import random
from datetime import datetime
from typing import Any, Dict, List, TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Session, relationship

from backend_v2.database import engine
from backend_v2.sim_base import SimBase as Base

if TYPE_CHECKING:
    # Only for type checkers; not imported at runtime (avoids circular imports)
    from backend_v2.services.sim_lab_service import SimLead  # noqa: F401

logger = logging.getLogger("the13th.sim_email.service")


# -------------------------------------------------------------------
# Delayed SimLead loader to avoid circular import
# -------------------------------------------------------------------


def _SimLead():
    """
    Delayed import of SimLead from sim_lab_service to avoid circular imports.

    This is only called inside runtime functions, never at module import time.
    """
    from backend_v2.services.sim_lab_service import SimLead  # type: ignore
    return SimLead


# -------------------------------------------------------------------
# Email simulation models (share Base with Simulation Lab)
# -------------------------------------------------------------------


class SimEmailThread(Base):
    __tablename__ = "sim_email_threads"

    id: int = Column(Integer, primary_key=True, index=True)
    lead_id: int = Column(Integer, ForeignKey("sim_leads.id"), nullable=False)
    subject: str = Column(String(255), nullable=False)
    status: str = Column(String(50), default="open", nullable=False)  # open / closed
    last_direction: str = Column(String(20), default="inbound", nullable=False)
    created_at: datetime = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: datetime = Column(DateTime, default=datetime.utcnow, nullable=False)

    # String-based relationship reference avoids import-time issues
    lead = relationship("SimLead")
    messages = relationship(
        "SimEmailMessage",
        back_populates="thread",
        cascade="all, delete-orphan",
    )


class SimEmailMessage(Base):
    __tablename__ = "sim_email_messages"

    id: int = Column(Integer, primary_key=True, index=True)
    thread_id: int = Column(Integer, ForeignKey("sim_email_threads.id"), nullable=False)
    direction: str = Column(String(20), nullable=False)  # inbound / outbound
    from_address: str = Column(String(255), nullable=False)
    to_address: str = Column(String(255), nullable=False)
    subject: str = Column(String(255), nullable=False)
    body: str = Column(String, nullable=False)
    simulated: bool = Column(Boolean, default=True, nullable=False)
    created_at: datetime = Column(DateTime, default=datetime.utcnow, nullable=False)

    thread = relationship("SimEmailThread", back_populates="messages")


# -------------------------------------------------------------------
# Schema init (idempotent, piggyback on shared Base)
# -------------------------------------------------------------------


def ensure_email_schema() -> None:
    """
    Ensure email simulation tables exist.

    Because we share the same Base as the Simulation Lab,
    calling create_all is safe and idempotent.
    """
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as exc:  # pragma: no cover
        logger.exception("Failed to create email simulation tables: %s", exc)
        raise


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------


def _company_slug(name: str | None) -> str:
    if not name:
        return "demo"
    return (
        name.lower()
        .replace("&", "and")
        .replace(" ", "")
        .replace(",", "")
        .replace(".", "")
    )


def _build_inbound_subject(lead: "SimLead") -> str:  # type: ignore[name-defined]
    base = "Question about working together"
    if lead.status == "new":
        return f"{base}"
    if lead.status == "nurturing":
        return "Quick follow-up on our earlier conversation"
    if lead.status == "won":
        return "Next steps and onboarding details"
    if lead.status == "lost":
        return "Feedback on our decision"
    return base


def _build_inbound_body(lead: "SimLead") -> str:  # type: ignore[name-defined]
    name = getattr(lead, "full_name", None) or "there"
    status_phrase = {
        "new": "just started looking at options",
        "nurturing": "still exploring a few options, but we're interested",
        "won": "already moving forward with you and want to clarify a few items",
        "lost": "gone in a different direction but wanted to share context",
    }.get(getattr(lead, "status", None), "trying to understand your services better")

    return (
        f"Hi there,\n\n"
        f"My name is {name}. We're {status_phrase}.\n\n"
        f"I had a couple of questions about how you work with clients and what the next steps would look like.\n\n"
        f"Thanks,\n"
        f"{name}"
    )


def _build_reply_body(
    lead: "SimLead",  # type: ignore[name-defined]
    last_inbound: SimEmailMessage | None,
) -> str:
    name = getattr(lead, "full_name", None) or "there"
    intro_variants = [
        f"Hi {name}, thanks for reaching out.",
        f"Hi {name}, appreciate your message.",
        f"Hi {name}, great to hear from you.",
    ]
    intro = random.choice(intro_variants)

    context_line = (
        "We help real estate teams stay on top of every lead and conversation using automation and admin intelligence."
    )

    closing = (
        "If you'd like, we can walk you through a quick demo or align on next steps.\n\n"
        "Best regards,\n"
        "THE13TH Demo Agent"
    )

    last_excerpt = ""
    if last_inbound:
        snippet = last_inbound.body.strip().split("\n")[0]
        if snippet:
            last_excerpt = f"\n\n> {snippet[:160]}"

    return f"{intro}\n\n{context_line}{last_excerpt}\n\n{closing}"


def _update_lead_after_reply(lead: "SimLead") -> None:  # type: ignore[name-defined]
    """
    Nudge the simulated lead state when we reply.
    """
    status = getattr(lead, "status", None)
    if status == "new":
        lead.status = "nurturing"
    elif status == "nurturing":
        # small chance of moving to won
        if random.random() < 0.1:
            lead.status = "won"

    # bump score slightly
    current_score = int(getattr(lead, "score", 0) or 0)
    new_score = min(100, max(0, current_score + random.randint(3, 10)))
    lead.score = new_score
    lead.updated_at = datetime.utcnow()


# -------------------------------------------------------------------
# Core operations
# -------------------------------------------------------------------


def simulate_inbound_emails(
    db: Session,
    max_leads: int = 50,
) -> Dict[str, Any]:
    """
    Generate inbound messages from a random slice of Simulation Lab leads.

    - Picks up to max_leads leads (biased towards new / nurturing).
    - Ensures each has a thread.
    - Adds one new inbound message into the thread.
    """

    ensure_email_schema()

    SimLeadModel = _SimLead()

    candidates: List["SimLead"] = (  # type: ignore[name-defined]
        db.query(SimLeadModel)
        .filter(SimLeadModel.status.in_(["new", "nurturing", "won", "lost"]))
        .order_by(func.random())
        .limit(max_leads)
        .all()
    )

    if not candidates:
        return {
            "status": "error",
            "message": "No simulation leads found. Seed Simulation Lab first.",
        }

    threads_created = 0
    inbound_messages_created = 0
    leads_touched = 0

    for lead in candidates:
        leads_touched += 1

        thread = (
            db.query(SimEmailThread)
            .filter(SimEmailThread.lead_id == lead.id)
            .first()
        )

        if thread is None:
            subject = _build_inbound_subject(lead)
            thread = SimEmailThread(
                lead_id=lead.id,
                subject=subject,
                status="open",
                last_direction="inbound",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(thread)
            db.flush()
            threads_created += 1

        company = getattr(lead, "company", None)
        company_slug = _company_slug(getattr(company, "name", None))
        to_address = f"agent@{company_slug}.the13th.io"

        subject = thread.subject or _build_inbound_subject(lead)
        body = _build_inbound_body(lead)

        msg = SimEmailMessage(
            thread_id=thread.id,
            direction="inbound",
            from_address=lead.email,
            to_address=to_address,
            subject=subject,
            body=body,
            simulated=True,
            created_at=datetime.utcnow(),
        )
        db.add(msg)

        thread.last_direction = "inbound"
        thread.updated_at = datetime.utcnow()

        inbound_messages_created += 1

    db.commit()

    logger.info(
        "Simulated inbound emails. leads_touched=%s, threads_created=%s, messages=%s",
        leads_touched,
        threads_created,
        inbound_messages_created,
    )

    return {
        "status": "ok",
        "message": "Simulated inbound emails generated.",
        "leads_touched": leads_touched,
        "threads_created": threads_created,
        "inbound_messages_created": inbound_messages_created,
    }


def auto_reply_to_threads(
    db: Session,
    max_threads: int = 50,
) -> Dict[str, Any]:
    """
    Generate simulated outbound replies for threads whose last message was inbound.
    """

    ensure_email_schema()

    threads: List[SimEmailThread] = (
        db.query(SimEmailThread)
        .filter(
            SimEmailThread.status == "open",
            SimEmailThread.last_direction == "inbound",
        )
        .order_by(SimEmailThread.updated_at.desc())
        .limit(max_threads)
        .all()
    )

    if not threads:
        return {
            "status": "ok",
            "message": "No open inbound threads to reply to.",
            "threads_replied": 0,
            "outbound_messages_created": 0,
        }

    SimLeadModel = _SimLead()

    threads_replied = 0
    outbound_messages_created = 0

    for thread in threads:
        lead = thread.lead  # type: ignore[assignment]
        if lead is None:
            # As a fallback, try to refetch via SimLeadModel
            lead = (
                db.query(SimLeadModel)
                .filter(SimLeadModel.id == thread.lead_id)
                .first()
            )
            if lead is None:
                continue

        last_inbound: SimEmailMessage | None = (
            db.query(SimEmailMessage)
            .filter(
                SimEmailMessage.thread_id == thread.id,
                SimEmailMessage.direction == "inbound",
            )
            .order_by(SimEmailMessage.created_at.desc())
            .first()
        )

        from_address = "demo-agent@the13th.io"
        to_address = lead.email
        subject = f"Re: {thread.subject}"
        body = _build_reply_body(lead, last_inbound)

        msg = SimEmailMessage(
            thread_id=thread.id,
            direction="outbound",
            from_address=from_address,
            to_address=to_address,
            subject=subject,
            body=body,
            simulated=True,
            created_at=datetime.utcnow(),
        )
        db.add(msg)

        _update_lead_after_reply(lead)

        thread.last_direction = "outbound"
        thread.updated_at = datetime.utcnow()

        threads_replied += 1
        outbound_messages_created += 1

    db.commit()

    logger.info(
        "Simulated outbound replies. threads_replied=%s, outbound_messages=%s",
        threads_replied,
        outbound_messages_created,
    )

    return {
        "status": "ok",
        "message": "Simulated replies sent to open threads.",
        "threads_replied": threads_replied,
        "outbound_messages_created": outbound_messages_created,
    }


def get_email_overview(db: Session) -> Dict[str, Any]:
    """
    Aggregate email simulation metrics for dashboards.
    """

    ensure_email_schema()

    total_threads = db.query(SimEmailThread).count()
    open_threads = (
        db.query(SimEmailThread)
        .filter(SimEmailThread.status == "open")
        .count()
    )

    total_messages = db.query(SimEmailMessage).count()
    inbound_count = (
        db.query(SimEmailMessage)
        .filter(SimEmailMessage.direction == "inbound")
        .count()
    )
    outbound_count = (
        db.query(SimEmailMessage)
        .filter(SimEmailMessage.direction == "outbound")
        .count()
    )

    avg_thread_length: float = 0.0
    if total_threads > 0:
        avg_thread_length = float(total_messages) / float(total_threads)

    reply_rate: float = 0.0
    if inbound_count > 0:
        reply_rate = float(outbound_count) / float(inbound_count)

    last_activity: datetime | None = (
        db.query(SimEmailMessage.created_at)
        .order_by(SimEmailMessage.created_at.desc())
        .limit(1)
        .scalar()
    )

    overview: Dict[str, Any] = {
        "status": "ok",
        "total_threads": total_threads,
        "open_threads": open_threads,
        "total_messages": total_messages,
        "inbound_count": inbound_count,
        "outbound_count": outbound_count,
        "avg_thread_length": round(avg_thread_length, 2),
        "reply_rate": round(reply_rate, 2),
        "last_activity": last_activity.isoformat() if last_activity else None,
    }
    return overview
