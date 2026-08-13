import json
import logging
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.database.models import CollectionRunRecord, ProjectRecord
from src.models.project import Project
from src.processors.deduplicator import compute_content_hash, compute_url_hash

logger = logging.getLogger(__name__)


class ProjectRepository:
    """
    Repository providing CRUD and querying operations for ProjectRecord database entities.
    """

    def __init__(self, session: Session):
        self.session = session

    def get_all_url_hashes(self) -> set[str]:
        """Fetch all unique URL hashes currently in the database."""
        stmt = select(ProjectRecord.url_hash)
        results = self.session.scalars(stmt).all()
        return set(results)

    def get_all_content_hashes(self) -> set[str]:
        """Fetch all unique content hashes currently in the database."""
        stmt = select(ProjectRecord.content_hash)
        results = self.session.scalars(stmt).all()
        return set(results)

    def get_by_id(self, project_id: int) -> ProjectRecord | None:
        """Find a project by its primary key ID."""
        return self.session.get(ProjectRecord, project_id)

    def get_by_url_hash(self, url_hash: str) -> ProjectRecord | None:
        """Find a project by its unique URL hash."""
        stmt = select(ProjectRecord).where(ProjectRecord.url_hash == url_hash)
        return self.session.scalars(stmt).first()

    def save_project(self, project: Project) -> ProjectRecord | None:
        """
        Save a single Project model to the database.
        Returns the created record or None if it is a duplicate.
        """
        url_str = str(project.source_url)
        url_hash = compute_url_hash(url_str)
        content_hash = compute_content_hash(project.title, project.description)

        # Check for duplicate URL or content hash
        existing = self.session.scalars(
            select(ProjectRecord).where(
                (ProjectRecord.url_hash == url_hash) | (ProjectRecord.content_hash == content_hash)
            )
        ).first()

        if existing:
            logger.debug("Project already exists in DB (ID: %s)", existing.id)
            return None

        record = ProjectRecord(
            title=project.title,
            description=project.description,
            source=project.source,
            source_url=url_str,
            url_hash=url_hash,
            content_hash=content_hash,
            client_name=project.client_name,
            budget=project.budget,
            currency=project.currency,
            project_type=project.project_type,
            skills_json=json.dumps(project.skills or []),
            score=project.score,
            status="DISCOVERED",
        )
        self.session.add(record)
        self.session.flush()
        return record

    def save_many(self, projects: list[Project]) -> tuple[list[ProjectRecord], int]:
        """
        Save a batch of validated Project models, automatically skipping duplicates.

        Returns:
            Tuple of (list of newly saved ProjectRecords, count of skipped duplicates)
        """
        if not projects:
            return [], 0

        existing_urls = self.get_all_url_hashes()
        existing_contents = self.get_all_content_hashes()

        saved_records: list[ProjectRecord] = []
        duplicate_count = 0

        for project in projects:
            url_str = str(project.source_url)
            url_hash = compute_url_hash(url_str)
            content_hash = compute_content_hash(project.title, project.description)

            if url_hash in existing_urls or content_hash in existing_contents:
                duplicate_count += 1
                continue

            record = ProjectRecord(
                title=project.title,
                description=project.description,
                source=project.source,
                source_url=url_str,
                url_hash=url_hash,
                content_hash=content_hash,
                client_name=project.client_name,
                budget=project.budget,
                currency=project.currency,
                project_type=project.project_type,
                skills_json=json.dumps(project.skills or []),
                score=project.score,
                status="DISCOVERED",
            )
            self.session.add(record)
            saved_records.append(record)
            existing_urls.add(url_hash)
            existing_contents.add(content_hash)

        self.session.flush()
        logger.info(
            "Batch save: %d new projects stored, %d duplicates skipped",
            len(saved_records),
            duplicate_count,
        )
        return saved_records, duplicate_count

    def list_projects(
        self,
        limit: int = 50,
        offset: int = 0,
        source: str | None = None,
        min_score: float | None = None,
    ) -> list[ProjectRecord]:
        """Query projects with optional filtering by source or minimum score."""
        stmt = select(ProjectRecord)
        if source:
            stmt = stmt.where(ProjectRecord.source == source)
        if min_score is not None:
            stmt = stmt.where(ProjectRecord.score >= min_score)

        stmt = stmt.order_by(ProjectRecord.created_at.desc()).offset(offset).limit(limit)
        return list(self.session.scalars(stmt).all())

    def count(self, source: str | None = None) -> int:
        """Count total project records in the database."""
        stmt = select(func.count(ProjectRecord.id))
        if source:
            stmt = stmt.where(ProjectRecord.source == source)
        return self.session.scalar(stmt) or 0


class CollectionRunRepository:
    """
    Repository for logging and querying collector execution history.
    """

    def __init__(self, session: Session):
        self.session = session

    def start_run(self, source_name: str) -> CollectionRunRecord:
        """Record the start of a collection run."""
        run = CollectionRunRecord(
            source_name=source_name,
            started_at=datetime.now(UTC),
            status="RUNNING",
        )
        self.session.add(run)
        self.session.flush()
        return run

    def complete_run(
        self,
        run_id: int,
        items_collected: int,
        items_saved: int,
        duplicates_skipped: int,
        status: str = "SUCCESS",
        error_message: str | None = None,
    ) -> CollectionRunRecord | None:
        """Record the completion details of a collection run."""
        run = self.session.get(CollectionRunRecord, run_id)
        if not run:
            return None

        run.completed_at = datetime.now(UTC)
        run.items_collected = items_collected
        run.items_saved = items_saved
        run.duplicates_skipped = duplicates_skipped
        run.status = status
        run.error_message = error_message
        self.session.flush()
        return run

    def get_recent_runs(self, limit: int = 10) -> list[CollectionRunRecord]:
        """Fetch the most recent collection runs."""
        stmt = (
            select(CollectionRunRecord).order_by(CollectionRunRecord.started_at.desc()).limit(limit)
        )
        return list(self.session.scalars(stmt).all())
