"""
Autonomous background scheduler daemon and daily digest distribution service.
"""

import logging
import threading
import time
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.database.connection import SessionLocal
from src.database.models import ProjectModel
from src.models.profile import UserProfile, get_default_profile
from src.models.project import Project
from src.notifications.dispatcher import NotificationDispatcher
from src.notifications.schemas import NotificationResult
from src.scheduler.coordinator import PipelineCoordinator, PipelineRunResult
from src.scoring.schemas import OpportunityScoreBreakdown

logger = logging.getLogger("PipelineScheduler")


class PipelineScheduler:
    """
    Background daemon running periodic lead harvesting and automated digest dispatches.
    """

    def __init__(
        self,
        coordinator: PipelineCoordinator | None = None,
        harvest_interval_minutes: float = 15.0,
        digest_interval_hours: float = 24.0,
        min_notification_score: float = 75.0,
        default_profile: UserProfile | None = None,
    ):
        self.coordinator = coordinator or PipelineCoordinator()
        self.harvest_interval_minutes = harvest_interval_minutes
        self.digest_interval_hours = digest_interval_hours
        self.min_notification_score = min_notification_score
        self.default_profile = default_profile or get_default_profile()

        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._paused = False

        self._total_cycles = 0
        self._last_run_at: datetime | None = None
        self._last_digest_at: datetime | None = None
        self._last_result: PipelineRunResult | None = None

    def start(self) -> None:
        """Start the background scheduler thread."""
        if self.is_running():
            logger.warning("Scheduler daemon is already running.")
            return

        self._stop_event.clear()
        self._paused = False
        self._thread = threading.Thread(
            target=self._run_loop, name="PipelineSchedulerDaemon", daemon=True
        )
        self._thread.start()
        logger.info(
            "Scheduler daemon started. Harvest interval: %.1f min(s), Digest interval: %.1f hr(s).",
            self.harvest_interval_minutes,
            self.digest_interval_hours,
        )

    def stop(self, timeout: float = 5.0) -> None:
        """Stop the background scheduler daemon."""
        if not self.is_running():
            return

        logger.info("Stopping scheduler daemon...")
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)
        self._thread = None
        logger.info("Scheduler daemon stopped.")

    def pause(self) -> None:
        """Pause automated pipeline triggers without terminating the background thread."""
        self._paused = True
        logger.info("Scheduler daemon paused.")

    def resume(self) -> None:
        """Resume automated pipeline triggers."""
        self._paused = False
        logger.info("Scheduler daemon resumed.")

    def is_running(self) -> bool:
        """Check if background daemon thread is alive."""
        return self._thread is not None and self._thread.is_alive()

    def is_paused(self) -> bool:
        """Check if scheduler is currently paused."""
        return self._paused

    def trigger_cycle_now(self, dry_run: bool = False) -> PipelineRunResult:
        """Manually execute an immediate pipeline cycle."""
        logger.info("Executing immediate on-demand pipeline cycle...")
        result = self.coordinator.run_cycle(
            profile=self.default_profile,
            min_notification_score=self.min_notification_score,
            dry_run=dry_run,
        )
        self._last_run_at = datetime.now(UTC)
        self._last_result = result
        self._total_cycles += 1
        return result

    def send_daily_digest(
        self,
        profile: UserProfile | None = None,
        lookback_hours: int = 24,
        dispatcher: NotificationDispatcher | None = None,
    ) -> list[NotificationResult]:
        """
        Synthesize and dispatch a daily digest of top-scoring opportunities.
        """
        active_dispatcher = dispatcher or self.coordinator.dispatcher
        since_time = datetime.now(UTC) - timedelta(hours=lookback_hours)

        with SessionLocal() as session:
            query = (
                select(ProjectModel)
                .options(selectinload(ProjectModel.opportunity))
                .where(ProjectModel.created_at >= since_time)
                .order_by(ProjectModel.score.desc().nullslast())
                .limit(10)
            )
            projects = session.scalars(query).all()

            top_leads: list[tuple[Project | dict[str, Any], OpportunityScoreBreakdown]] = []
            for pm in projects:
                p_obj = pm.to_pydantic()
                opp = pm.opportunity
                if opp:
                    breakdown = OpportunityScoreBreakdown(
                        overall_score=opp.overall_score,
                        skill_match_score=opp.skill_match_score or 0.0,
                        budget_score=opp.budget_score or 0.0,
                        client_score=opp.client_score or 0.0,
                        competition_score=opp.competition_score or 0.0,
                        complexity_score=opp.complexity_score or 0.0,
                        freshness_score=opp.freshness_score or 0.0,
                        win_probability=opp.win_probability or 0.0,
                        explanation=opp.explanation or "",
                    )
                else:
                    breakdown = OpportunityScoreBreakdown(
                        overall_score=pm.score or 0.0,
                        skill_match_score=pm.score or 0.0,
                        budget_score=pm.score or 0.0,
                        client_score=100.0,
                        competition_score=50.0,
                        complexity_score=50.0,
                        freshness_score=100.0,
                        win_probability=50.0,
                        explanation="Digest Opportunity",
                    )
                top_leads.append((p_obj, breakdown))

        logger.info("Prepared daily digest with %d top lead(s). Dispatching...", len(top_leads))
        results = active_dispatcher.dispatch_digest(top_leads)
        self._last_digest_at = datetime.now(UTC)
        return results

    def get_status(self) -> dict[str, Any]:
        """Retrieve telemetry and operational status of scheduler daemon."""
        next_run = None
        if self.is_running() and not self._paused and self._last_run_at:
            next_run = (
                self._last_run_at + timedelta(minutes=self.harvest_interval_minutes)
            ).isoformat()

        return {
            "running": self.is_running(),
            "paused": self._paused,
            "harvest_interval_minutes": self.harvest_interval_minutes,
            "digest_interval_hours": self.digest_interval_hours,
            "min_notification_score": self.min_notification_score,
            "total_cycles_executed": self._total_cycles,
            "last_run_at": self._last_run_at.isoformat() if self._last_run_at else None,
            "last_digest_at": self._last_digest_at.isoformat() if self._last_digest_at else None,
            "next_run_at": next_run,
            "last_run_result": self._last_result.to_dict() if self._last_result else None,
        }

    def _run_loop(self) -> None:
        """Internal daemon loop sleeping in short increments to allow rapid responsive shutdown."""
        harvest_interval_sec = self.harvest_interval_minutes * 60
        last_harvest_time = 0.0

        while not self._stop_event.is_set():
            now = time.time()
            if not self._paused:
                # Check harvest timer
                if now - last_harvest_time >= harvest_interval_sec:
                    try:
                        self.trigger_cycle_now()
                        last_harvest_time = time.time()
                    except Exception as exc:
                        logger.error("Error during scheduled harvest cycle: %s", exc)

            # Sleep in short 1-second chunks for responsive cancellation
            self._stop_event.wait(timeout=1.0)
