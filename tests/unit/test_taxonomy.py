"""
Unit tests for skill taxonomy, synonym mapping, and implied skill ontology.
"""

from src.matching.taxonomy import (
    get_implied_skills,
    normalize_skill_name,
)


class TestTaxonomy:
    """Tests for canonical skill normalization and ontology graph traversal."""

    def test_normalize_synonyms(self):
        assert normalize_skill_name("postgres") == "PostgreSQL"
        assert normalize_skill_name("PostgreSQL") == "PostgreSQL"
        assert normalize_skill_name("fastapi") == "FastAPI"
        assert normalize_skill_name("fast-api") == "FastAPI"
        assert normalize_skill_name("reactjs") == "React"
        assert normalize_skill_name("next.js") == "Next.js"
        assert normalize_skill_name("k8s") == "Kubernetes"
        assert normalize_skill_name("py") == "Python"
        assert normalize_skill_name("chatgpt") == "OpenAI"

    def test_unknown_skill_returns_cleaned_name(self):
        assert normalize_skill_name("CustomInternalTool") == "CustomInternalTool"

    def test_implied_skills_graph(self):
        implied_fastapi = get_implied_skills("FastAPI")
        assert "Python" in implied_fastapi

        implied_langchain = get_implied_skills("LangChain")
        assert "Python" in implied_langchain
        assert "LLM" in implied_langchain
        assert "RAG" in implied_langchain

        implied_nextjs = get_implied_skills("Next.js")
        assert "React" in implied_nextjs
        assert "TypeScript" in implied_nextjs

    def test_implied_skills_case_insensitivity(self):
        implied = get_implied_skills("fastapi")
        assert "Python" in implied
