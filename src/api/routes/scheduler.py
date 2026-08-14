"""
REST API endpoints for scheduler lifecycle management and on-demand pipeline execution.
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status

from src.scheduler.service import PipelineScheduler

logger = logging.getLogger("SchedulerAPI")

router = APIRouter(prefix="/api/scheduler", tags=["Scheduler & Autonomous Execution"])

# Global scheduler service instance
_SCHEDULER = PipelineScheduler()


@router.get("/status", status_code=status.HTTP_200_OK)
def get_scheduler_status() -> dict[str, Any]:
    """Retrieve operational status, active configuration, and cycle metrics."""
    return dict(_SCHEDULER.get_status())


@router.post("/start", status_code=status.HTTP_200_OK)
def start_scheduler(
    harvest_interval_minutes: float = Query(
        default=15.0, ge=1.0, description="Harvest interval in minutes"
    ),
    digest_interval_hours: float = Query(
        default=24.0, ge=1.0, description="Daily digest interval in hours"
    ),
    min_notification_score: float = Query(
        default=75.0, ge=0.0, le=100.0, description="Min score for alert dispatch"
    ),
) -> dict[str, Any]:
    """Start background scheduler daemon thread."""
    if _SCHEDULER.is_running():
        return {"status": "already_running", "message": "Scheduler daemon is already running."}

    _SCHEDULER.harvest_interval_minutes = harvest_interval_minutes
    _SCHEDULER.digest_interval_hours = digest_interval_hours
    _SCHEDULER.min_notification_score = min_notification_score
    _SCHEDULER.start()

    return {"status": "started", "message": "Background scheduler daemon started successfully."}


@router.post("/pause", status_code=status.HTTP_200_OK)
def pause_scheduler() -> dict[str, Any]:
    """Pause automatic scheduled harvesting runs."""
    _SCHEDULER.pause()
    return {"status": "paused", "message": "Scheduled harvest runs paused."}


@router.post("/resume", status_code=status.HTTP_200_OK)
def resume_scheduler() -> dict[str, Any]:
    """Resume paused scheduler executions."""
    _SCHEDULER.resume()
    return {"status": "resumed", "message": "Scheduled harvest runs resumed."}


@router.post("/stop", status_code=status.HTTP_200_OK)
def stop_scheduler() -> dict[str, Any]:
    """Stop the background scheduler daemon."""
    _SCHEDULER.stop()
    return {"status": "stopped", "message": "Scheduler daemon stopped successfully."}


@router.post("/run-now", status_code=status.HTTP_200_OK)
def trigger_immediate_cycle() -> dict[str, Any]:
    """Trigger an immediate on-demand pipeline cycle across all active collectors."""
    try:
        result = _SCHEDULER.trigger_cycle_now()
        return {
            "status": "completed",
            "result": {
                "collected_count": result.collected_count,
                "new_projects_saved": result.new_projects_saved,
                "duplicates_skipped": result.duplicates_skipped,
                "opportunities_scored": result.opportunities_scored,
                "high_priority_count": result.high_priority_count,
                "notifications_sent": result.notifications_sent,
                "duration_seconds": result.duration_seconds,
                "success": result.success,
                "errors": result.errors,
            },
        }
    except Exception as exc:
        logger.error("Immediate pipeline cycle failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pipeline execution failed: {exc}",
        ) from exc


@router.post("/digest", status_code=status.HTTP_200_OK)
def trigger_daily_digest(
    lookback_hours: int = Query(default=24, ge=1, description="Hours to look back for top leads"),
) -> dict[str, Any]:
    """Synthesize and broadcast a summary digest to active notification channels."""
    try:
        results = _SCHEDULER.send_daily_digest(lookback_hours=lookback_hours)
        return {
            "status": "dispatched",
            "channels_notified": len(results),
            "results": [
                {
                    "channel": r.channel.value,
                    "success": r.success,
                    "error": r.error_message,
                }
                for r in results
            ],
        }
    except Exception as exc:
        logger.error("Failed to dispatch summary digest: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Digest broadcast failed: {exc}",
        ) from exc
