from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, String, Text

from backend_v2.database import Base  # Your Base metadata object


class SimReportLog(Base):
    __tablename__ = "sim_reports_log"

    id = Column(Integer, primary_key=True, autoincrement=True)

    generated_at = Column(DateTime, default=datetime.utcnow)
    report_type = Column(String(50), nullable=False, default="weekly_intel")

    file_path = Column(String(500), nullable=False)

    summary_json = Column(Text, nullable=True)
