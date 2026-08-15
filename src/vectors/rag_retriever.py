"""
Semantic Portfolio RAG Context Injector.
Semantically aligns project requirements with developer case studies, metrics, and proof points.
"""

import logging
import time
from typing import Any

from src.models.profile import UserProfile, get_default_profile
from src.vectors.engine import DenseVectorEngine
from src.vectors.schemas import (
    PortfolioRAGMatchItem,
    PortfolioRAGRequest,
    PortfolioRAGResponse,
)

logger = logging.getLogger("SemanticPortfolioRAG")


class SemanticPortfolioRAG:
    """
    Retrieval-Augmented Generation (RAG) context engine mapping opportunity requirements to developer proof points.
    """

    def __init__(self, embedder: DenseVectorEngine | None = None):
        self.embedder = embedder or DenseVectorEngine()

    def retrieve_context(
        self,
        req: PortfolioRAGRequest,
        profile: UserProfile | None = None,
    ) -> PortfolioRAGResponse:
        """
        Semantically retrieve the most contextually relevant case studies and synthesize evidence paragraphs.
        """
        start_time = time.perf_counter()
        user_prof = profile or get_default_profile()
        portfolio_items = user_prof.portfolio or []

        # Vectorize project requirements
        query_text = f"{req.project_title}\n{req.project_description}\nSkills: {', '.join(req.target_skills)}"
        query_vec = self.embedder.embed_text(query_text)

        scored_items: list[tuple[float, dict[str, Any]]] = []

        for p in portfolio_items:
            p_dict: dict[str, Any] = (
                p.model_dump() if hasattr(p, "model_dump") else (p if isinstance(p, dict) else {})
            )
            title = p_dict.get("title", "")
            industry = p_dict.get("industry", "Production")
            techs = p_dict.get("technologies", [])
            outcomes = p_dict.get("outcomes", [])
            desc = p_dict.get("description", "")

            case_text = (
                f"{title} {industry} " f"{' '.join(techs)} " f"{' '.join(outcomes)} " f"{desc}"
            )
            case_vec = self.embedder.embed_text(case_text)
            sim = self.embedder.cosine_similarity(query_vec, case_vec)
            scored_items.append((sim, p_dict))

        # Sort by semantic similarity descending
        scored_items.sort(key=lambda x: x[0], reverse=True)

        matched: list[PortfolioRAGMatchItem] = []
        proof_snippets: list[str] = []

        for sim, p_dict in scored_items[: req.top_k]:
            title = p_dict.get("title", "Production System")
            ind = p_dict.get("industry", "Enterprise")
            techs = p_dict.get("technologies", [])
            outcomes = p_dict.get("outcomes", [])
            desc = p_dict.get("description", "")

            # Format citation snippet
            outcome_str = f" resulting in {', '.join(outcomes)}" if outcomes else ""
            citation = f"Engineered '{title}' ({ind}) using {', '.join(techs[:3])}{outcome_str}."

            matched.append(
                PortfolioRAGMatchItem(
                    title=title,
                    client_industry=ind,
                    technologies=techs,
                    quantitative_outcomes=outcomes,
                    summary_paragraph=desc,
                    semantic_similarity=round(max(0.0, sim), 4),
                    relevant_citation_snippet=citation,
                )
            )
            proof_snippets.append(citation)

        # Synthesize combined proof paragraph for proposal injection
        if matched:
            top = matched[0]
            top_tech = ", ".join(top.technologies[:3])
            top_outcome = (
                top.quantitative_outcomes[0]
                if top.quantitative_outcomes
                else "production-grade reliability"
            )
            proof_para = (
                f"In a similar project ('{top.title}'), I architected a robust system using {top_tech} "
                f"which delivered {top_outcome}. I will leverage this exact architectural pattern for {req.project_title}."
            )
        else:
            proof_para = (
                f"I bring extensive production experience in {', '.join(req.target_skills[:3]) or 'Python and FastAPI'}, "
                f"having built scalable, high-throughput microservices delivered on schedule."
            )

        duration = (time.perf_counter() - start_time) * 1000.0

        return PortfolioRAGResponse(
            project_title=req.project_title,
            matched_case_studies=matched,
            suggested_proof_paragraph=proof_para,
            retrieval_duration_ms=round(duration, 2),
        )


# Global Singleton RAG Instance
GLOBAL_PORTFOLIO_RAG = SemanticPortfolioRAG()
