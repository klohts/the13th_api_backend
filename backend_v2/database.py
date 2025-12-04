from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from sqlalchemy.orm import declarative_base

Base = declarative_base()


logger = logging.getLogger("backend_v2.database")

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"

DEFAULT_DB_PATH = DATA_DIR / "the13th_allinone.db"
DEFAULT_DB_URL = f"sqlite:///{DEFAULT_DB_PATH}"

DB_URL = os.getenv("THE13TH_DB_URL", str(DEFAULT_DB_URL))

engine = create_engine(
    DB_URL,
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
