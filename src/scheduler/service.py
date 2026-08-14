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
from src.models.profile import UserProfile
from src.models.project import Project
from src.notifications.dispatcher import NotificationDispatcher
from src.notifications.schemas import NotificationResult
from src.scheduler.coordinator import PipelineCoordinator, PipelineRunResult
from src.scoring.schemas import OpportunityScoreBreakdown

logger = logging.getLogger("PipelineScheduler")


class PipelineScheduler:
    """
    Background worker daemon running periodic pipeline harvest cycles and daily digests.
    """

    def __init__(
        self,
        coordinator: PipelineCoordinator | None = None,
        harvest_interval_minutes: float = 15.0,
        digest_interval_hours: float = 24.0,
        min_notification_score: float = 75.0,
    ):
        self.coordinator = coordinator or PipelineCoordinator()
        self.harvest_interval_minutes = harvest_interval_minutes
        self.digest_interval_hours = digest_interval_hours
        self.min_notification_score = min_notification_score

        self._running = False
        self._paused = False
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._last_run_at: datetime | None = None
        self._last_digest_at: datetime | None = None
        self._total_cycles = 0
        self._last_run_result: PipelineRunResult | None = None

    def is_running(self) -> bool:
        """Return True if background scheduler thread is alive and running."""
        return self._running and self._thread is not None and self._thread.is_alive()

    def is_paused(self) -> bool:
        """Return True if scheduler is active but paused."""
        return self._paused

    def start(self) -> None:
        """Start background daemon worker thread."""
        if self.is_running():
            logger.warning("PipelineScheduler is already running.")
            return

        self._running = True
        self._paused = False
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name="ClientFinderSchedulerWorker",
        )
        self._thread.start()
        logger.info(
            "Scheduler daemon started. Harvest interval: %.1f min(s), Digest interval: %.1f hr(s).",
            self.harvest_interval_minutes,
            self.digest_interval_hours,
        )

    def pause(self) -> None:
        """Pause automated pipeline harvest cycles."""
        self._paused = True
        logger.info("PipelineScheduler paused.")

    def resume(self) -> None:
        """Resume automated pipeline harvest cycles."""
        self._paused = False
        logger.info("PipelineScheduler resumed.")

    def stop(self) -> None:
        """Signal background worker to terminate and wait for clean shutdown."""
        if not self.is_running():
            return

        logger.info("Stopping scheduler daemon...")
        self._running = False
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None
        logger.info("Scheduler daemon stopped.")

    def trigger_cycle_now(
        self,
        min_notification_score: float | None = None,
        limit_per_collector: int = 10,
    ) -> PipelineRunResult:
        """
        Execute an immediate on-demand pipeline harvest cycle.
        """
        score_thresh = (
            min_notification_score
            if min_notification_score is not None
            else self.min_notification_score
        )
        logger.info("Executing immediate on-demand pipeline cycle...")
        result = self.coordinator.run_cycle(
            min_notification_score=score_thresh,
            limit_per_collector=limit_per_collector,
        )
        self._last_run_at = datetime.now(UTC)
        self._last_run_result = result
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
            next_run_dt = self._last_run_at + timedelta(minutes=self.harvest_interval_minutes)
            next_run = next_run_dt.isoformat()

        return {
            "running": self.is_running(),
            "paused": self.is_paused(),
            "harvest_interval_minutes": self.harvest_interval_minutes,
            "digest_interval_hours": self.digest_interval_hours,
            "min_notification_score": self.min_notification_score,
            "last_run_at": self._last_run_at.isoformat() if self._last_run_at else None,
            "last_digest_at": self._last_digest_at.isoformat() if self._last_digest_at else None,
            "next_run_estimated": next_run,
            "total_cycles_executed": self._total_cycles,
            "last_run_summary": {
                "collected": self._last_run_result.collected_count,
                "saved": self._last_run_result.new_projects_saved,
                "scored": self._last_run_result.opportunities_scored,
                "high_priority": self._last_run_result.high_priority_count,
                "alerts_sent": self._last_run_result.notifications_sent,
                "duration_seconds": self._last_run_result.duration_seconds,
            }
            if self._last_run_result
            else None,
        }

    def _worker_loop(self) -> None:
        """Continuous daemon execution loop running periodic harvests and digests."""
        logger.info("Scheduler worker thread initialized.")

        # Run an initial cycle on startup
        try:
            self.trigger_cycle_now()
        except Exception as exc:
            logger.error("Initial harvest cycle failed: %s", exc)

        while not self._stop_event.is_set():
            # Check for harvest cycle interval
            if not self._paused:
                now = datetime.now(UTC)
                interval_delta = timedelta(minutes=self.harvest_interval_minutes)

                if self._last_run_at is None or (now - self._last_run_at) >= interval_delta:
                    try:
                        self.trigger_cycle_now()
                    except Exception as exc:
                        logger.error("Scheduled harvest cycle failed: %s", exc)

                # Check for daily digest interval
                digest_delta = timedelta(hours=self.digest_interval_hours)
                if self._last_digest_at is None or (now - self._last_digest_at) >= digest_delta:
                    try:
                        self.send_daily_digest()
                    except Exception as exc:
                        logger.error("Scheduled daily digest failed: %s", exc)

            # Sleep in short increments to allow rapid clean interruption
            for _ in range(50):
                if self._stop_event.is_set():
                    break
                time.sleep(0.1)

        logger.info("Scheduler worker thread exited.")
