from typing import Any

from src.collectors.base_collector import BaseCollector


class ExampleCollector(BaseCollector):
    """
    Example collector used for development and testing.

    This collector does not access the internet yet.
    """

    def __init__(self):
        super().__init__("Example Source")

    def collect(self) -> list[dict[str, Any]]:
        """
        Return example project opportunities.
        """

        return [
            {
                "title": "AI Chatbot Development",

                "description": (
                    "Build an AI chatbot using Python, "
                    "FastAPI and RAG."
                ),

                "source": self.source_name,

                "source_url": (
                    "https://example.com/project/123"
                ),

                "client_name": "Example Client",

                "budget": 2000,

                "currency": "USD",

                "project_type": "AI Development",

                "skills": [
                    "Python",
                    "FastAPI",
                    "RAG"
                ]
            },

            {
                "title": "Computer Vision Application",

                "description": (
                    "Develop a computer vision application "
                    "using Python and OpenCV."
                ),

                "source": self.source_name,

                "source_url": (
                    "https://example.com/project/456"
                ),

                "client_name": "Vision Client",

                "budget": 1500,

                "currency": "USD",

                "project_type": "Computer Vision",

                "skills": [
                    "Python",
                    "OpenCV",
                    "Computer Vision"
                ]
            }
        ]