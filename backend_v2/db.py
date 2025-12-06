import logging
from typing import Any, Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from backend_v2.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------
# Declarative Base
# ---------------------------------------------------------
# All your models (Lead, Pilot, etc.) should subclass this.
Base = declarative_base()


def _create_engine() -> Engine:
    """
    Create and return the SQLAlchemy engine using settings.database_url.
    Handles SQLite vs others and enables pool_pre_ping.
    """
    database_url: str = settings.database_url

    if not database_url:
        # Fail fast with clear logging if misconfigured
        logger.critical("DATABASE_URL / database_url is empty in settings.")
        raise RuntimeError("DATABASE_URL / database_url is not configured")

    connect_args: dict[str, Any] = {}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    engine: Engine = create_engine(
        database_url,
        echo=settings.debug,
        future=True,
        pool_pre_ping=True,
        connect_args=connect_args,
    )

    logger.info("Database engine created for URL: %s", database_url)
    return engine


# Global engine + session factory
engine: Engine = _create_engine()

SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    autocommit=False,
    autoflush=False,
    future=True,
)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a DB session and guarantees cleanup.
    """
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Import all ORM models and create tables if they do not exist.

    This should be called once on startup (e.g. in main.py).
    Import happens here (not at module import) to avoid circular imports.
    """
    # Import all modules that define models so that
    # Base.metadata has all tables before create_all().
    import backend_v2.models  # noqa: F401

    logger.info("Ensuring database tables exist via Base.metadata.create_all()")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ensured.")


__all__ = ["Base", "engine", "SessionLocal", "get_db", "init_db"]
