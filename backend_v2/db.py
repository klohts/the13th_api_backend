from __future__ import annotations

import logging
from typing import Generator

from sqlmodel import SQLModel, Session, create_engine

from .config import settings

logger = logging.getLogger("the13th.backend_v2.db")


def _create_engine():
    """Create the SQLAlchemy/SQLModel engine for THE13TH admin DB."""
    connect_args = {}
    if settings.database_url.startswith("sqlite"):
        # Required for SQLite in multithreaded FastAPI context
        connect_args = {"check_same_thread": False}

    engine_ = create_engine(
        settings.database_url,
        echo=bool(settings.debug),
        connect_args=connect_args,
    )
    logger.debug("DB engine created for URL: %s", settings.database_url)
    return engine_


engine = _create_engine()


def init_db() -> None:
    """Create all tables if they do not exist."""
    # Import models so SQLModel metadata is populated
    from . import models  # noqa: F401

    logger.info("Initializing database schema...")
    SQLModel.metadata.create_all(engine)
    logger.info("Database schema initialized.")


def get_session() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a DB session.

    - Commits if the endpoint finishes without errors.
    - Rolls back on exception.
    - Always closes the session.
    """
    session = Session(engine)
    try:
        yield session
        session.commit()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error during DB session, rolling back: %s", exc)
        session.rollback()
        raise
    finally:
        session.close()


# ✅ ALIAS FOR ROUTERS EXPECTING get_db
get_db = get_session
