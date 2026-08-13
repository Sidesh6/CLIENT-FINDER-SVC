import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy declarative models."""

    pass


class ProjectRecord(Base):
    """
    Persistent database record representing a discovered project opportunity.
    """

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    url_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)

    client_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    budget: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str | None] = mapped_column(String(10), nullable=True)
    project_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    skills_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)

    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="DISCOVERED", nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    @property
    def skills(self) -> list[str]:
        """Deserialize skills JSON array into a list of strings."""
        try:
            parsed = json.loads(self.skills_json)
            if isinstance(parsed, list):
                return [str(item) for item in parsed]
            return []
        except Exception:
            return []

    @skills.setter
    def skills(self, value: list[str]) -> None:
        """Serialize a list of strings into JSON format."""
        self.skills_json = json.dumps(value or [])

    def to_dict(self) -> dict[str, Any]:
        """Convert record to a dictionary representation."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "source": self.source,
            "source_url": self.source_url,
            "url_hash": self.url_hash,
            "content_hash": self.content_hash,
            "client_name": self.client_name,
            "budget": self.budget,
            "currency": self.currency,
            "project_type": self.project_type,
            "skills": self.skills,
            "score": self.score,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class SourceRecord(Base):
    """
    Persistent record representing a configured opportunity source (e.g. Hacker News).
    """

    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )


class CollectionRunRecord(Base):
    """
    Logs metadata for every collector execution run.
    """

    __tablename__ = "collection_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_name: Mapped[str] = mapped_column(String(100), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="RUNNING", nullable=False)
    items_collected: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    items_saved: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duplicates_skipped: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
