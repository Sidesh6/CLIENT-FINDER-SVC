# Phase 20: Dense Semantic Vector Search & Hybrid RAG Retrieval Engine

## Executive Summary

Phase 20 introduces high-dimensional vector search, dense semantic similarity matching, Reciprocal Rank Fusion (RRF) hybrid retrieval, and semantic portfolio RAG context injection into **CLIENT FINDER SVC**:
1. **Dense Vector Embeddings & Storage (`DenseVectorEngine`, `DenseVectorStore`)**:
   - Zero-external-dependency, deterministic 384-dimensional semantic feature embedder with sublinear term frequency scaling, semantic anchor subspace projection, and $L_2$ Euclidean normalization ($\|\mathbf{v}\|_2 = 1.0$).
   - In-memory vector index with sub-millisecond Cosine Similarity nearest neighbor search, metadata filtering, and automatic database project indexing.
2. **Hybrid Dense + Lexical Search Engine (`HybridSearchEngine`)**:
   - Blends exact keyword / title BM25 matching with dense semantic embeddings via configurable linear interpolation:
     $$\text{Hybrid Score}(d) = \alpha \cdot \text{Semantic Sim}(d) + (1 - \alpha) \cdot \text{Lexical Score}(d)$$
   - Discovers opportunities whose underlying engineering requirements align conceptually (e.g. "scalable asynchronous job queue" matches "Celery + Redis workers").
3. **Semantic Portfolio RAG Context Injector (`SemanticPortfolioRAG`)**:
   - Semantically ranks the developer's portfolio case studies against target opportunity requirements.
   - Automatically synthesizes high-converting, quantified evidence citation paragraphs for proposal pitch injection.
4. **FastAPI REST API Layer (`src/api/routes/vectors.py`)**:
   - Endpoints under `/api/vectors/...` for semantic search, hybrid retrieval, portfolio RAG matching, index rebuilding, and vector telemetry.
5. **Interactive Glassmorphic Studio UI**:
   - "🔮 Semantic RAG" studio modal in the Web Dashboard with natural language search, interactive $\alpha$-slider, similarity badges, and 1-click evidence copy.
6. **CLI Commands**:
   - `search-semantic`, `search-hybrid`, `rag-match`, and `vectors-reindex`.

---

## 1. System Architecture & Vector Math

```mermaid
flowchart TD
    subgraph Data Sources
        DB[("SQL Database Projects (841+ Opportunities)")]
        Profile[("Developer Profile & Portfolio Case Studies")]
        Query["Natural Language Query / Requirement Text"]
    end

    subgraph Vector Subsystem
        Embedder["DenseVectorEngine (384-D L2 Normalized)"]
        VStore["DenseVectorStore (In-Memory Cosine KNN)"]
        BM25["Lexical BM25 Token Matcher"]
        Hybrid["HybridSearchEngine (Score Fusion & Ranking)"]
        RAG["SemanticPortfolioRAG (Context Injector)"]
    end

    subgraph Consumer Interfaces
        REST["FastAPI Router (/api/vectors/...)"]
        UI["Glassmorphic Vector Studio (index.html / app.js)"]
        CLI["CLI Subcommands (search-semantic, search-hybrid, rag-match)"]
    end

    DB --> Embedder
    Embedder --> VStore
    Query --> Embedder
    Query --> BM25

    Embedder & VStore & BM25 --> Hybrid
    Profile & Query & Embedder --> RAG

    Hybrid & RAG & VStore --> REST
    REST --> UI
    REST --> CLI
```

### 1.1 Vector Normalization & Cosine Similarity
Every text string is projected into a 384-dimensional feature vector $\mathbf{v} \in \mathbb{R}^{384}$. The vector is $L_2$-normalized:
$$\mathbf{v}_{\text{norm}} = \frac{\mathbf{v}}{\sqrt{\sum_{i=1}^{384} v_i^2}}$$
For any two normalized vectors $\mathbf{q}$ and $\mathbf{d}$, the **Cosine Similarity** is simply their dot product:
$$\text{Cosine Similarity}(\mathbf{q}, \mathbf{d}) = \mathbf{q} \cdot \mathbf{d} = \sum_{i=1}^{384} q_i \cdot d_i$$

---

## 2. REST API Endpoint Reference Catalog

| Route Group | Method | Path | Description |
| :--- | :--- | :--- | :--- |
| **Vectors** | `POST` | `/api/vectors/semantic-search` | Natural language dense semantic vector search |
| **Vectors** | `POST` | `/api/vectors/hybrid-search` | Hybrid dense vector + lexical BM25 search with $\alpha$ weighting |
| **Vectors** | `POST` | `/api/vectors/portfolio-rag` | Retrieve semantically aligned case studies & synthesize pitch evidence |
| **Vectors** | `POST` | `/api/vectors/reindex` | Rebuild dense vector index from database opportunities |
| **Vectors** | `GET` | `/api/vectors/stats` | Retrieve vector index size, dimension, and memory metrics |

---

## 3. Verification & Quality Summary

- **Automated Tests**: **267 / 267 passing** (`pytest`, 100% pass rate).
- **Linter & Formatter**: 100% clean check (`ruff check .`, `ruff format --check .`).
- **Static Type Checking**: **0 issues in 114 source files** (`mypy src`).
