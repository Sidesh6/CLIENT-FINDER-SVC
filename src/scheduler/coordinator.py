"""
Pipeline Coordinator executing the unified 8-step lead discovery, extraction, scoring, persistence, and alert lifecycle.
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, cast

from src.ai.extractor import ProjectExtractor
from src.collectors.base_collector import BaseCollector
from src.collectors.hackernews_collector import HackerNewsCollector
from src.database.connection import SessionLocal
from src.database.models import ProjectModel
from src.database.repository import CollectionRunRepository, ProjectRepository
from src.models.profile import UserProfile, get_default_profile
from src.models.project import Project
from src.notifications.channels.console import ConsoleNotifier
from src.notifications.dispatcher import NotificationDispatcher
from src.processors.cleaner import ProjectCleaner
from src.scoring.engine import OpportunityScorer
from src.scoring.schemas import OpportunityScoreBreakdown

logger = logging.getLogger("PipelineCoordinator")


@dataclass
class PipelineRunResult:
    """
    Telemetry and execution statistics from a single pipeline cycle.
    """

    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    duration_seconds: float = 0.0
    collected_count: int = 0
    cleaned_count: int = 0
    new_projects_saved: int = 0
    duplicates_skipped: int = 0
    opportunities_scored: int = 0
    high_priority_count: int = 0
    notifications_sent: int = 0
    errors: list[str] = field(default_factory=list)
    success: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert run result to dictionary format."""
        return {
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": round(self.duration_seconds, 2),
            "collected_count": self.collected_count,
            "cleaned_count": self.cleaned_count,
            "new_projects_saved": self.new_projects_saved,
            "duplicates_skipped": self.duplicates_skipped,
            "opportunities_scored": self.opportunities_scored,
            "high_priority_count": self.high_priority_count,
            "notifications_sent": self.notifications_sent,
            "errors": self.errors,
            "success": self.success,
        }


class PipelineCoordinator:
    """
    Coordinates and orchestrates the autonomous end-to-end client finder pipeline.
    """

    def __init__(
        self,
        collectors: list[BaseCollector] | None = None,
        cleaner: ProjectCleaner | None = None,
        extractor: ProjectExtractor | None = None,
        scorer: OpportunityScorer | None = None,
        dispatcher: NotificationDispatcher | None = None,
        default_profile: UserProfile | None = None,
    ):
        self.default_profile = default_profile or get_default_profile()
        self.collectors = (
            collectors if collectors is not None else [HackerNewsCollector(max_projects=15)]
        )
        self.cleaner = cleaner or ProjectCleaner()
        self.extractor = extractor or ProjectExtractor()
        self.scorer = scorer or OpportunityScorer(default_profile=self.default_profile)
        self.dispatcher = dispatcher or NotificationDispatcher(channels=[ConsoleNotifier()])

    def run_cycle(
        self,
        collectors: list[BaseCollector] | None = None,
        profile: UserProfile | None = None,
        min_notification_score: float = 75.0,
        dry_run: bool = False,
        limit_per_collector: int = 10,
    ) -> PipelineRunResult:
        """
        Execute an autonomous pipeline cycle across collectors.
        """
        active_profile = profile or self.default_profile
        active_collectors = collectors or self.collectors

        result = PipelineRunResult()
        start_time = time.perf_counter()

        logger.info(
            "Starting automated pipeline cycle across %d collector(s)...",
            len(active_collectors),
        )

        raw_items: list[dict[str, Any]] = []

        # Step 1: Data Collection
        for col in active_collectors:
            try:
                if hasattr(col, "max_projects"):
                    col.max_projects = limit_per_collector
                items = col.collect()
                logger.info("Collector '%s' retrieved %d items.", col.name, len(items))
                raw_items.extend(items)
            except Exception as exc:
                err_msg = f"Collector '{col.name}' failed: {exc}"
                logger.error(err_msg)
                result.errors.append(err_msg)

        result.collected_count = len(raw_items)

        if not raw_items:
            logger.info("No items harvested during this cycle.")
            result.completed_at = datetime.now(UTC)
            result.duration_seconds = time.perf_counter() - start_time
            return result

        # Step 2: Cleaning & Sanitization
        try:
            cleaned_items = self.cleaner.clean_many(raw_items)
            result.cleaned_count = len(cleaned_items)
        except Exception as exc:
            err_msg = f"Cleaning step failed: {exc}"
            logger.error(err_msg)
            result.errors.append(err_msg)
            cleaned_items = raw_items

        # Step 3: AI Requirement Extraction
        enriched_projects: list[Project] = []
        for item in cleaned_items:
            try:
                extracted = self.extractor.extract(item)
                enriched_projects.append(extracted)
            except Exception as exc:
                logger.warning("Extraction failed for item '%s': %s", item.get("title", ""), exc)
                # Fallback to basic Project construct
                try:
                    enriched_projects.append(
                        Project(
                            title=str(item.get("title", "Untitled Opportunity")),
                            description=str(item.get("description", "")),
                            source=str(item.get("source", "Unknown")),
                            source_url=item.get("source_url", "https://example.com"),
                        )
                    )
                except Exception:
                    pass

        if dry_run:
            logger.info(
                "Dry-run mode enabled: Skipping database persistence and notification dispatch."
            )
            result.completed_at = datetime.now(UTC)
            result.duration_seconds = time.perf_counter() - start_time
            return result

        # Step 4 & 5: Database Persistence & Opportunity Scoring
        saved_project_models: list[ProjectModel] = []
        scored_pairs: list[tuple[ProjectModel, OpportunityScoreBreakdown]] = []

        with SessionLocal() as session:
            repo = ProjectRepository(session)
            run_repo = CollectionRunRepository(session)

            # Persist projects
            saved_project_models = repo.add_many(
                cast(list[Project | ProjectModel | dict[str, Any]], enriched_projects)
            )
            result.new_projects_saved = len(saved_project_models)
            result.duplicates_skipped = len(enriched_projects) - len(saved_project_models)
            session.commit()

            # Score each newly saved project
            for pm in saved_project_models:
                p_obj = pm.to_pydantic()
                try:
                    opp_model = self.scorer.score_and_persist(
                        project_id=pm.id,
                        project=p_obj,
                        session=session,
                        profile=active_profile,
                    )
                    breakdown = OpportunityScoreBreakdown(
                        overall_score=opp_model.overall_score,
                        skill_match_score=opp_model.skill_match_score or 0.0,
                        budget_score=opp_model.budget_score or 0.0,
                        client_score=opp_model.client_score or 0.0,
                        competition_score=opp_model.competition_score or 0.0,
                        complexity_score=opp_model.complexity_score or 0.0,
                        freshness_score=opp_model.freshness_score or 0.0,
                        win_probability=opp_model.win_probability or 0.0,
                        explanation=opp_model.explanation or "",
                    )
                    scored_pairs.append((pm, breakdown))
                    result.opportunities_scored += 1
                    if breakdown.overall_score >= min_notification_score:
                        result.high_priority_count += 1
                except Exception as exc:
                    err_msg = f"Scoring failed for project ID {pm.id}: {exc}"
                    logger.error(err_msg)
                    result.errors.append(err_msg)

            # Step 6: Multi-Channel Notification Dispatch
            for pm, breakdown in scored_pairs:
                if breakdown.overall_score >= min_notification_score:
                    try:
                        p_obj = pm.to_pydantic()
                        dispatch_results = self.dispatcher.dispatch(
                            project=p_obj,
                            score_breakdown=breakdown,
                            min_score=min_notification_score,
                        )
                        sent = sum(1 for r in dispatch_results if r.success)
                        result.notifications_sent += sent
                    except Exception as exc:
                        logger.warning(
                            "Notification dispatch failed for project ID %d: %s", pm.id, exc
                        )

            # Step 7: Audit Collection Run
            try:
                run_repo.create_run(
                    source_name="PipelineCoordinator",
                    projects_found=result.collected_count,
                    new_projects=result.new_projects_saved,
                    duration_seconds=time.perf_counter() - start_time,
                    status="SUCCESS" if not result.errors else "PARTIAL",
                )
                session.commit()
            except Exception as exc:
                logger.warning("Failed to record collection run audit: %s", exc)

        result.completed_at = datetime.now(UTC)
        result.duration_seconds = time.perf_counter() - start_time
        result.success = len(result.errors) == 0

        logger.info(
            "Pipeline cycle completed in %.2fs. Found: %d, Saved: %d, High-Priority: %d, Alerts: %d",
            result.duration_seconds,
            result.collected_count,
            result.new_projects_saved,
            result.high_priority_count,
            result.notifications_sent,
        )

        return result
