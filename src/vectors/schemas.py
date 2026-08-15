"""
Pydantic Schemas for Dense Semantic Vector Search, Hybrid RAG Retrieval, and Vector Index Telemetry.
"""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class VectorDocument(BaseModel):
    """An indexed vector document with dense embedding and metadata."""

    id: str = Field(description="Unique document or project identifier")
    text: str = Field(description="Raw indexed textual content")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Custom metadata tags")
    embedding: list[float] = Field(
        default_factory=list, description="Normalized dense float embedding vector"
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SemanticSearchRequest(BaseModel):
    """Inbound request for natural language semantic vector search."""

    query: str = Field(description="Natural language query or requirement description")
    limit: int = Field(default=10, ge=1, le=100, description="Max results to return")
    min_similarity: float = Field(
        default=0.3, ge=0.0, le=1.0, description="Minimum cosine similarity threshold"
    )
    filter_category: str | None = Field(default=None, description="Optional category filter")
    min_budget: float | None = Field(default=None, description="Optional minimum budget filter")


class SemanticSearchResultItem(BaseModel):
    """A matched opportunity result from semantic vector search."""

    project_id: int | str
    title: str
    description: str
    cosine_similarity: float = Field(ge=0.0, le=1.0)
    source: str = "Public Web"
    source_url: str | None = None
    budget: float | None = None
    currency: str = "USD"
    skills: list[str] = Field(default_factory=list)
    semantic_highlights: list[str] = Field(default_factory=list)


class SemanticSearchResponse(BaseModel):
    """Output response from dense semantic vector search."""

    query: str
    total_matches: int
    results: list[SemanticSearchResultItem]
    search_duration_ms: float
    vector_dimension: int


class HybridSearchRequest(BaseModel):
    """Inbound request for hybrid dense vector + lexical BM25 search."""

    query: str = Field(description="Search query string")
    alpha: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Weight balance: 1.0 = Pure Semantic Vector, 0.0 = Pure Lexical BM25",
    )
    limit: int = Field(default=10, ge=1, le=100)
    min_score: float = Field(default=0.2, ge=0.0, le=1.0)


class HybridSearchResultItem(BaseModel):
    """A matched opportunity from hybrid retrieval."""

    project_id: int | str
    title: str
    description: str
    hybrid_score: float = Field(ge=0.0, le=1.0)
    semantic_similarity: float = Field(ge=0.0, le=1.0)
    lexical_score: float = Field(ge=0.0, le=1.0)
    source: str = "Public Web"
    budget: float | None = None
    skills: list[str] = Field(default_factory=list)


class HybridSearchResponse(BaseModel):
    """Output response from hybrid dense + lexical search."""

    query: str
    alpha: float
    total_matches: int
    results: list[HybridSearchResultItem]
    duration_ms: float


class PortfolioRAGRequest(BaseModel):
    """Inbound request to retrieve semantically relevant portfolio case studies for a project."""

    project_title: str
    project_description: str = Field(default="")
    target_skills: list[str] = Field(default_factory=list)
    top_k: int = Field(default=3, ge=1, le=10)


class PortfolioRAGMatchItem(BaseModel):
    """A contextually retrieved portfolio case study with semantic relevance."""

    title: str
    client_industry: str
    technologies: list[str]
    quantitative_outcomes: list[str]
    summary_paragraph: str
    semantic_similarity: float = Field(ge=0.0, le=1.0)
    relevant_citation_snippet: str = Field(
        description="Formatted proof snippet for pitch inclusion"
    )


class PortfolioRAGResponse(BaseModel):
    """Semantic portfolio retrieval response for proposal RAG context injection."""

    project_title: str
    matched_case_studies: list[PortfolioRAGMatchItem]
    suggested_proof_paragraph: str = Field(
        description="Ready-to-paste case study evidence paragraph for proposal"
    )
    retrieval_duration_ms: float


class VectorIndexStats(BaseModel):
    """Operational telemetry for the dense vector index."""

    total_indexed_documents: int
    vector_dimension: int
    index_memory_bytes: int
    last_reindexed_at: datetime | None
    is_ready: bool
