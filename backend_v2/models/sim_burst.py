from sqlalchemy import Column, Integer, DateTime
from datetime import datetime
from backend_v2.database import Base


class SimBurst(Base):
    __tablename__ = "sim_bursts"

    id = Column(Integer, primary_key=True, index=True)
    burst_index = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
