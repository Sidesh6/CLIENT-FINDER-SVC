from typing import Any

from src.models.project import Project


class ProjectExtractor:
    """
    Extracts structured information from project descriptions.

    The actual LLM integration will be added later.
    """

    def extract(self, project: dict[str, Any]) -> Project:
        """
        Extract structured project information.

        Args:
            project: Cleaned project data.

        Returns:
            Structured project information.
        """

        return Project(
            title=project["title"],
            description=project["description"],
            source=project["source"],
            source_url=project["source_url"],
            client_name=project.get("client_name", None),
            budget=project.get("budget", None),
            currency=project.get("currency", None),
            project_type=project.get("project_type", None),
            skills=project.get("skills", []),
            project_start_date=project.get("project_start_date", None),
            project_end_date=project.get("project_end_date", None),
            score=project.get("score", None),
        )
