"""
Endpoints for inspecting and triggering data collection pipelines.
"""

from fastapi import APIRouter, Query

from src.ai.extractor import ProjectExtractor
from src.api.routes.profile import get_current_active_profile
from src.api.schemas import CollectorTriggerResponse
from src.collectors.hackernews_collector import HackerNewsCollector
from src.database.connection import SessionLocal
from src.database.repository import ProjectRepository
from src.processors.cleaner import ProjectCleaner
from src.scoring.engine import OpportunityScorer

router = APIRouter(prefix="/api/collectors", tags=["Collectors"])


@router.get("")
def list_collectors() -> list[dict[str, str | bool]]:
    """
    List registered external collectors and their capabilities.
    """
    return [
        {
            "name": "Hacker News",
            "type": "API / Community",
            "enabled": True,
            "description": "Scrapes Ask HN 'Freelancer? Seeking freelancer?' threads via Algolia API",
        },
        {
            "name": "Freelancer / RSS Feeds",
            "type": "RSS / Webhook",
            "enabled": True,
            "description": "Monitors freelance job boards and remote tech feeds",
        },
    ]


@router.post("/trigger", response_model=CollectorTriggerResponse)
def trigger_collector(
    collector_name: str = Query("Hacker News", description="Name of collector to trigger"),
    limit: int = Query(5, ge=1, le=25, description="Max opportunities to harvest"),
) -> CollectorTriggerResponse:
    """
    Trigger immediate execution of an opportunity collector and run full extraction & scoring pipeline.
    """
    collector = HackerNewsCollector(max_projects=limit)
    raw_projects = collector.collect()

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
        added_models = repo.add_many(enriched)
        session.commit()

        for pm in added_models:
            p_obj = pm.to_pydantic()
            scorer.score_and_persist(p_obj, profile=profile, session=session)
            scored_count += 1

    return CollectorTriggerResponse(
        collector_name=collector_name,
        status="completed",
        collected_count=len(raw_projects),
        enriched_count=len(enriched),
        scored_count=scored_count,
        message=f"Successfully harvested {len(raw_projects)} items, extracted requirements, and scored opportunities.",
    )
