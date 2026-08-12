from typing import Any


class ProjectExtractor:
    """
    Extracts structured information from project descriptions.

    The actual LLM integration will be added later.
    """

    def extract(self, project: dict[str, Any]) -> dict[str, Any]:
        """
        Extract structured project information.

        Args:
            project: Cleaned project data.

        Returns:
            Structured project information.
        """

        description = project.get("description", "")

        return {
            "title": project.get("title"),
            "description": description,
            "skills": [],
            "budget": None,
            "currency": None,
            "project_type": None,
            "client_name": None,
            "deadline": None,
        }