from typing import Any


class ProjectCleaner:
    """
    Cleans and normalizes raw project data.
    """

    def clean(self, project: dict[str, Any]) -> dict[str, Any]:
        """
        Clean a single project.

        Args:
            project: Raw project data.

        Returns:
            Cleaned project data.
        """

        cleaned_project = {}

        for key, value in project.items():
            if isinstance(value, str):
                value = value.strip()
            elif key == "project_type" and isinstance(value, list):
                value = str(value[0]) if value else "Contract"

            cleaned_project[key] = value

        return cleaned_project

    def clean_many(self, projects: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Clean multiple projects.
        """

        return [self.clean(project) for project in projects]


def clean_project_data(project: dict[str, Any]) -> dict[str, Any]:
    """Clean a single project dictionary."""
    return ProjectCleaner().clean(project)
