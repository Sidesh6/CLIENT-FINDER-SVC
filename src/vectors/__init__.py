"""
Dense Semantic Vector Embeddings, Hybrid RAG Retrieval, and Nearest Neighbor Search Package.
"""

from src.vectors.engine import (
    GLOBAL_VECTOR_STORE,
    DenseVectorEngine,
    DenseVectorStore,
)
from src.vectors.hybrid_search import (
    GLOBAL_HYBRID_SEARCH,
    HybridSearchEngine,
)
from src.vectors.rag_retriever import (
    GLOBAL_PORTFOLIO_RAG,
    SemanticPortfolioRAG,
)
from src.vectors.schemas import (
    HybridSearchRequest,
    HybridSearchResponse,
    HybridSearchResultItem,
    PortfolioRAGMatchItem,
    PortfolioRAGRequest,
    PortfolioRAGResponse,
    SemanticSearchRequest,
    SemanticSearchResponse,
    SemanticSearchResultItem,
    VectorDocument,
    VectorIndexStats,
)

__all__ = [
    "DenseVectorEngine",
    "DenseVectorStore",
    "GLOBAL_VECTOR_STORE",
    "HybridSearchEngine",
    "GLOBAL_HYBRID_SEARCH",
    "SemanticPortfolioRAG",
    "GLOBAL_PORTFOLIO_RAG",
    "VectorDocument",
    "SemanticSearchRequest",
    "SemanticSearchResultItem",
    "SemanticSearchResponse",
    "HybridSearchRequest",
    "HybridSearchResultItem",
    "HybridSearchResponse",
    "PortfolioRAGRequest",
    "PortfolioRAGMatchItem",
    "PortfolioRAGResponse",
    "VectorIndexStats",
]
