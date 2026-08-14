"""
Project requirement extraction coordinator.
Uses LLM structured extraction with automatic rule-based heuristic fallback.
"""

import json
import logging
from typing import Any

from pydantic import HttpUrl

from src.ai.client import BaseLLMClient, get_llm_client
from src.ai.heuristic import HeuristicExtractor
from src.ai.prompts import EXTRACTION_SYSTEM_PROMPT, build_extraction_prompt
from src.ai.schemas import ExtractedRequirements
from src.models.project import Project

logger = logging.getLogger(__name__)


class ProjectExtractor:
    """
    Extracts structured technical requirements, skills, categories, budgets,
    and metadata from project descriptions using LLMs and heuristic fallback.
    """

    def __init__(
        self,
        llm_client: BaseLLMClient | None = None,
        heuristic_extractor: HeuristicExtractor | None = None,
    ):
        self.llm_client = llm_client if llm_client is not None else get_llm_client()
        self.heuristic = heuristic_extractor or HeuristicExtractor()

    def extract_requirements(
        self, title: str, description: str, source: str = "Unknown"
    ) -> ExtractedRequirements:
        """
        Extract structured requirements from title and description.
        Attempts LLM parsing first, gracefully falling back to HeuristicExtractor on failure.
        """
        if self.llm_client is not None:
            try:
                prompt = build_extraction_prompt(
                    title=title, description=description, source=source
                )
                raw_json = self.llm_client.generate(
                    prompt=prompt, system_prompt=EXTRACTION_SYSTEM_PROMPT
                )
                parsed = json.loads(raw_json)
                return ExtractedRequirements.model_validate(parsed)
            except Exception as exc:
                logger.warning(
                    "LLM requirement extraction failed (%s). Falling back to heuristic extractor.",
                    exc,
                )

        return self.heuristic.extract(title=title, description=description)

    def extract(self, project: dict[str, Any] | Project) -> Project:
        """
        Extract structured information and return a fully enriched Pydantic Project model.

        Args:
            project: Raw/cleaned project dictionary or existing Project model

        Returns:
            Enriched Project instance
        """
        if isinstance(project, Project):
            title = project.title
            description = project.description
            source = project.source
            source_url = project.source_url
            client_name = project.client_name
            budget = project.budget
            currency = project.currency
            project_type = project.project_type
            skills = list(project.skills)
            start_date = project.project_start_date
            end_date = project.project_end_date
            score = project.score
        elif isinstance(project, dict):
            title = str(project["title"])
            description = str(project["description"])
            source = str(project.get("source", "Unknown"))
            source_url = HttpUrl(str(project["source_url"]))
            client_name = project.get("client_name")
            budget = project.get("budget")
            currency = project.get("currency")
            project_type = project.get("project_type")
            skills = list(project.get("skills", []))
            start_date = project.get("project_start_date")
            end_date = project.get("project_end_date")
            score = project.get("score")
        else:
            raise TypeError(f"Unsupported project payload type: {type(project)}")

        # Run AI/Heuristic extraction
        reqs = self.extract_requirements(title=title, description=description, source=source)

        # Merge extracted skills with existing
        merged_skills = list(dict.fromkeys(skills + reqs.required_skills))

        # Backfill budget if missing
        final_budget = budget
        if final_budget is None and reqs.budget_min is not None:
            final_budget = reqs.budget_min

        final_currency = currency or reqs.currency
        final_project_type = project_type or (
            reqs.project_type.value if reqs.project_type.value != "Unknown" else None
        )

        return Project(
            title=title,
            description=description,
            source=source,
            source_url=source_url,
            client_name=client_name,
            budget=final_budget,
            currency=final_currency,
            project_type=final_project_type,
            skills=merged_skills,
            category=reqs.category.value,
            complexity=reqs.estimated_complexity.value,
            deliverables=reqs.deliverables,
            confidence_score=reqs.confidence_score,
            project_start_date=start_date,
            project_end_date=end_date,
            score=score,
        )

    def extract_many(self, projects: list[dict[str, Any] | Project]) -> list[Project]:
        """
        Process a batch of projects through the extraction pipeline.
        """
        return [self.extract(p) for p in projects]
