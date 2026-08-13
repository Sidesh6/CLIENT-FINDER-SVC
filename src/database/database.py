import logging
import os
from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.database.models import Base

logger = logging.getLogger(__name__)

# Default database: SQLite database file in project root
DEFAULT_DB_URL = "sqlite:///client_finder.db"


def get_db_url() -> str:
    """Retrieve database connection URL from environment or return default SQLite."""
    return os.getenv("DATABASE_URL", DEFAULT_DB_URL)


def get_engine(db_url: str | None = None, echo: bool = False) -> Engine:
    """
    Create a SQLAlchemy Engine.
    For SQLite, automatically enables connect_args={'check_same_thread': False}.
    """
    url = db_url or get_db_url()
    connect_args = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    return create_engine(url, echo=echo, connect_args=connect_args)


def init_db(engine: Engine) -> None:
    """Create all database tables defined in SQLAlchemy Base metadata."""
    logger.info("Initializing database schema on %s...", engine.url)
    Base.metadata.create_all(bind=engine)
    logger.info("Database schema initialized successfully.")


def get_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create a session factory bound to the provided engine."""
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


@contextmanager
def get_db_session(session_factory: sessionmaker[Session]) -> Generator[Session, None, None]:
    """
    Context manager for database sessions with automatic commit/rollback.
    """
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception as exc:
        session.rollback()
        logger.error("Database transaction rolled back due to error: %s", exc)
        raise
    finally:
        session.close()
