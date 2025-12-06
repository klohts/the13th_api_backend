import datetime
from typing import Any, Dict, Optional

from sqlalchemy import Column, DateTime, Integer, String, JSON, Index

from backend_v2.db import Base


class Lead(Base):
    """Canonical lead model for THE13TH ingestion layer."""

    __tablename__ = "leads"

    id: int = Column(Integer, primary_key=True, index=True)
    tenant_key: Optional[str] = Column(String(64), index=True, nullable=True)
    source: str = Column(String(64), index=True, nullable=False)
    full_name: Optional[str] = Column(String(255), nullable=True)
    email: Optional[str] = Column(String(255), index=True, nullable=True)
    phone: Optional[str] = Column(String(64), index=True, nullable=True)
    assigned_agent: Optional[str] = Column(String(255), nullable=True)
    status: str = Column(String(32), index=True, nullable=False, default="new")
    external_id: Optional[str] = Column(String(64), index=True, nullable=True)
    raw_payload: Dict[str, Any] = Column(JSON, nullable=True)
    created_at: datetime.datetime = Column(
        DateTime, default=datetime.datetime.utcnow, nullable=False, index=True
    )

    __table_args__ = (
        Index("ix_leads_tenant_source_created", "tenant_key", "source", "created_at"),
    )
