"""
Endpoints for inspecting, configuring, and triggering multi-source data collection pipelines.
"""

from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query, status

from src.ai.extractor import ProjectExtractor
from src.api.routes.profile import get_current_active_profile
from src.api.schemas import CollectorTriggerResponse
from src.collectors.registry import DEFAULT_REGISTRY
from src.database.connection import SessionLocal
from src.database.repository import ProjectRepository
from src.processors.cleaner import ProjectCleaner
from src.scoring.engine import OpportunityScorer

router = APIRouter(prefix="/api/collectors", tags=["Collectors & Multi-Source Feeds"])


@router.get("", response_model=list[dict[str, Any]])
def list_collectors() -> list[dict[str, Any]]:
    """
    List all registered external source collectors and their operational health states.
    """
    return [state.to_dict() for state in DEFAULT_REGISTRY.get_all_states()]


@router.get("/health", response_model=list[dict[str, Any]])
def get_collectors_health() -> list[dict[str, Any]]:
    """
    Retrieve operational health telemetry, success rates, and circuit-breaker states.
    """
    return [state.to_dict() for state in DEFAULT_REGISTRY.get_all_states()]


@router.post("/{source_name}/toggle")
def toggle_collector(
    source_name: str,
    enable: Annotated[bool | None, Query(description="Explicit boolean or None to invert")] = None,
) -> dict[str, Any]:
    """
    Enable or disable a specific source collector.
    """
    try:
        new_state = DEFAULT_REGISTRY.toggle(source_name, enable=enable)
        return {
            "source_name": source_name,
            "enabled": new_state,
            "message": f"Collector '{source_name}' enabled set to {new_state}.",
        }
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collector '{source_name}' not registered in system.",
        ) from None


@router.post("/{source_name}/reset-circuit")
def reset_collector_circuit(source_name: str) -> dict[str, Any]:
    """
    Manually reset a tripped circuit breaker for a source.
    """
    success = DEFAULT_REGISTRY.reset_circuit(source_name)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collector '{source_name}' not registered.",
        )
    return {
        "source_name": source_name,
        "circuit_broken": False,
        "message": f"Circuit breaker for '{source_name}' reset successfully.",
    }


@router.post("/collect", response_model=CollectorTriggerResponse)
@router.post("/trigger", response_model=CollectorTriggerResponse)
def trigger_collector(
    collector_name: Annotated[
        str,
        Query(
            description="Name of collector ('Hacker News', 'RemoteOK', 'WeWorkRemotely', or 'all')"
        ),
    ] = "Hacker News",
    limit: Annotated[int, Query(ge=1, le=50, description="Max opportunities per source")] = 10,
) -> CollectorTriggerResponse:
    """
    Trigger immediate execution of an opportunity collector and run full extraction & scoring pipeline.
    """
    if collector_name.lower() == "all":
        collectors = DEFAULT_REGISTRY.get_active_collectors()
    else:
        collector = DEFAULT_REGISTRY.get_collector(collector_name)
        if not collector:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collector '{collector_name}' not found. Available: {DEFAULT_REGISTRY.list_sources()}",
            )
        collectors = [collector]

    raw_projects: list[dict[str, Any]] = []

    for col in collectors:
        try:
            if hasattr(col, "max_projects"):
                col.max_projects = limit
            items = col.collect()
            DEFAULT_REGISTRY.record_success(col.source_name, len(items))
            raw_projects.extend(items)
        except Exception as exc:
            DEFAULT_REGISTRY.record_failure(col.source_name, str(exc))

    if not raw_projects:
        return CollectorTriggerResponse(
            collector_name=collector_name,
            status="completed",
            collected_count=0,
            enriched_count=0,
            scored_count=0,
            message="No new items discovered in target feeds.",
        )

    # Clean
    cleaner = ProjectCleaner()
    cleaned = cleaner.clean_many(raw_projects)

    # Extract Requirements
    extractor = ProjectExtractor()
    enriched = [extractor.extract(p) for p in cleaned]

    # Save to Database & Score
    profile = get_current_active_profile()
    scorer = OpportunityScorer(default_profile=profile)
    scored_count = 0

    with SessionLocal() as session:
        repo = ProjectRepository(session)
        added_models = repo.add_many(list(enriched))
        session.commit()

        for pm in added_models:
            p_obj = pm.to_pydantic()
            scorer.score_and_persist(
                project_id=pm.id, project=p_obj, session=session, profile=profile
            )
            scored_count += 1

    return CollectorTriggerResponse(
        collector_name=collector_name,
        status="completed",
        collected_count=len(raw_projects),
        enriched_count=len(enriched),
        scored_count=scored_count,
        message=f"Successfully harvested {len(raw_projects)} items across {len(collectors)} source(s), extracted requirements, and scored opportunities.",
    )
