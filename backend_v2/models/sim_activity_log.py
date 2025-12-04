
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, func
from backend_v2.database import Base

class SimActivityLog(Base):
    __tablename__ = "sim_activity_log"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, nullable=False)
    agent_id = Column(Integer, nullable=True)
    lead_id = Column(Integer, nullable=True)
    event_type = Column(String(50), nullable=False)
    score_change = Column(Float, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), index=True)
