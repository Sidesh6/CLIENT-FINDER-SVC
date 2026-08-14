"""
Database connection, session factory, and dependency injection helper for FastAPI.
"""

from collections.abc import Generator
from typing import Any

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from src.database.database import (
    DEFAULT_DB_URL,
    get_db_session,
    get_db_url,
    get_engine,
    get_session_factory,
    init_db,
)
from src.database.models import Base

# Default singleton engine and session factory
engine: Engine = get_engine()
SessionLocal: sessionmaker[Session] = get_session_factory(engine)


def get_db() -> Generator[Session, Any, None]:
    """FastAPI dependency yielding a managed database session."""
    with get_db_session(session_factory=SessionLocal) as session:
        yield session


__all__ = [
    "Base",
    "DEFAULT_DB_URL",
    "SessionLocal",
    "engine",
    "get_db",
    "get_db_session",
    "get_db_url",
    "get_engine",
    "get_session_factory",
    "init_db",
]
