"""
Unit tests for HeuristicExtractor regex, skill matching, and classification logic.
"""

from src.ai.heuristic import HeuristicExtractor
from src.ai.schemas import (
    ExperienceLevel,
    PaymentType,
    ProjectCategory,
    ProjectComplexity,
)


class TestHeuristicExtractor:
    """Tests for rule-based heuristic extraction."""

    def test_extract_skills_from_text(self):
        extractor = HeuristicExtractor()
        text = "Looking for a Python developer with FastAPI and PostgreSQL expertise to build a RAG chatbot using LangChain."
        skills = extractor.extract_skills(text)

        assert "Python" in skills
        assert "FastAPI" in skills
        assert "PostgreSQL" in skills
        assert "RAG" in skills
        assert "LangChain" in skills

    def test_extract_budget_fixed_range(self):
        extractor = HeuristicExtractor()
        text = "Budget: $3,000 - $5,000 for the full milestone deliverable."
        b_min, b_max, currency, p_type = extractor.extract_budget(text)

        assert b_min == 3000.0
        assert b_max == 5000.0
        assert currency == "USD"
        assert p_type == PaymentType.FIXED_PRICE

    def test_extract_budget_hourly_rate(self):
        extractor = HeuristicExtractor()
        text = "Hourly rate is $80/hr, expecting ~20 hours per week."
        b_min, b_max, currency, p_type = extractor.extract_budget(text)

        assert b_min == 80.0
        assert b_max == 80.0
        assert currency == "USD"
        assert p_type == PaymentType.HOURLY

    def test_extract_budget_european_and_indian_currency(self):
        extractor = HeuristicExtractor()

        # Euro
        text_eur = "Compensation: €2,500 fixed price"
        b_min, _, curr_eur, _ = extractor.extract_budget(text_eur)
        assert b_min == 2500.0
        assert curr_eur == "EUR"

        # INR
        text_inr = "Budget: ₹50,000 for initial phase"
        b_min_inr, _, curr_inr, _ = extractor.extract_budget(text_inr)
        assert b_min_inr == 50000.0
        assert curr_inr == "INR"

    def test_classify_category_ai(self):
        extractor = HeuristicExtractor()
        skills = ["Python", "LangChain", "OpenAI"]
        cat = extractor.classify_category(skills, "Build an AI agent for customer support")
        assert cat == ProjectCategory.AI_DEVELOPMENT

    def test_classify_category_web(self):
        extractor = HeuristicExtractor()
        skills = ["Next.js", "React", "TailwindCSS"]
        cat = extractor.classify_category(skills, "Build modern web application frontend")
        assert cat == ProjectCategory.WEB_DEVELOPMENT

    def test_classify_category_scraping(self):
        extractor = HeuristicExtractor()
        skills = ["Python", "Playwright", "Web Scraping"]
        cat = extractor.classify_category(skills, "Scrape e-commerce prices daily")
        assert cat == ProjectCategory.AUTOMATION_SCRAPING

    def test_estimate_complexity_levels(self):
        extractor = HeuristicExtractor()

        # High complexity
        high = extractor.estimate_complexity(
            ["Python", "FastAPI", "PostgreSQL", "Docker", "Kubernetes", "Redis", "Kafka"],
            "Architect high throughput microservices with distributed caching.",
        )
        assert high == ProjectComplexity.HIGH

        # Low complexity
        low = extractor.estimate_complexity(["Python"], "Quick script to parse a CSV file.")
        assert low == ProjectComplexity.LOW

    def test_estimate_experience_level(self):
        extractor = HeuristicExtractor()

        assert (
            extractor.estimate_experience_level("Seeking a senior Python engineer (5+ years)")
            == ExperienceLevel.SENIOR
        )
        assert (
            extractor.estimate_experience_level("Looking for a lead architect to guide our team")
            == ExperienceLevel.LEAD
        )
        assert (
            extractor.estimate_experience_level("Junior developer intern needed")
            == ExperienceLevel.JUNIOR
        )

    def test_full_heuristic_extract_pipeline(self):
        extractor = HeuristicExtractor()
        title = "Senior AI Engineer (RAG & LangChain)"
        description = """
        We need a Senior AI Engineer to build a RAG pipeline with FastAPI and PostgreSQL.
        Budget: $4,000 - $6,000 fixed price.
        Deliverables:
        - Design vector database schema
        - Integrate OpenAI embeddings and LangChain retrieval
        - Deploy on AWS with Docker
        """

        reqs = extractor.extract(title, description)

        assert reqs.category == ProjectCategory.AI_DEVELOPMENT
        assert "Python" in reqs.required_skills or "FastAPI" in reqs.required_skills
        assert "RAG" in reqs.required_skills
        assert "LangChain" in reqs.required_skills
        assert reqs.budget_min == 4000.0
        assert reqs.budget_max == 6000.0
        assert reqs.currency == "USD"
        assert reqs.project_type == PaymentType.FIXED_PRICE
        assert reqs.experience_level == ExperienceLevel.SENIOR
        assert len(reqs.deliverables) >= 2
        assert reqs.confidence_score >= 0.70
