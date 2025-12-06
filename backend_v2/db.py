from __future__ import annotations

import logging
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlmodel import SQLModel

from backend_v2.config import settings

logger = logging.getLogger("the13th.backend_v2.db")


def _create_engine() -> Engine:
    """
    Create the SQLAlchemy engine based on DATABASE_URL.
    Handles SQLite vs non-SQLite differences.
    """
    database_url = settings.database_url
    connect_args = {}

    if database_url.startswith("sqlite"):
        # Needed for SQLite when used in multi-threaded FastAPI context
        connect_args["check_same_thread"] = False

    engine = create_engine(
        database_url,
        echo=settings.debug,
        future=True,
        connect_args=connect_args,
    )
    logger.info("Database engine created for %s", database_url)
    return engine


engine: Engine = _create_engine()

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=Session,
)


def get_session() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a database session and
    makes sure it is closed afterwards.
    """
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Alias used by some routers
get_db = get_session

# Backwards-compatible Base alias; models can inherit from this if needed.
Base = SQLModel


def init_db() -> None:
    """
    Import all model modules and create tables.

    Uses SQLModel.metadata so all SQLModel-based tables
    (Lead, Pilot, etc.) are created in the same metadata.
    """
    import backend_v2.models  # noqa: F401  # ensures models are imported

    logger.info("Ensuring database tables exist via SQLModel.metadata.create_all()")
    SQLModel.metadata.create_all(bind=engine)
    logger.info("Database tables ensured.")


__all__ = [
    "Base",
    "engine",
    "SessionLocal",
    "get_db",
    "get_session",
    "init_db",
]
