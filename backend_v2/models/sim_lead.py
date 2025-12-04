from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime
from backend_v2.database import Base


class SimLead(Base):
    __tablename__ = "sim_leads"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("sim_companies.id"), index=True)

    name = Column(String)
    price = Column(Integer)
    deal_stage = Column(String)

    score_band = Column(String)

    last_activity = Column(DateTime, default=datetime.utcnow)
