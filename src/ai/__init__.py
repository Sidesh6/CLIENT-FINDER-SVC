"""
AI package for Client Finder service.
Provides requirement extraction, LLM clients, prompts, and schemas.
"""

from src.ai.client import (
    BaseLLMClient,
    GeminiLLMClient,
    OpenAICompatibleClient,
    get_llm_client,
)
from src.ai.extractor import ProjectExtractor
from src.ai.heuristic import HeuristicExtractor
from src.ai.prompts import EXTRACTION_SYSTEM_PROMPT, build_extraction_prompt
from src.ai.schemas import (
    ExperienceLevel,
    ExtractedRequirements,
    PaymentType,
    ProjectCategory,
    ProjectComplexity,
)

__all__ = [
    "ProjectExtractor",
    "HeuristicExtractor",
    "ExtractedRequirements",
    "ProjectCategory",
    "ProjectComplexity",
    "PaymentType",
    "ExperienceLevel",
    "BaseLLMClient",
    "OpenAICompatibleClient",
    "GeminiLLMClient",
    "get_llm_client",
    "EXTRACTION_SYSTEM_PROMPT",
    "build_extraction_prompt",
]
