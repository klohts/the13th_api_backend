from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from backend_v2.database import Base


class SimAgentActivity(Base):
    __tablename__ = "sim_agent_activity"

    id = Column(Integer, primary_key=True, index=True)
    agent_name = Column(String, index=True)
    actions = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow)
