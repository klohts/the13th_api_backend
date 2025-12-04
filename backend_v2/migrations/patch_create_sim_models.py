#!/usr/bin/env python3
"""
THE13TH — Model Generator (Option A)
Creates all Simulation Lab ORM model files in backend_v2/models/.

Safe:
 - Backs up existing files automatically
 - Creates missing directories
 - Idempotent (can be re-run)
"""

import os
import sys
import shutil
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[2]
MODELS_DIR = ROOT / "backend_v2" / "models"

FILES = {
    "sim_company.py": """from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from backend_v2.database import Base


class SimCompany(Base):
    __tablename__ = "sim_companies"

    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
""",

    "sim_lead.py": """from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
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
""",

    "sim_agent_activity.py": """from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from backend_v2.database import Base


class SimAgentActivity(Base):
    __tablename__ = "sim_agent_activity"

    id = Column(Integer, primary_key=True, index=True)
    agent_name = Column(String, index=True)
    actions = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow)
""",

    "sim_burst.py": """from sqlalchemy import Column, Integer, DateTime
from datetime import datetime
from backend_v2.database import Base


class SimBurst(Base):
    __tablename__ = "sim_bursts"

    id = Column(Integer, primary_key=True, index=True)
    burst_index = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
""",

    "sim_email_thread.py": """from sqlalchemy import Column, Integer, String, DateTime
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
"""
}


def safe_write(path: Path, content: str):
    """Backup and write file safely."""
    if path.exists():
        backup = path.with_suffix(path.suffix + f".bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        shutil.copy2(path, backup)
        print(f"[BACKUP] {path.name} → {backup.name}")

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[WRITE]  {path.name}")


def main():
    print("=== THE13TH • Simulation Models Generator (Option A) ===")
    print("Project root:", ROOT)
    print("Models dir :", MODELS_DIR)

    if not MODELS_DIR.exists():
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        print("[CREATE] models directory created.")

    for filename, content in FILES.items():
        path = MODELS_DIR / filename
        safe_write(path, content)

    print("\n=== DONE ===")
    print("All Simulation ORM model files have been written successfully.")
    print("You can now restart the backend:")
    print("  python -m backend_v2.run_uvicorn\n")


if __name__ == "__main__":
    main()
