"""
Unit & Integration Tests for Dense Semantic Vector Search, Hybrid RAG Retrieval, and Vector API Endpoints.
"""

import math
import uuid

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.database.connection import Base, engine, get_db
from src.database.models import ProjectModel
from src.models.profile import get_default_profile
from src.models.project import Project
from src.vectors.engine import (
    DenseVectorEngine,
    DenseVectorStore,
)
from src.vectors.hybrid_search import HybridSearchEngine
from src.vectors.rag_retriever import SemanticPortfolioRAG
from src.vectors.schemas import (
    HybridSearchRequest,
    PortfolioRAGRequest,
)


@pytest.fixture(autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client():
    return TestClient(app)


class TestDenseVectorEngine:
    """Tests for DenseVectorEngine normalization, dimensionality, and semantic embeddings."""

    def test_vector_dimension_and_l2_normalization(self):
        engine_inst = DenseVectorEngine()
        text = "FastAPI backend engineer with PostgreSQL database and Docker microservices."
        vec = engine_inst.embed_text(text)

        assert len(vec) == 384
        # L2 norm calculation: sqrt(sum(x^2)) ~= 1.0
        magnitude = math.sqrt(sum(x * x for x in vec))
        assert abs(magnitude - 1.0) < 1e-4

    def test_empty_text_returns_unit_vector(self):
        engine_inst = DenseVectorEngine()
        vec = engine_inst.embed_text("")
        assert len(vec) == 384
        assert vec[0] == 1.0
        assert sum(vec[1:]) == 0.0

    def test_semantic_similarity_concept_matching(self):
        engine_inst = DenseVectorEngine()
        query_vec = engine_inst.embed_text(
            "Looking for high throughput asynchronous Python backend"
        )
        similar_vec = engine_inst.embed_text("FastAPI Celery Redis async queue microservice")
        unrelated_vec = engine_inst.embed_text("Senior pastry chef artisan sourdough baking")

        sim_related = engine_inst.cosine_similarity(query_vec, similar_vec)
        sim_unrelated = engine_inst.cosine_similarity(query_vec, unrelated_vec)

        assert sim_related > sim_unrelated
        assert sim_related > 0.40


class TestDenseVectorStore:
    """Tests for in-memory DenseVectorStore indexing and Cosine Top-k retrieval."""

    def test_add_and_search_documents(self):
        store = DenseVectorStore()
        store.add_document(
            doc_id="1",
            text="Senior Python developer for FastAPI vector search RAG pipeline with OpenAI.",
            metadata={
                "title": "FastAPI Vector RAG",
                "budget": 5000.0,
                "skills": ["Python", "FastAPI"],
            },
        )
        store.add_document(
            doc_id="2",
            text="Wordpress developer needed for landing page theme customization and CSS tweaks.",
            metadata={"title": "Wordpress Page Fixes", "budget": 500.0, "skills": ["PHP", "CSS"]},
        )

        assert store.count() == 2

        results = store.search(
            query="AI embeddings and LLM semantic search backend",
            limit=2,
            min_similarity=0.1,
        )

        assert len(results) >= 1
        assert results[0].project_id == "1"
        assert results[0].cosine_similarity > 0.3

    def test_filter_function(self):
        store = DenseVectorStore()
        store.add_document(
            doc_id="10",
            text="React and Next.js frontend engineer",
            metadata={"category": "FRONTEND", "budget": 2000.0},
        )
        store.add_document(
            doc_id="11",
            text="React native mobile app developer",
            metadata={"category": "MOBILE", "budget": 8000.0},
        )

        results = store.search(
            query="React developer",
            limit=5,
            min_similarity=0.0,
            filter_fn=lambda m: m.get("category") == "MOBILE",
        )

        assert len(results) == 1
        assert results[0].project_id == "11"

    def test_database_reindex(self):
        uid = uuid.uuid4().hex[:8]
        with next(get_db()) as session:
            p = Project(
                title=f"Vector Reindex Opportunity {uid}",
                description="FastAPI Celery distributed async queue implementation",
                source="HN",
                source_url=f"https://example.com/vec-{uid}",
                skills=["FastAPI", "Celery", "Redis"],
                budget=6500.0,
            )
            pm = ProjectModel.from_pydantic(p)
            session.add(pm)
            session.commit()

        store = DenseVectorStore()
        indexed_count = store.index_from_database()
        assert indexed_count >= 1

        stats = store.get_stats()
        assert stats.total_indexed_documents >= 1
        assert stats.vector_dimension == 384
        assert stats.is_ready is True


class TestHybridSearchEngine:
    """Tests for HybridSearchEngine blending dense vector similarity with lexical BM25 matching."""

    def test_hybrid_search_alpha_blending(self):
        store = DenseVectorStore()
        store.add_document(
            doc_id="h1",
            text="Machine learning engineer to train custom transformer models in PyTorch",
            metadata={
                "title": "ML PyTorch Engineer",
                "skills": ["PyTorch", "Python"],
                "budget": 8000.0,
            },
        )
        store.add_document(
            doc_id="h2",
            text="Fullstack developer with React and Node.js for SaaS dashboard",
            metadata={
                "title": "Fullstack SaaS Dashboard",
                "skills": ["React", "Node"],
                "budget": 4000.0,
            },
        )

        engine = HybridSearchEngine(vector_store=store)

        # 1. Pure Semantic (alpha = 1.0)
        res_sem = engine.search(
            HybridSearchRequest(
                query="AI neural network deep learning", alpha=1.0, limit=2, min_score=0.1
            )
        )
        assert len(res_sem.results) >= 1
        assert res_sem.results[0].project_id == "h1"

        # 2. Pure Lexical (alpha = 0.0)
        res_lex = engine.search(
            HybridSearchRequest(query="React SaaS dashboard", alpha=0.0, limit=2, min_score=0.1)
        )
        assert len(res_lex.results) >= 1
        assert res_lex.results[0].project_id == "h2"


class TestSemanticPortfolioRAG:
    """Tests for SemanticPortfolioRAG case study retrieval and citation synthesis."""

    def test_portfolio_rag_context_retrieval(self):
        rag = SemanticPortfolioRAG()
        profile = get_default_profile()

        req = PortfolioRAGRequest(
            project_title="FastAPI AI Vector Search Engine",
            project_description="Build a high performance microservice with vector embeddings and PostgreSQL database.",
            target_skills=["FastAPI", "Python", "PostgreSQL", "AI"],
            top_k=2,
        )

        res = rag.retrieve_context(req, profile=profile)

        assert res.project_title == "FastAPI AI Vector Search Engine"
        assert len(res.matched_case_studies) > 0
        top_match = res.matched_case_studies[0]
        assert top_match.semantic_similarity > 0.2
        assert "suggested_proof_paragraph" in res.model_dump()
        assert len(res.suggested_proof_paragraph) > 30


class TestVectorApiEndpoints:
    """Integration tests for /api/vectors/... REST API endpoints."""

    def test_semantic_search_route(self, client: TestClient):
        payload = {
            "query": "Asynchronous backend microservices with Redis",
            "limit": 5,
            "min_similarity": 0.0,
        }
        res = client.post("/api/vectors/semantic-search", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert "results" in data
        assert data["vector_dimension"] == 384

    def test_hybrid_search_route(self, client: TestClient):
        payload = {
            "query": "FastAPI PostgreSQL",
            "alpha": 0.6,
            "limit": 5,
            "min_score": 0.0,
        }
        res = client.post("/api/vectors/hybrid-search", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["alpha"] == 0.6
        assert "results" in data

    def test_portfolio_rag_route(self, client: TestClient):
        payload = {
            "project_title": "Enterprise Knowledge Graph RAG",
            "project_description": "LLM vector search with Python microservices",
            "target_skills": ["Python", "FastAPI"],
            "top_k": 2,
        }
        res = client.post("/api/vectors/portfolio-rag", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert len(data["matched_case_studies"]) <= 2
        assert len(data["suggested_proof_paragraph"]) > 20

    def test_vector_stats_and_reindex_route(self, client: TestClient):
        res_reindex = client.post("/api/vectors/reindex")
        assert res_reindex.status_code == 200
        data_reindex = res_reindex.json()
        assert "indexed_documents" in data_reindex

        res_stats = client.get("/api/vectors/stats")
        assert res_stats.status_code == 200
        data_stats = res_stats.json()
        assert data_stats["vector_dimension"] == 384
        assert data_stats["is_ready"] is True
