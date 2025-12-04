from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from backend_v2.database import Base


class SimCompany(Base):
    __tablename__ = "sim_companies"

    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
