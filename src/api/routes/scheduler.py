"""
REST endpoints for controlling the autonomous background scheduler daemon.
"""

from typing import Any

from fastapi import APIRouter

from src.scheduler.service import PipelineScheduler

router = APIRouter(prefix="/api/scheduler", tags=["Scheduler"])

_SCHEDULER = PipelineScheduler()


@router.get("/status")
def get_scheduler_status() -> dict[str, Any]:
    """
    Get operational status, cycle telemetry, and timers of the background scheduler.
    """
    return _SCHEDULER.get_status()


@router.post("/start")
def start_scheduler() -> dict[str, Any]:
    """
    Start the autonomous background scheduler daemon.
    """
    _SCHEDULER.start()
    return {"status": "started", "scheduler": _SCHEDULER.get_status()}


@router.post("/pause")
def pause_scheduler() -> dict[str, Any]:
    """
    Pause automated periodic triggers.
    """
    _SCHEDULER.pause()
    return {"status": "paused", "scheduler": _SCHEDULER.get_status()}


@router.post("/resume")
def resume_scheduler() -> dict[str, Any]:
    """
    Resume automated periodic triggers.
    """
    _SCHEDULER.resume()
    return {"status": "resumed", "scheduler": _SCHEDULER.get_status()}


@router.post("/stop")
def stop_scheduler() -> dict[str, Any]:
    """
    Stop the background scheduler daemon.
    """
    _SCHEDULER.stop()
    return {"status": "stopped", "scheduler": _SCHEDULER.get_status()}


@router.post("/run-now")
def trigger_immediate_cycle() -> dict[str, Any]:
    """
    Trigger an immediate on-demand pipeline cycle across collectors.
    """
    result = _SCHEDULER.trigger_cycle_now()
    return {
        "status": "completed",
        "result": result.to_dict(),
    }


@router.post("/digest")
def trigger_daily_digest() -> dict[str, Any]:
    """
    Synthesize and dispatch an immediate daily summary digest to active channels.
    """
    results = _SCHEDULER.send_daily_digest()
    return {
        "status": "sent",
        "channels_contacted": len(results),
        "results": [r.model_dump() for r in results],
    }
