"""
Technical Client Interview Preparation Assistant.
Extracts likely architectural questions, model answers based on portfolio proof, and reverse questions to ask the client.
"""

import logging

from pydantic import BaseModel, Field

from src.models.profile import UserProfile, get_default_profile

logger = logging.getLogger("InterviewPrepAdvisor")


class InterviewQuestion(BaseModel):
    """An anticipated technical or architectural interview question with guidance."""

    question: str
    why_client_asks: str
    model_answer: str
    key_technologies: list[str] = Field(default_factory=list)


class InterviewPrepSheet(BaseModel):
    """Complete technical interview preparation cheatsheet for an opportunity."""

    project_title: str
    target_skills: list[str]
    architecture_overview: str
    likely_questions: list[InterviewQuestion]
    reverse_questions_to_ask_client: list[str]
    red_flags_to_watch_for: list[str]


class InterviewPrepAdvisor:
    """
    Generates tailored interview briefing sheets to help developers ace technical discovery calls.
    """

    def __init__(self, default_profile: UserProfile | None = None):
        self.default_profile = default_profile or get_default_profile()

    def generate(
        self,
        project_title: str,
        project_description: str,
        skills: list[str] | None = None,
        profile: UserProfile | None = None,
    ) -> InterviewPrepSheet:
        """
        Generate structured interview preparation guide tailored to the project's technical stack.
        """
        user_prof = profile or self.default_profile
        target_skills = skills or ["Python", "FastAPI", "PostgreSQL", "RAG"]

        questions: list[InterviewQuestion] = [
            InterviewQuestion(
                question="How do you structure high-throughput asynchronous pipelines and handle rate limits or network failures?",
                why_client_asks="To verify you write robust, production-ready code with backoff retries and error isolation rather than fragile scripts.",
                model_answer=(
                    "I implement circuit-breaker and token-bucket rate limiting patterns using exponential backoff with jitter. "
                    "By separating raw ingestion from data enrichment via background task queues and using connection pooling, "
                    "the system maintains 99.9% uptime even under upstream API degradation."
                ),
                key_technologies=["Asyncio", "Circuit Breakers", "Exponential Backoff"],
            ),
            InterviewQuestion(
                question="How do you ensure data integrity and prevent duplicate records across distributed ingestion feeds?",
                why_client_asks="Duplicates waste compute, corrupt analytics, and create customer-facing errors.",
                model_answer=(
                    "I compute cryptographic SHA-256 content and canonical URL hashes at ingestion time, verified against "
                    "indexed unique database constraints. This guarantees idempotent processing without redundant database writes."
                ),
                key_technologies=["SHA-256 Hashing", "Idempotency", "Database Indexing"],
            ),
            InterviewQuestion(
                question="What is your approach to testing and validating AI/LLM outputs to prevent hallucinations?",
                why_client_asks="Clients want confidence that automated AI pipelines produce structured, schema-compliant outputs reliably.",
                model_answer=(
                    "I enforce strict Pydantic v2 structured schemas with validation boundaries and implement a two-tier fallback: "
                    "if an LLM API experiences transient downtime or validation errors, a deterministic heuristic engine immediately handles "
                    "the extraction with zero downtime."
                ),
                key_technologies=["Pydantic v2", "Structured JSON Outputs", "Heuristic Fallbacks"],
            ),
        ]

        reverse_questions = [
            "What does success look like for this project in the first 30 days after deployment?",
            "Are there existing legacy databases or third-party APIs that have strict rate limits or undocumented quirks?",
            "What is your deployment environment (Docker, AWS, Kubernetes, Serverless), and who handles production deployment approval?",
        ]

        red_flags = [
            "Unclear decision-making hierarchy where multiple stakeholders give conflicting technical directions.",
            "Expectation of complex real-time AI systems without budget for proper observability and caching infrastructure.",
            "Reluctance to establish formal milestone acceptance criteria prior to sprint kickoff.",
        ]

        arch_summary = (
            f"Senior engineering solution for '{project_title}' ({user_prof.name}) utilizing "
            f"{', '.join(target_skills[:4])} with clean separation of ingestion, persistence, scoring, and API presentation."
        )

        return InterviewPrepSheet(
            project_title=project_title,
            target_skills=target_skills,
            architecture_overview=arch_summary,
            likely_questions=questions,
            reverse_questions_to_ask_client=reverse_questions,
            red_flags_to_watch_for=red_flags,
        )
