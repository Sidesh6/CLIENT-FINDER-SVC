"""
Hybrid Dense Vector + Lexical Search Engine with Reciprocal Rank Fusion (RRF).
Blends exact skill/keyword matching with dense semantic embeddings.
"""

import logging
import re
import time

from src.vectors.engine import GLOBAL_VECTOR_STORE, DenseVectorStore
from src.vectors.schemas import (
    HybridSearchRequest,
    HybridSearchResponse,
    HybridSearchResultItem,
)

logger = logging.getLogger("HybridSearchEngine")


class HybridSearchEngine:
    """
    Blends dense semantic vector representations with lexical BM25 matching.
    """

    def __init__(self, vector_store: DenseVectorStore | None = None):
        self.vector_store = vector_store or GLOBAL_VECTOR_STORE

    def search(self, req: HybridSearchRequest) -> HybridSearchResponse:
        """
        Execute hybrid search blending dense semantic similarity with lexical token overlap.
        """
        start_time = time.perf_counter()
        query = req.query.strip()
        alpha = req.alpha  # 1.0 = Pure Semantic, 0.0 = Pure Lexical
        limit = req.limit

        if self.vector_store.count() == 0:
            # Auto-populate vector store if not yet indexed
            self.vector_store.index_from_database()

        # 1. Dense Semantic Similarity Retrieval
        dense_matches = self.vector_store.search(query=query, limit=limit * 3, min_similarity=0.0)
        dense_score_map: dict[str, float] = {
            str(item.project_id): item.cosine_similarity for item in dense_matches
        }

        # 2. Lexical Token BM25 Scoring
        query_terms = set(re.findall(r"\b[a-zA-Z0-9_-]+\b", query.lower()))
        lexical_scores: dict[str, float] = {}

        for doc_id, doc in self.vector_store._documents.items():
            score = self._compute_lexical_score(query_terms, doc.text, doc.metadata)
            lexical_scores[doc_id] = score

        # 3. Hybrid Fusion Calculation: Score = alpha * dense + (1 - alpha) * lexical
        all_doc_ids = set(dense_score_map.keys()).union(set(lexical_scores.keys()))
        hybrid_results: list[tuple[float, float, float, str]] = []

        for doc_id in all_doc_ids:
            dense_sim = max(0.0, dense_score_map.get(doc_id, 0.0))
            lex_score = lexical_scores.get(doc_id, 0.0)

            # Blended linear interpolation
            fused_score = (alpha * dense_sim) + ((1.0 - alpha) * lex_score)

            if fused_score >= req.min_score:
                hybrid_results.append((fused_score, dense_sim, lex_score, doc_id))

        # Sort by fused hybrid score descending
        hybrid_results.sort(key=lambda x: x[0], reverse=True)

        items: list[HybridSearchResultItem] = []
        for fused, dense_sim, lex_score, doc_id in hybrid_results[:limit]:
            target_doc = self.vector_store.get_document(doc_id)
            if target_doc is None:
                continue
            meta = target_doc.metadata
            items.append(
                HybridSearchResultItem(
                    project_id=meta.get("project_id", doc_id),
                    title=meta.get("title", doc_id),
                    description=target_doc.text[:280] + ("..." if len(target_doc.text) > 280 else ""),
                    hybrid_score=round(fused, 4),
                    semantic_similarity=round(dense_sim, 4),
                    lexical_score=round(lex_score, 4),
                    source=meta.get("source", "Public Web"),
                    budget=meta.get("budget"),
                    skills=meta.get("skills", []),
                )
            )

        duration = (time.perf_counter() - start_time) * 1000.0
        return HybridSearchResponse(
            query=query,
            alpha=alpha,
            total_matches=len(items),
            results=items,
            duration_ms=round(duration, 2),
        )

    def _compute_lexical_score(self, query_terms: set[str], doc_text: str, metadata: dict) -> float:
        """Compute normalized term frequency / title match score."""
        if not query_terms:
            return 0.0

        lower_doc = doc_text.lower()
        title_lower = metadata.get("title", "").lower()
        skills = [s.lower() for s in metadata.get("skills", [])]

        matches = 0.0
        for term in query_terms:
            # Title matches receive highest weight
            if term in title_lower:
                matches += 2.0
            # Explicit skill matches receive high weight
            elif any(term in s for s in skills):
                matches += 1.5
            elif term in lower_doc:
                matches += 1.0

        max_possible = len(query_terms) * 2.0
        if max_possible == 0:
            return 0.0
        return min(1.0, matches / max_possible)


# Global Singleton Instance
GLOBAL_HYBRID_SEARCH = HybridSearchEngine()
