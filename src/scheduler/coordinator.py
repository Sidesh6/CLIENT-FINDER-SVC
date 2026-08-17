"""
Automated Pipeline Coordinator.
Orchestrates collection, cleaning, extraction, persistence, deduplication, scoring, and notification dispatch.
"""

import logging
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, cast

from src.ai.extractor import ProjectExtractor
from src.collectors.base_collector import BaseCollector
from src.collectors.registry import DEFAULT_REGISTRY, CollectorRegistry
from src.database.connection import SessionLocal
from src.database.models import ProjectModel
from src.database.repository import ProjectRepository
from src.models.profile import UserProfile, get_default_profile
from src.models.project import Project
from src.notifications.dispatcher import NotificationDispatcher
from src.processors.cleaner import clean_project_data
from src.scoring.engine import OpportunityScorer
from src.scoring.schemas import OpportunityScoreBreakdown

logger = logging.getLogger("PipelineCoordinator")


@dataclass
class PipelineRunResult:
    """Telemetry and execution metrics summary for a pipeline run."""

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
    sources_used: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    success: bool = True


class PipelineCoordinator:
    """
    Unified coordinator executing full harvest-to-notification cycles across active collectors.
    """

    def __init__(
        self,
        collectors: Sequence[BaseCollector] | None = None,
        registry: CollectorRegistry | None = None,
        extractor: ProjectExtractor | None = None,
        scorer: OpportunityScorer | None = None,
        dispatcher: NotificationDispatcher | None = None,
        default_profile: UserProfile | None = None,
    ):
        self.registry = registry or DEFAULT_REGISTRY
        self.collectors = list(collectors) if collectors is not None else None
        self.extractor = extractor or ProjectExtractor()
        self.default_profile = default_profile or get_default_profile()
        self.scorer = scorer or OpportunityScorer(default_profile=self.default_profile)
        self.dispatcher = dispatcher or NotificationDispatcher()

    def run_cycle(
        self,
        min_notification_score: float = 75.0,
        dry_run: bool = False,
        limit_per_collector: int = 10,
        profile: UserProfile | None = None,
        collectors: Sequence[BaseCollector] | None = None,
    ) -> PipelineRunResult:
        """
        Execute an end-to-end autonomous discovery, scoring, and notification cycle.
        """
        start_time = time.perf_counter()
        result = PipelineRunResult(started_at=datetime.now(UTC))
        active_profile = profile or self.default_profile

        if collectors is not None:
            active_collectors = list(collectors)
        elif self.collectors is not None:
            active_collectors = self.collectors
        else:
            active_collectors = self.registry.get_active_collectors()

        logger.info(
            "Starting automated pipeline cycle across %d collector(s)...", len(active_collectors)
        )

        raw_items: list[dict[str, Any]] = []

        # Step 1: Data Collection & Health Telemetry
        for col in active_collectors:
            col_name = getattr(col, "source_name", getattr(col, "name", str(col)))
            if col_name not in result.sources_used:
                result.sources_used.append(col_name)
            try:
                if hasattr(col, "max_projects"):
                    col.max_projects = limit_per_collector
                items = col.collect()
                logger.info("Collector '%s' retrieved %d items.", col_name, len(items))
                self.registry.record_success(col_name, len(items))
                raw_items.extend(items)
            except Exception as exc:
                err_msg = f"Collector '{col_name}' failed: {exc}"
                logger.error(err_msg)
                self.registry.record_failure(col_name, str(exc))
                result.errors.append(err_msg)

        result.collected_count = len(raw_items)

        if not raw_items:
            logger.info("No items harvested during this cycle.")
            result.completed_at = datetime.now(UTC)
            result.duration_seconds = time.perf_counter() - start_time
            return result

        # Step 2: Data Cleaning & Normalization
        cleaned_items: list[dict[str, Any]] = []
        for raw in raw_items:
            try:
                cleaned = clean_project_data(raw)
                if cleaned:
                    cleaned_items.append(cleaned)
            except Exception as exc:
                logger.warning("Cleaning item failed: %s", exc)

        result.cleaned_count = len(cleaned_items)

        # Step 3: Metadata Extraction & Enrichment
        enriched_projects: list[Project] = []
        for c_dict in cleaned_items:
            try:
                p_obj = self.extractor.extract(c_dict)
                enriched_projects.append(p_obj)
            except Exception as exc:
                logger.warning("Failed to extract/model project: %s", exc)

        if dry_run:
            logger.info(
                "Dry run requested. Skipping persistence, scoring, and notification dispatch."
            )
            result.completed_at = datetime.now(UTC)
            result.duration_seconds = time.perf_counter() - start_time
            return result

        # Step 4: Persistence & De-duplication
        scored_pairs: list[tuple[ProjectModel, OpportunityScoreBreakdown]] = []

        with SessionLocal() as session:
            repo = ProjectRepository(session)

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

            # Step 7: Auto-Sync Direct Freelance Leads to Excel & CSV
            try:
                from src.analytics.excel_exporter import GLOBAL_EXCEL_EXPORTER

                synced_count = GLOBAL_EXCEL_EXPORTER.export(min_score=0.0, direct_clients_only=True)
                print(f"[+] Auto-synced {synced_count} freelance clients into data/freelance_clients.xlsx")
            except Exception as exc:
                logger.warning("Auto-syncing to Excel spreadsheet failed: %s", exc)


        result.completed_at = datetime.now(UTC)
        result.duration_seconds = time.perf_counter() - start_time
        result.success = len(result.errors) == 0

        # Broadcast real-time cycle completion event
        try:
            from src.api.events import GLOBAL_EVENT_BROADCASTER, EventType

            GLOBAL_EVENT_BROADCASTER.broadcast_sync(
                event_type=EventType.CYCLE_COMPLETED,
                data={
                    "duration_seconds": round(result.duration_seconds, 2),
                    "collected_count": result.collected_count,
                    "new_saved": result.new_projects_saved,
                    "high_priority_count": result.high_priority_count,
                    "sources": result.sources_used,
                },
            )
        except Exception:
            pass


        logger.info(
            "Pipeline cycle completed in %.2fs across %s. Found: %d, Saved: %d, High-Priority: %d, Alerts: %d",
            result.duration_seconds,
            result.sources_used,
            result.collected_count,
            result.new_projects_saved,
            result.high_priority_count,
            result.notifications_sent,
        )

        return result
