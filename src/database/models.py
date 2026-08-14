"""
SQLAlchemy ORM models for Client Finder database.
Defines SourceModel, ProjectModel, OpportunityModel, and CollectionRunRecord entities.
"""

import hashlib
import json
from datetime import UTC, datetime
from typing import Any, Optional

from pydantic import HttpUrl
from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from src.models.project import Project


class Base(DeclarativeBase):
    """Base declarative class for all ORM models."""

    pass


def normalize_url(url: str) -> str:
    """
    Normalize a URL string by trimming whitespace and standardizing trailing slashes.
    """
    cleaned = url.strip()
    return cleaned.rstrip("/") if len(cleaned) > 8 else cleaned


def compute_content_hash(title: str, description: str) -> str:
    """
    Compute a deterministic SHA-256 hash from normalized title and description.
    Used for duplicate detection across project opportunities.

    Args:
        title: Project title
        description: Project description

    Returns:
        Hexadecimal SHA-256 digest string
    """
    normalized = f"{title.strip().lower()}|{description.strip().lower()}".encode()
    return hashlib.sha256(normalized).hexdigest()


def compute_url_hash(url: str) -> str:
    """Compute a SHA-256 hash of a normalized URL."""
    canonical_url = normalize_url(url)
    return hashlib.sha256(canonical_url.encode("utf-8")).hexdigest()


class SourceModel(Base):
    """
    Represents an external project source/platform (e.g. Hacker News, Upwork, RSS).
    """

    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False, default="api")
    base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    collection_interval: Mapped[int] = mapped_column(Integer, default=3600, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    projects: Mapped[list["ProjectModel"]] = relationship(
        "ProjectModel", back_populates="source_model", cascade="all, delete-orphan"
    )

    @property
    def is_active(self) -> bool:
        """Alias for enabled."""
        return self.enabled

    @property
    def source_type(self) -> str:
        """Alias for type."""
        return self.type

    def __repr__(self) -> str:
        return f"<SourceModel id={self.id} name='{self.name}' type='{self.type}' enabled={self.enabled}>"


class ProjectModel(Base):
    """
    Represents a discovered and normalized project opportunity.
    """

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[int | None] = mapped_column(
        ForeignKey("sources.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)

    title: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str] = mapped_column(String(1000), unique=True, index=True, nullable=False)
    url_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)

    client_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    budget: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str | None] = mapped_column(String(10), nullable=True)
    project_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    skills: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)

    status: Mapped[str] = mapped_column(
        String(50), default="DISCOVERED", index=True, nullable=False
    )
    score: Mapped[float | None] = mapped_column(Float, nullable=True)

    posted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    deadline: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    raw_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    source_model: Mapped[Optional["SourceModel"]] = relationship("SourceModel", back_populates="projects")
    opportunity: Mapped[Optional["OpportunityModel"]] = relationship(
        "OpportunityModel", back_populates="project", uselist=False, cascade="all, delete-orphan"
    )

    @property
    def source_name(self) -> str:
        """Alias returning source string attribute."""
        return self.source

    @property
    def skills_json(self) -> str:
        """JSON serialized representation of skills for compatibility."""
        return json.dumps(self.skills or [])

    def __repr__(self) -> str:
        return f"<ProjectModel id={self.id} title='{self.title[:30]}...' source='{self.source}' status='{self.status}'>"

    def to_pydantic(self) -> Project:
        """Convert ORM model to Pydantic Project model."""
        return Project(
            title=self.title,
            description=self.description,
            source=self.source_name,
            source_url=HttpUrl(self.source_url),
            client_name=self.client_name,
            budget=self.budget,
            currency=self.currency,
            project_type=self.project_type,
            skills=self.skills or [],
            project_start_date=self.posted_at,
            project_end_date=self.deadline,
            score=self.score,
        )

    @classmethod
    def from_pydantic(
        cls,
        project: Project,
        source_id: int | None = None,
        external_id: str | None = None,
        raw_data: dict[str, Any] | None = None,
        status: str = "DISCOVERED",
    ) -> "ProjectModel":
        """
        Create a ProjectModel instance from a Pydantic Project schema.
        Automatically calculates url_hash and content_hash.
        """
        u_hash = compute_url_hash(str(project.source_url))
        c_hash = compute_content_hash(project.title, project.description)
        return cls(
            source_id=source_id,
            source=project.source,
            external_id=external_id,
            title=project.title,
            description=project.description,
            source_url=str(project.source_url),
            url_hash=u_hash,
            content_hash=c_hash,
            client_name=project.client_name,
            budget=project.budget,
            currency=project.currency,
            project_type=project.project_type,
            skills=project.skills or [],
            status=status,
            score=project.score,
            posted_at=project.project_start_date,
            deadline=project.project_end_date,
            raw_data=raw_data,
        )


class OpportunityModel(Base):
    """
    Represents an evaluated and scored opportunity linked to a project.
    """

    __tablename__ = "opportunities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )

    skill_match_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    budget_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    client_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    competition_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    complexity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    freshness_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    win_probability: Mapped[float | None] = mapped_column(Float, nullable=True)

    overall_score: Mapped[float] = mapped_column(Float, index=True, nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    project: Mapped["ProjectModel"] = relationship("ProjectModel", back_populates="opportunity")

    def __repr__(self) -> str:
        return f"<OpportunityModel id={self.id} project_id={self.project_id} overall_score={self.overall_score}>"


class CollectionRunRecord(Base):
    """
    Tracks execution history and metrics for collector runs.
    """

    __tablename__ = "collection_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), default="RUNNING", nullable=False)
    items_collected: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    items_saved: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duplicates_skipped: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    @property
    def source_name(self) -> str:
        """Alias for source."""
        return self.source

    def __repr__(self) -> str:
        return f"<CollectionRunRecord id={self.id} source='{self.source}' status='{self.status}' saved={self.items_saved}>"


# Compatibility aliases
ProjectRecord = ProjectModel
SourceRecord = SourceModel
