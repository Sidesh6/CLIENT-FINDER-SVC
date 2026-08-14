"""
Database engine, session management, and schema lifecycle utilities.
Supports SQLite (local file or in-memory) and PostgreSQL.
"""

import logging
import os
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.database.models import Base

logger = logging.getLogger(__name__)

# Default database: SQLite database file in data/ directory
DEFAULT_SQLITE_PATH = Path("data") / "client_finder.db"
DEFAULT_DB_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_SQLITE_PATH}")


def get_db_url() -> str:
    """Retrieve database connection URL from environment or return default SQLite."""
    return os.getenv("DATABASE_URL", DEFAULT_DB_URL)


def get_engine(
    db_url: str | None = None,
    echo: bool = False,
    pool_pre_ping: bool = True,
    **kwargs: Any,
) -> Engine:
    """
    Create a SQLAlchemy Engine.
    For SQLite, automatically enables connect_args={'check_same_thread': False}
    and creates the target directory if needed.
    """
    url = db_url or get_db_url()

    # Ensure parent directory exists if using local SQLite file
    if url.startswith("sqlite:///") and not url.startswith("sqlite:///:memory:"):
        db_path = url.replace("sqlite:///", "")
        path_obj = Path(db_path)
        if path_obj.parent:
            path_obj.parent.mkdir(parents=True, exist_ok=True)

    connect_args = kwargs.pop("connect_args", {})
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    return create_engine(
        url,
        echo=echo,
        pool_pre_ping=pool_pre_ping,
        connect_args=connect_args,
        **kwargs,
    )


def init_db(engine: Engine | None = None, db_url: str | None = None) -> None:
    """Create all database tables defined in SQLAlchemy Base metadata."""
    target_engine = engine or get_engine(db_url=db_url)
    logger.info("Initializing database schema on %s...", target_engine.url)
    Base.metadata.create_all(bind=target_engine)
    logger.info("Database schema initialized successfully.")


def drop_db(engine: Engine | None = None, db_url: str | None = None) -> None:
    """Drop all database tables. Primarily used for test teardown."""
    target_engine = engine or get_engine(db_url=db_url)
    Base.metadata.drop_all(bind=target_engine)


def get_session_factory(
    engine: Engine | None = None,
    db_url: str | None = None,
) -> sessionmaker[Session]:
    """Create a session factory bound to the provided or default engine."""
    target_engine = engine or get_engine(db_url=db_url)
    return sessionmaker(
        bind=target_engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )


@contextmanager
def get_db_session(
    factory_or_engine: sessionmaker[Session] | Engine | None = None,
    engine: Engine | None = None,
    session_factory: sessionmaker[Session] | None = None,
    db_url: str | None = None,
) -> Generator[Session, None, None]:
    """
    Context manager for database sessions with automatic commit on exit,
    rollback on exception, and session closing.

    Accepts a sessionmaker instance, an Engine, or creates a default session.
    """
    target = factory_or_engine or session_factory or engine
    if isinstance(target, sessionmaker):
        session = target()
    elif isinstance(target, Engine):
        session = get_session_factory(engine=target)()
    else:
        session = get_session_factory(db_url=db_url)()

    try:
        yield session
        session.commit()
    except Exception as exc:
        session.rollback()
        logger.error("Database transaction rolled back due to error: %s", exc)
        raise
    finally:
        session.close()
