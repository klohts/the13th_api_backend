from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from backend_v2.database import Base


class SimEmailThread(Base):
    __tablename__ = "sim_email_threads"

    id = Column(Integer, primary_key=True, index=True)
    subject = Column(String)
    status = Column(String)  # open / closed
    total_messages = Column(Integer)
    inbound_count = Column(Integer)
    outbound_count = Column(Integer)
    avg_thread_length = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
