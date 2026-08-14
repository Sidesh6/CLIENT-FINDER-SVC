"""
Repository pattern implementations for database models.
Provides transactional query and mutation interfaces for Projects, Sources, Opportunities, and CollectionRuns.
"""

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from src.database.models import (
    ApplicationModel,
    ApplicationStatus,
    CollectionRunRecord,
    OpportunityModel,
    ProjectModel,
    SourceModel,
    compute_content_hash,
    compute_url_hash,
    normalize_url,
)
from src.models.project import Project

logger = logging.getLogger(__name__)


class SourceRepository:
    """
    Repository for managing project sources.
    """

    def __init__(self, session: Session | None = None):
        self.session = session

    def _get_session(self, session: Session | None) -> Session:
        s = session or self.session
        if s is None:
            raise ValueError("A valid database session must be provided.")
        return s

    def get_by_id(self, source_id: int, session: Session | None = None) -> SourceModel | None:
        """Fetch a source by its primary key ID."""
        sess = self._get_session(session)
        return sess.get(SourceModel, source_id)

    def get_by_name(self, name: str, session: Session | None = None) -> SourceModel | None:
        """Fetch a source by its unique name."""
        sess = self._get_session(session)
        stmt = select(SourceModel).where(SourceModel.name == name)
        return sess.scalars(stmt).first()

    def get_or_create(
        self,
        name: str,
        source_type: str = "api",
        session: Session | None = None,
        base_url: str | None = None,
        collection_interval: int = 3600,
    ) -> SourceModel:
        """
        Retrieve an existing source or create a new one if it does not exist.
        """
        sess = self._get_session(session)
        source = self.get_by_name(name, session=sess)
        if source is not None:
            return source

        source = SourceModel(
            name=name,
            type=source_type,
            base_url=base_url,
            collection_interval=collection_interval,
            enabled=True,
        )
        sess.add(source)
        sess.flush()
        return source

    def list_sources(
        self, session: Session | None = None, enabled_only: bool = False
    ) -> list[SourceModel]:
        """List all configured sources."""
        sess = self._get_session(session)
        stmt = select(SourceModel)
        if enabled_only:
            stmt = stmt.where(SourceModel.enabled.is_(True))
        return list(sess.scalars(stmt).all())

    def set_enabled(
        self, source_id: int, enabled: bool, session: Session | None = None
    ) -> SourceModel | None:
        """Enable or disable a specific source."""
        sess = self._get_session(session)
        source = self.get_by_id(source_id, session=sess)
        if source:
            source.enabled = enabled
            sess.flush()
        return source


class ProjectRepository:
    """
    Repository for managing project opportunities, deduplication, and querying.
    """

    def __init__(self, session: Session | None = None):
        self.session = session

    def _get_session(self, session: Session | None) -> Session:
        s = session or self.session
        if s is None:
            raise ValueError("A valid database session must be provided.")
        return s

    def is_duplicate(
        self,
        url: str,
        content_hash: str | None = None,
        session: Session | None = None,
    ) -> bool:
        """
        Check if a project already exists by exact URL, normalized URL, or content hash.
        """
        sess = self._get_session(session)
        norm_url = normalize_url(url)
        u_hash = compute_url_hash(url)

        stmt = select(ProjectModel.id).where(
            or_(
                ProjectModel.source_url == url,
                ProjectModel.source_url == norm_url,
                ProjectModel.source_url == f"{norm_url}/",
                ProjectModel.url_hash == u_hash,
            )
        )
        if sess.scalars(stmt).first() is not None:
            return True

        if content_hash:
            hash_stmt = select(ProjectModel.id).where(ProjectModel.content_hash == content_hash)
            if sess.scalars(hash_stmt).first() is not None:
                return True

        return False

    def get_by_id(self, project_id: int, session: Session | None = None) -> ProjectModel | None:
        """Fetch project opportunity by its primary key ID."""
        sess = self._get_session(session)
        return sess.get(ProjectModel, project_id)

    def get_by_url(self, url: str, session: Session | None = None) -> ProjectModel | None:
        """Fetch project opportunity by exact or normalized source URL."""
        sess = self._get_session(session)
        norm_url = normalize_url(url)
        u_hash = compute_url_hash(url)
        stmt = select(ProjectModel).where(
            or_(
                ProjectModel.source_url == url,
                ProjectModel.source_url == norm_url,
                ProjectModel.source_url == f"{norm_url}/",
                ProjectModel.url_hash == u_hash,
            )
        )
        return sess.scalars(stmt).first()

    def get_by_url_hash(self, url_hash: str, session: Session | None = None) -> ProjectModel | None:
        """Find a project by its unique URL hash."""
        sess = self._get_session(session)
        stmt = select(ProjectModel).where(ProjectModel.url_hash == url_hash)
        return sess.scalars(stmt).first()

    def get_by_content_hash(
        self, content_hash: str, session: Session | None = None
    ) -> ProjectModel | None:
        """Fetch project opportunity by content hash."""
        sess = self._get_session(session)
        stmt = select(ProjectModel).where(ProjectModel.content_hash == content_hash)
        return sess.scalars(stmt).first()

    def get_by_external_id(
        self, source_name: str, external_id: str, session: Session | None = None
    ) -> ProjectModel | None:
        """Fetch project opportunity by source name and external identifier."""
        sess = self._get_session(session)
        stmt = select(ProjectModel).where(
            ProjectModel.source == source_name,
            ProjectModel.external_id == external_id,
        )
        return sess.scalars(stmt).first()

    def get_all_url_hashes(self, session: Session | None = None) -> set[str]:
        """Fetch all unique URL hashes currently in the database."""
        sess = self._get_session(session)
        stmt = select(ProjectModel.url_hash)
        return set(sess.scalars(stmt).all())

    def get_all_content_hashes(self, session: Session | None = None) -> set[str]:
        """Fetch all unique content hashes currently in the database."""
        sess = self._get_session(session)
        stmt = select(ProjectModel.content_hash)
        return set(sess.scalars(stmt).all())

    def add(
        self,
        project: Project | ProjectModel | dict[str, Any],
        session: Session | None = None,
        source_id: int | None = None,
        external_id: str | None = None,
        raw_data: dict[str, Any] | None = None,
        status: str | None = None,
    ) -> ProjectModel:
        """
        Persist a single project opportunity.
        """
        sess = self._get_session(session)

        if isinstance(project, ProjectModel):
            model = project
        elif isinstance(project, Project):
            model = ProjectModel.from_pydantic(
                project,
                source_id=source_id,
                external_id=external_id,
                raw_data=raw_data,
                status=status or "DISCOVERED",
            )
        elif isinstance(project, dict):
            url_str = str(project.get("source_url", project.get("url", "")))
            u_hash = project.get("url_hash", compute_url_hash(url_str))
            c_hash = project.get(
                "content_hash",
                compute_content_hash(project.get("title", ""), project.get("description", "")),
            )
            model = ProjectModel(
                source_id=source_id or project.get("source_id"),
                source=project.get("source", project.get("source_name", "Unknown")),
                external_id=external_id or project.get("external_id"),
                title=project["title"],
                description=project["description"],
                source_url=url_str,
                url_hash=u_hash,
                content_hash=c_hash,
                client_name=project.get("client_name"),
                budget=project.get("budget"),
                currency=project.get("currency"),
                project_type=project.get("project_type"),
                skills=project.get("skills", []),
                status=status or project.get("status") or "DISCOVERED",
                score=project.get("score"),
                posted_at=project.get("posted_at", project.get("project_start_date")),
                deadline=project.get("deadline", project.get("project_end_date")),
                raw_data=raw_data or project.get("raw_data"),
            )
        else:
            raise TypeError(f"Unsupported project type: {type(project)}")

        sess.add(model)
        sess.flush()
        return model

    def save_project(
        self,
        project: Project,
        session: Session | None = None,
    ) -> ProjectModel | None:
        """
        Save a single project if not duplicate. Returns saved model or None.
        """
        sess = self._get_session(session)
        url_str = str(project.source_url)
        c_hash = compute_content_hash(project.title, project.description)

        if self.is_duplicate(url_str, c_hash, session=sess):
            logger.debug("Project '%s' is a duplicate, skipping", project.title)
            return None

        return self.add(project, session=sess)

    def add_many(
        self,
        projects: list[Project | ProjectModel | dict[str, Any]],
        session: Session | None = None,
        skip_duplicates: bool = True,
        source_id: int | None = None,
    ) -> list[ProjectModel]:
        """
        Persist a batch of projects, optionally skipping duplicates.
        """
        sess = self._get_session(session)
        persisted: list[ProjectModel] = []

        for item in projects:
            if isinstance(item, Project):
                url = str(item.source_url)
                c_hash = compute_content_hash(item.title, item.description)
            elif isinstance(item, ProjectModel):
                url = item.source_url
                c_hash = item.content_hash
            elif isinstance(item, dict):
                url = str(item.get("source_url", item.get("url", "")))
                c_hash = item.get(
                    "content_hash",
                    compute_content_hash(item.get("title", ""), item.get("description", "")),
                )
            else:
                continue

            if skip_duplicates and self.is_duplicate(url, c_hash, session=sess):
                continue

            persisted_model = self.add(item, session=sess, source_id=source_id)
            persisted.append(persisted_model)

        return persisted

    def save_many(
        self,
        projects: list[Project],
        session: Session | None = None,
    ) -> tuple[list[ProjectModel], int]:
        """
        Save a list of Pydantic projects, skipping duplicates.
        Returns:
            Tuple of (saved_models_list, duplicate_count)
        """
        sess = self._get_session(session)
        saved: list[ProjectModel] = []
        skipped = 0

        for proj in projects:
            record = self.save_project(proj, session=sess)
            if record is not None:
                saved.append(record)
            else:
                skipped += 1

        return saved, skipped

    def list_projects(
        self,
        session: Session | None = None,
        limit: int = 50,
        offset: int = 0,
        status: str | None = None,
        source_name: str | None = None,
        source: str | None = None,
        min_score: float | None = None,
        order_by_score: bool = False,
    ) -> list[ProjectModel]:
        """
        List projects with filtering and pagination.
        """
        sess = self._get_session(session)
        stmt = select(ProjectModel)

        filter_source = source_name or source
        if status:
            stmt = stmt.where(ProjectModel.status == status)
        if filter_source:
            stmt = stmt.where(ProjectModel.source == filter_source)
        if min_score is not None:
            stmt = stmt.where(ProjectModel.score >= min_score)

        if order_by_score:
            stmt = stmt.order_by(ProjectModel.score.desc().nullslast())
        else:
            stmt = stmt.order_by(ProjectModel.created_at.desc())

        stmt = stmt.limit(limit).offset(offset)
        return list(sess.scalars(stmt).all())

    def update_status(
        self, project_id: int, status: str, session: Session | None = None
    ) -> ProjectModel | None:
        """Update the lifecycle status of a project."""
        sess = self._get_session(session)
        project = self.get_by_id(project_id, session=sess)
        if project:
            project.status = status
            sess.flush()
        return project

    def update_score(
        self, project_id: int, score: float, session: Session | None = None
    ) -> ProjectModel | None:
        """Update the opportunity score of a project."""
        sess = self._get_session(session)
        project = self.get_by_id(project_id, session=sess)
        if project:
            project.score = score
            sess.flush()
        return project

    def delete(self, project_id: int, session: Session | None = None) -> bool:
        """Delete a project opportunity by ID."""
        sess = self._get_session(session)
        project = self.get_by_id(project_id, session=sess)
        if project:
            sess.delete(project)
            sess.flush()
            return True
        return False

    def count(
        self,
        session: Session | None = None,
        status: str | None = None,
        source_name: str | None = None,
        source: str | None = None,
    ) -> int:
        """Count total projects matching optional filters."""
        sess = self._get_session(session)
        stmt = select(func.count(ProjectModel.id))

        filter_source = source_name or source
        if status:
            stmt = stmt.where(ProjectModel.status == status)
        if filter_source:
            stmt = stmt.where(ProjectModel.source == filter_source)

        result = sess.scalar(stmt)
        return result or 0


class OpportunityRepository:
    """
    Repository for storing and querying scored opportunity breakdowns.
    """

    def __init__(self, session: Session | None = None):
        self.session = session

    def _get_session(self, session: Session | None) -> Session:
        s = session or self.session
        if s is None:
            raise ValueError("A valid database session must be provided.")
        return s

    def get_by_project_id(
        self, project_id: int, session: Session | None = None
    ) -> OpportunityModel | None:
        """Retrieve opportunity score record for a project."""
        sess = self._get_session(session)
        stmt = select(OpportunityModel).where(OpportunityModel.project_id == project_id)
        return sess.scalars(stmt).first()

    def create_or_update(
        self,
        project_id: int,
        overall_score: float,
        session: Session | None = None,
        skill_match_score: float | None = None,
        budget_score: float | None = None,
        client_score: float | None = None,
        competition_score: float | None = None,
        complexity_score: float | None = None,
        freshness_score: float | None = None,
        win_probability: float | None = None,
        explanation: str | None = None,
    ) -> OpportunityModel:
        """
        Create a new opportunity evaluation record or update existing for a project.
        """
        sess = self._get_session(session)
        opportunity = self.get_by_project_id(project_id, session=sess)

        if opportunity is None:
            opportunity = OpportunityModel(
                project_id=project_id,
                overall_score=overall_score,
                skill_match_score=skill_match_score,
                budget_score=budget_score,
                client_score=client_score,
                competition_score=competition_score,
                complexity_score=complexity_score,
                freshness_score=freshness_score,
                win_probability=win_probability,
                explanation=explanation,
            )
            sess.add(opportunity)
        else:
            opportunity.overall_score = overall_score
            opportunity.skill_match_score = skill_match_score
            opportunity.budget_score = budget_score
            opportunity.client_score = client_score
            opportunity.competition_score = competition_score
            opportunity.complexity_score = complexity_score
            opportunity.freshness_score = freshness_score
            opportunity.win_probability = win_probability
            opportunity.explanation = explanation

        # Synchronize score with parent project
        proj_repo = ProjectRepository(sess)
        proj_repo.update_score(project_id, overall_score, session=sess)

        sess.flush()
        return opportunity

    def list_top_opportunities(
        self,
        session: Session | None = None,
        limit: int = 20,
        min_score: float = 0.0,
    ) -> list[OpportunityModel]:
        """List highest-scored opportunities."""
        sess = self._get_session(session)
        stmt = (
            select(OpportunityModel)
            .where(OpportunityModel.overall_score >= min_score)
            .order_by(OpportunityModel.overall_score.desc())
            .limit(limit)
        )
        return list(sess.scalars(stmt).all())


class CollectionRunRepository:
    """
    Repository for managing scraper/collector run logs and metrics.
    """

    def __init__(self, session: Session | None = None):
        self.session = session

    def _get_session(self, session: Session | None) -> Session:
        s = session or self.session
        if s is None:
            raise ValueError("A valid database session must be provided.")
        return s

    def start_run(self, source: str, session: Session | None = None) -> CollectionRunRecord:
        """Start a new collector run and log initial record."""
        sess = self._get_session(session)
        run = CollectionRunRecord(source=source, status="RUNNING")
        sess.add(run)
        sess.flush()
        return run

    def complete_run(
        self,
        run_id: int,
        items_collected: int = 0,
        items_saved: int = 0,
        duplicates_skipped: int = 0,
        status: str = "SUCCESS",
        session: Session | None = None,
    ) -> CollectionRunRecord | None:
        """Mark collection run as completed successfully."""
        sess = self._get_session(session)
        run = sess.get(CollectionRunRecord, run_id)
        if run:
            run.status = status
            run.items_collected = items_collected
            run.items_saved = items_saved
            run.duplicates_skipped = duplicates_skipped
            run.completed_at = datetime.now(UTC)
            sess.flush()
        return run

    def fail_run(
        self, run_id: int, error_message: str, session: Session | None = None
    ) -> CollectionRunRecord | None:
        """Mark collection run as failed with error details."""
        sess = self._get_session(session)
        run = sess.get(CollectionRunRecord, run_id)
        if run:
            run.status = "FAILED"
            run.error_message = error_message
            run.completed_at = datetime.now(UTC)
            sess.flush()
        return run

    def get_by_id(self, run_id: int, session: Session | None = None) -> CollectionRunRecord | None:
        """Fetch collection run record by ID."""
        sess = self._get_session(session)
        return sess.get(CollectionRunRecord, run_id)

    def list_recent_runs(
        self, limit: int = 20, session: Session | None = None
    ) -> list[CollectionRunRecord]:
        """List most recent collection runs."""
        sess = self._get_session(session)
        stmt = (
            select(CollectionRunRecord).order_by(CollectionRunRecord.started_at.desc()).limit(limit)
        )
        return list(sess.scalars(stmt).all())

    def create_run(
        self,
        source_name: str,
        projects_found: int = 0,
        new_projects: int = 0,
        duration_seconds: float = 0.0,
        status: str = "SUCCESS",
        session: Session | None = None,
    ) -> CollectionRunRecord:
        """Create a completed run record directly."""
        sess = self._get_session(session)
        run = CollectionRunRecord(
            source=source_name,
            status=status,
            items_collected=projects_found,
            items_saved=new_projects,
            duplicates_skipped=max(0, projects_found - new_projects),
            completed_at=datetime.now(UTC),
        )
        sess.add(run)
        sess.flush()
        return run

    def get_recent_runs(
        self, limit: int = 20, session: Session | None = None
    ) -> list[CollectionRunRecord]:
        """Alias for list_recent_runs."""
        return self.list_recent_runs(limit=limit, session=session)


class ApplicationRepository:
    """
    Repository for managing application submissions, status lifecycle transitions, and revenue outcomes.
    """

    def __init__(self, session: Session | None = None):
        self.session = session

    def _get_session(self, session: Session | None) -> Session:
        s = session or self.session
        if s is None:
            raise ValueError("A valid database session must be provided.")
        return s

    def create(
        self,
        project_id: int,
        status: str = ApplicationStatus.APPLIED.value,
        proposed_budget: float | None = None,
        currency: str = "USD",
        proposal_text: str | None = None,
        pitch_angle: str | None = None,
        notes: str | None = None,
        session: Session | None = None,
    ) -> ApplicationModel:
        """
        Record a new application and synchronize the parent project's status.
        """
        sess = self._get_session(session)

        # Check if application already exists for this project
        existing = sess.scalar(
            select(ApplicationModel).where(ApplicationModel.project_id == project_id)
        )
        if existing:
            existing.status = status
            if proposed_budget is not None:
                existing.proposed_budget = proposed_budget
            if currency:
                existing.currency = currency
            if proposal_text:
                existing.proposal_text = proposal_text
            if pitch_angle:
                existing.pitch_angle = pitch_angle
            if notes:
                existing.notes = notes
            sess.flush()
            return existing

        app = ApplicationModel(
            project_id=project_id,
            status=status,
            applied_at=datetime.now(UTC),
            proposed_budget=proposed_budget,
            currency=currency,
            proposal_text=proposal_text,
            pitch_angle=pitch_angle,
            notes=notes,
        )
        sess.add(app)

        # Synchronize project status to APPLIED
        project = sess.get(ProjectModel, project_id)
        if project:
            project.status = "APPLIED"

        sess.flush()
        return app

    def get_by_id(self, app_id: int, session: Session | None = None) -> ApplicationModel | None:
        """Fetch application record by ID."""
        sess = self._get_session(session)
        return sess.get(ApplicationModel, app_id)

    def get_by_project_id(
        self, project_id: int, session: Session | None = None
    ) -> ApplicationModel | None:
        """Fetch application record for a given project ID."""
        sess = self._get_session(session)
        return sess.scalar(
            select(ApplicationModel).where(ApplicationModel.project_id == project_id)
        )

    def list_applications(
        self,
        status: str | None = None,
        pitch_angle: str | None = None,
        min_revenue: float | None = None,
        limit: int = 50,
        offset: int = 0,
        session: Session | None = None,
    ) -> list[ApplicationModel]:
        """List applications with optional status, pitch angle, and revenue filters."""
        sess = self._get_session(session)
        stmt = select(ApplicationModel)

        if status:
            stmt = stmt.where(ApplicationModel.status == status)
        if pitch_angle:
            stmt = stmt.where(ApplicationModel.pitch_angle == pitch_angle)
        if min_revenue is not None:
            stmt = stmt.where(ApplicationModel.final_revenue >= min_revenue)

        stmt = stmt.order_by(ApplicationModel.applied_at.desc()).offset(offset).limit(limit)
        return list(sess.scalars(stmt).all())

    def update_status(
        self,
        app_id: int,
        new_status: str,
        client_feedback: str | None = None,
        final_revenue: float | None = None,
        notes: str | None = None,
        session: Session | None = None,
    ) -> ApplicationModel | None:
        """
        Transition application lifecycle status and record outcome timestamps.
        """
        sess = self._get_session(session)
        app = sess.get(ApplicationModel, app_id)
        if not app:
            return None

        app.status = new_status
        now = datetime.now(UTC)

        if new_status == ApplicationStatus.CLIENT_REPLIED.value and not app.response_at:
            app.response_at = now
        elif new_status == ApplicationStatus.INTERVIEW.value:
            if not app.response_at:
                app.response_at = now
            if not app.interview_at:
                app.interview_at = now
        elif new_status in (
            ApplicationStatus.WON.value,
            ApplicationStatus.LOST.value,
            ApplicationStatus.CANCELLED.value,
            ApplicationStatus.COMPLETED.value,
        ):
            app.closed_at = now

        if client_feedback is not None:
            app.client_feedback = client_feedback
        if final_revenue is not None:
            app.final_revenue = final_revenue
        if notes is not None:
            app.notes = notes

        sess.flush()
        return app

    def delete(self, app_id: int, session: Session | None = None) -> bool:
        """Delete an application record."""
        sess = self._get_session(session)
        app = sess.get(ApplicationModel, app_id)
        if app:
            sess.delete(app)
            sess.flush()
            return True
        return False

    def count_by_status(self, session: Session | None = None) -> dict[str, int]:
        """Aggregate counts of applications across all lifecycle states."""
        sess = self._get_session(session)
        stmt = select(ApplicationModel.status, func.count(ApplicationModel.id)).group_by(
            ApplicationModel.status
        )
        rows = sess.execute(stmt).all()
        return dict(rows)  # type: ignore[arg-type]
