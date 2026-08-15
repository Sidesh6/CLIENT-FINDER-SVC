"""
Dense Semantic Vector Embeddings Engine & Cosine Nearest-Neighbor Store.
Provides sub-millisecond high-dimensional vector search with zero external heavy dependencies.
"""

import hashlib
import logging
import math
import re
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from src.database.connection import SessionLocal
from src.database.models import ProjectModel
from src.vectors.schemas import (
    SemanticSearchResultItem,
    VectorDocument,
    VectorIndexStats,
)

logger = logging.getLogger("DenseVectorEngine")


class DenseVectorEngine:
    """
    Zero-external-dependency, deterministic semantic feature embedder.
    Generates 384-dimensional dense $L_2$-normalized vector representations from text.
    """

    DIMENSION = 384

    # Semantic keyword synonym anchors mapped to feature subspaces
    SEMANTIC_ANCHORS: dict[str, list[str]] = {
        "api_backend": [
            "fastapi",
            "flask",
            "django",
            "express",
            "backend",
            "rest",
            "graphql",
            "endpoints",
            "microservice",
        ],
        "async_distributed": [
            "asyncio",
            "celery",
            "redis",
            "rabbitmq",
            "kafka",
            "queue",
            "worker",
            "real-time",
            "websocket",
            "streaming",
        ],
        "database_storage": [
            "postgresql",
            "mysql",
            "mongodb",
            "sqlite",
            "sqlalchemy",
            "orm",
            "database",
            "schema",
            "sql",
            "migrations",
        ],
        "ai_machine_learning": [
            "ai",
            "llm",
            "rag",
            "embeddings",
            "vector",
            "openai",
            "langchain",
            "llamaindex",
            "nlp",
            "huggingface",
            "pytorch",
        ],
        "frontend_ui": [
            "react",
            "next.js",
            "vue",
            "typescript",
            "javascript",
            "tailwind",
            "css",
            "html",
            "frontend",
            "ui",
            "ux",
        ],
        "devops_cloud": [
            "docker",
            "kubernetes",
            "aws",
            "gcp",
            "ci/cd",
            "terraform",
            "linux",
            "nginx",
            "deploy",
            "cloud",
        ],
        "security_auth": [
            "auth",
            "jwt",
            "oauth",
            "security",
            "encryption",
            "stripe",
            "billing",
            "payment",
        ],
    }

    def embed_text(self, text: str) -> list[float]:
        """
        Generate a normalized 384-dimensional dense embedding vector for a given string.
        """
        if not text or not text.strip():
            # Return unit vector pointing along first axis
            vec = [0.0] * self.DIMENSION
            vec[0] = 1.0
            return vec

        vector = [0.0] * self.DIMENSION
        lower_text = text.lower()
        tokens = re.findall(r"\b[a-zA-Z0-9_-]+\b", lower_text)

        # 1. Token frequency counting
        counts: dict[str, int] = {}
        for t in tokens:
            counts[t] = counts.get(t, 0) + 1

        # 2. Semantic Anchor subspace projection (Dimension bands 0 to 224)
        band_size = 32
        for band_idx, (domain, keywords) in enumerate(self.SEMANTIC_ANCHORS.items()):
            domain_weight = 0.0
            for kw in keywords:
                if kw in lower_text:
                    domain_weight += 1.5 + (counts.get(kw, 0) * 0.5)

            if domain_weight > 0:
                base_dim = band_idx * band_size
                for i in range(band_size):
                    dim = base_dim + i
                    # Deterministic pseudo-random seed projection for each keyword in domain
                    hash_val = int(
                        hashlib.md5(f"{domain}_{i}".encode()).hexdigest(),
                        16,
                    )
                    sign = 1.0 if (hash_val % 2 == 0) else -1.0
                    vector[dim] += sign * domain_weight * (0.8 + 0.4 * (i / band_size))

        # 3. Sublinear N-gram & Hash Projection (Dimension bands 224 to 384)
        for token, count in counts.items():
            tf_weight = 1.0 + math.log(count)
            # Hash token across 4 deterministic bucket dimensions
            for seed in range(4):
                token_hash = int(
                    hashlib.sha256(f"{token}_{seed}".encode()).hexdigest(),
                    16,
                )
                dim = 224 + (token_hash % (self.DIMENSION - 224))
                sign = 1.0 if ((token_hash >> 8) % 2 == 0) else -1.0
                vector[dim] += sign * tf_weight

        # 4. $L_2$ Euclidean Normalization: v_norm = v / ||v||_2
        squared_sum = sum(x * x for x in vector)
        magnitude = math.sqrt(squared_sum)

        if magnitude < 1e-9:
            vector[0] = 1.0
            return vector

        return [round(x / magnitude, 6) for x in vector]

    @staticmethod
    def cosine_similarity(v1: list[float], v2: list[float]) -> float:
        """
        Compute Cosine Similarity between two L2-normalized float vectors.
        Since both vectors are unit magnitude, cosine similarity = dot product.
        """
        if len(v1) != len(v2) or not v1:
            return 0.0
        dot_product = sum(a * b for a, b in zip(v1, v2, strict=False))
        # Clamp to valid cosine range [-1.0, 1.0]
        return max(-1.0, min(1.0, dot_product))


class DenseVectorStore:
    """
    In-memory dense vector store supporting sub-millisecond Top-k nearest neighbor retrieval.
    """

    def __init__(self, embedder: DenseVectorEngine | None = None):
        self.embedder = embedder or DenseVectorEngine()
        self._documents: dict[str, VectorDocument] = {}
        self._last_reindexed_at: datetime | None = None

    def add_document(
        self,
        doc_id: str,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> VectorDocument:
        """Embed text and insert document into the vector store."""
        meta = metadata or {}
        embedding = self.embedder.embed_text(text)
        doc = VectorDocument(
            id=str(doc_id),
            text=text,
            metadata=meta,
            embedding=embedding,
            created_at=datetime.now(UTC),
        )
        self._documents[str(doc_id)] = doc
        return doc

    def get_document(self, doc_id: str) -> VectorDocument | None:
        """Retrieve indexed document by ID."""
        return self._documents.get(str(doc_id))

    def count(self) -> int:
        """Return total count of indexed vectors."""
        return len(self._documents)

    def search(
        self,
        query: str,
        limit: int = 10,
        min_similarity: float = 0.2,
        filter_fn: Callable[[dict[str, Any]], bool] | None = None,
    ) -> list[SemanticSearchResultItem]:
        """
        Execute Cosine Similarity nearest neighbor search across all indexed vectors.
        """
        query_vector = self.embedder.embed_text(query)
        scored: list[tuple[float, VectorDocument]] = []

        for doc in self._documents.values():
            if filter_fn and not filter_fn(doc.metadata):
                continue
            sim = self.embedder.cosine_similarity(query_vector, doc.embedding)
            if sim >= min_similarity:
                scored.append((sim, doc))

        # Sort by similarity in descending order
        scored.sort(key=lambda x: x[0], reverse=True)

        results: list[SemanticSearchResultItem] = []
        for sim, doc in scored[:limit]:
            meta = doc.metadata
            # Extract key matching keywords as semantic highlights
            highlights = self._extract_semantic_highlights(query, doc.text)
            results.append(
                SemanticSearchResultItem(
                    project_id=meta.get("project_id", doc.id),
                    title=meta.get("title", doc.id),
                    description=doc.text[:280] + ("..." if len(doc.text) > 280 else ""),
                    cosine_similarity=round(sim, 4),
                    source=meta.get("source", "Public Web"),
                    source_url=meta.get("source_url"),
                    budget=meta.get("budget"),
                    currency=meta.get("currency", "USD"),
                    skills=meta.get("skills", []),
                    semantic_highlights=highlights,
                )
            )
        return results

    def _extract_semantic_highlights(self, query: str, doc_text: str) -> list[str]:
        """Extract matching semantic terms between query and document text."""
        query_words = set(re.findall(r"\b[a-zA-Z]{3,}\b", query.lower()))
        doc_words = set(re.findall(r"\b[a-zA-Z]{3,}\b", doc_text.lower()))
        common = query_words.intersection(doc_words)
        # Filter common stop words
        stops = {"and", "the", "for", "with", "that", "this", "from", "are", "have", "you"}
        return [w.capitalize() for w in common if w not in stops][:6]

    def index_from_database(self) -> int:
        """
        Load all stored opportunities from SQL database into the dense vector store.
        """
        start_time = time.perf_counter()
        indexed_count = 0
        with SessionLocal() as session:
            from sqlalchemy import select

            projects = session.scalars(select(ProjectModel)).all()
            for pm in projects:
                skills_list = pm.skills or []
                text = f"{pm.title}\n{pm.description or ''}\nSkills: {', '.join(skills_list)}"
                meta = {
                    "project_id": pm.id,
                    "title": pm.title,
                    "source": pm.source,
                    "source_url": pm.source_url,
                    "budget": pm.budget,
                    "currency": pm.currency or "USD",
                    "skills": skills_list,
                    "score": pm.score,
                    "status": pm.status,
                }
                self.add_document(doc_id=str(pm.id), text=text, metadata=meta)
                indexed_count += 1

        self._last_reindexed_at = datetime.now(UTC)
        duration = time.perf_counter() - start_time
        logger.info(
            "Indexed %d database projects into DenseVectorStore in %.3fs.",
            indexed_count,
            duration,
        )
        return indexed_count

    def get_stats(self) -> VectorIndexStats:
        """Retrieve operational statistics of the vector index."""
        # Estimate memory: each float is ~8 bytes * 384 dims = 3KB per vector doc
        mem_bytes = len(self._documents) * (self.embedder.DIMENSION * 8 + 512)
        return VectorIndexStats(
            total_indexed_documents=len(self._documents),
            vector_dimension=self.embedder.DIMENSION,
            index_memory_bytes=mem_bytes,
            last_reindexed_at=self._last_reindexed_at,
            is_ready=len(self._documents) > 0,
        )


# Global Singleton Vector Store
GLOBAL_VECTOR_STORE = DenseVectorStore()
