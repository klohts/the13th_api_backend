import logging
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import URL, make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from backend_v2.config import settings

logger = logging.getLogger("the13th.backend_v2.db")

Base = declarative_base()


def _build_sqlalchemy_url(raw_url: str) -> URL:
    """
    Validate and parse the DATABASE_URL string into a SQLAlchemy URL.
    Raises a RuntimeError with a clear message if invalid.
    """
    if not raw_url or not raw_url.strip():
        msg = (
            "DATABASE_URL is empty or not set. "
            "Set DATABASE_URL in your environment or .env file, e.g.:\n"
            "  DATABASE_URL=sqlite:///./the13th.db\n"
            "or a Postgres URL, e.g.:\n"
            "  DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/dbname"
        )
        logger.error(msg)
        raise RuntimeError(msg)

    try:
        url = make_url(raw_url)
    except Exception as exc:
        msg = (
            f"Invalid DATABASE_URL '{raw_url}'. "
            "Expected a valid SQLAlchemy URL such as:\n"
            "  sqlite:///./the13th.db\n"
            "  postgresql+psycopg2://user:pass@host:5432/dbname"
        )
        logger.error(msg)
        raise RuntimeError(msg) from exc

    # Log a safe version without credentials
    safe_url = url.set(password="***") if url.password else url
    logger.info("Using DATABASE_URL=%s", safe_url)
    return url


def _create_engine() -> Engine:
    """
    Create the global SQLAlchemy engine using the configured DATABASE_URL.
    """
    raw_url: str = settings.database_url
    url: URL = _build_sqlalchemy_url(raw_url)

    try:
        engine = create_engine(
            url,
            echo=False,
            future=True,
            pool_pre_ping=True,
        )
    except SQLAlchemyError:
        logger.exception("Failed to create database engine for %s", url)
        raise

    logger.info("Database engine created for %s", url)
    return engine


engine: Engine = _create_engine()

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=Session,
)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a database session and ensures it is closed.
    """
    db: Session = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        logger.exception("Error during DB session; rolling back.")
        db.rollback()
        raise
    finally:
        db.close()


def get_session() -> Generator[Session, None, None]:
    """
    Backwards-compatible alias for FastAPI dependency usage.

    Existing routers that do:
        from backend_v2.db import get_session
        ...
        def endpoint(..., db: Session = Depends(get_session)):

    will keep working.
    """
    yield from get_db()


def init_db() -> None:
    """
    Initialize the database by creating all tables.
    Import models inside the function to avoid circular imports.
    """
    import backend_v2.models  # noqa: F401

    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created/verified successfully.")
    except SQLAlchemyError:
        logger.exception("Failed to initialize database schema.")
        raise
