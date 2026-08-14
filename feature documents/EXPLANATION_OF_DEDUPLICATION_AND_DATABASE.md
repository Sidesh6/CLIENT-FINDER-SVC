# Feature Documentation: Deduplication Engine & Database Persistence Layer

**Project:** CLIENT FINDER SVC  
**Components:** Deduplication Engine (`src/processors/deduplicator.py`) & SQLAlchemy 2.0 Database Layer (`src/database/`)  
**Date:** August 2026  
**Status:** Complete & Verified (52/52 Tests Passing)  

---

## 1. Executive Summary

In a continuous project discovery pipeline, collectors run on periodic schedules (e.g., every 30 minutes or daily). Across public job feeds and developer forums (such as Hacker News, freelance boards, and RSS feeds), a significant portion of opportunities encountered in subsequent polling cycles will be identical or cross-posted duplicates.

Without a robust deduplication and relational storage architecture:
1. **Data Redundancy:** Multiple identical project records pollute the database.
2. **Wasted AI Spend:** Subsequent LLM requirement extraction and scoring prompts would process identical listings repeatedly, dramatically inflating API costs.
3. **Transient State Loss:** Without persistent storage, collected data is lost when Python execution terminates.

This document outlines the **Deduplication Subsystem** and **SQLAlchemy 2.0 Persistence Layer**, designed to uniquely fingerprint, persist, and manage opportunities seamlessly across SQLite and PostgreSQL.

---

## 2. Relational Database Architecture

📁 **Directory:** [`src/database/`](file:///c:/PRIVATE%20PROJECTS/CLIENT-FINDER-SVC/src/database/)

```text
  ┌─────────────────────────────────┐
  │         sources (Table)         │
  ├─────────────────────────────────┤
  │ id: Integer (PK)                │
  │ name: String (Unique)           │
  │ type: String                    │
  │ base_url: String (Nullable)     │
  │ enabled: Boolean                │
  │ collection_interval: Integer    │
  │ created_at, updated_at: DateTime│
  └───────────────┬─────────────────┘
                  │ 1:N
                  ▼
  ┌─────────────────────────────────┐          ┌──────────────────────────────────┐
  │        projects (Table)         │   1:1    │      opportunities (Table)       │
  ├─────────────────────────────────┤─────────►├──────────────────────────────────┤
  │ id: Integer (PK)                │          │ id: Integer (PK)                 │
  │ source_id: Integer (FK -> sources)         │ project_id: Integer (FK, Unique) │
  │ source: String (Index)          │          │ skill_match_score: Float         │
  │ external_id: String (Index)     │          │ budget_score: Float              │
  │ title: String (Index)           │          │ client_score: Float              │
  │ description: Text               │          │ competition_score: Float         │
  │ source_url: String (Unique)     │          │ complexity_score: Float          │
  │ url_hash: String (Unique Index) │          │ freshness_score: Float           │
  │ content_hash: String (Index)    │          │ win_probability: Float           │
  │ client_name: String             │          │ overall_score: Float (Index)     │
  │ budget, currency, project_type  │          │ explanation: Text                │
  │ skills: JSON                    │          │ created_at, updated_at: DateTime │
  │ status: String (DISCOVERED...)  │          └──────────────────────────────────┘
  │ score: Float                    │
  │ raw_data: JSON                  │          ┌──────────────────────────────────┐
  │ posted_at, deadline: DateTime   │          │     collection_runs (Table)      │
  │ created_at, updated_at: DateTime│          ├──────────────────────────────────┤
  └─────────────────────────────────┘          │ id: Integer (PK)                 │
                                               │ source: String (Index)           │
                                               │ status: String (RUNNING/SUCCESS) │
                                               │ items_collected: Integer         │
                                               │ items_saved: Integer             │
                                               │ duplicates_skipped: Integer      │
                                               │ error_message: Text              │
                                               │ started_at, completed_at: DateTime
                                               └──────────────────────────────────┘
```

---

## 3. Declarative ORM Models

📁 **File:** [`src/database/models.py`](file:///c:/PRIVATE%20PROJECTS/CLIENT-FINDER-SVC/src/database/models.py)

Built with modern SQLAlchemy 2.0 type annotations (`Mapped[...]` and `mapped_column(...)`):

### 3.1. `SourceModel` (`sources` table)
- Manages source platforms (e.g. Hacker News, Web scrapers, Upwork API).
- Tracks `enabled` flag, polling frequency (`collection_interval`), and base endpoints.
- Relationship: `projects = relationship("ProjectModel", back_populates="source_model", cascade="all, delete-orphan")`.

### 3.2. `ProjectModel` / `ProjectRecord` (`projects` table)
- Core entity storing validated project opportunity data.
- **Dual Unique Indices**:
  - `source_url`: Full canonical link to project opportunity.
  - `url_hash`: Deterministic SHA-256 hash of normalized URL ($O(1)$ fast indexed lookups).
- `content_hash`: SHA-256 fingerprint generated from normalized `title + description`.
- `skills`: Serialized JSON array of skills with `@property def skills_json(self) -> str` compatibility.
- **Bidirectional Pydantic Serialization**:
  - `to_pydantic() -> Project`: Converts ORM entity into validated Pydantic model.
  - `ProjectModel.from_pydantic(Project)`: Factory constructor computing hashes automatically.

### 3.3. `OpportunityModel` (`opportunities` table)
- 1-to-1 cascade child of `ProjectModel`.
- Preserves explainable score breakdowns (`skill_match_score`, `budget_score`, `client_score`, `overall_score`, `explanation`).

### 3.4. `CollectionRunRecord` (`collection_runs` table)
- Audit log tracking scraping executions, throughput metrics (`items_collected`, `items_saved`, `duplicates_skipped`), errors, and timestamps.

---

## 4. Multi-Level Deduplication Engine

📁 **File:** [`src/processors/deduplicator.py`](file:///c:/PRIVATE%20PROJECTS/CLIENT-FINDER-SVC/src/processors/deduplicator.py)

The deduplication engine protects the pipeline at multiple layers:

### 4.1. Canonical URL Normalization & Hashing
```python
normalize_url(url: str) -> str
compute_url_hash(url: str) -> str
```
- **Tracking Parameter Removal**: Strips marketing noise (`utm_source`, `utm_medium`, `utm_campaign`, `utm_term`, `utm_content`, `ref`, `fbclid`, `gclid`, `source`).
- **Hostname Normalization**: Lowercases scheme and network hostname.
- **Path Cleaning**: Normalizes trailing slashes and parameter order deterministically.
- **Hashing**: Produces a SHA-256 digest string for indexing.

### 4.2. Content Fingerprinting
```python
normalize_content(title: str, description: str) -> str
compute_content_hash(title: str, description: str) -> str
```
- Strips punctuation, non-alphanumeric noise, and collapses multi-line formatting.
- Converts to lowercase and hashes `title + description` into a deterministic SHA-256 fingerprint.
- Detects cross-posted or duplicate projects even if the source URL differs.

### 4.3. Batch Filtering (`ProjectDeduplicator`)
- Maintains in-memory session caches (`_seen_url_hashes`, `_seen_content_hashes`).
- Filters incoming batches against existing database hashes:
  ```python
  unique_projects, duplicate_count = deduplicator.deduplicate_batch(
      projects,
      existing_url_hashes=db_url_hashes,
      existing_content_hashes=db_content_hashes,
  )
  ```

---

## 5. Repository Pattern Implementation

📁 **File:** [`src/database/repository.py`](file:///c:/PRIVATE%20PROJECTS/CLIENT-FINDER-SVC/src/database/repository.py)

Encapsulates all database querying and transactional mutations:

| Repository Class | Primary Methods | Description |
|---|---|---|
| **`ProjectRepository`** | `add()`, `save_project()` | Persists single project, skipping if duplicate. |
| | `add_many()`, `save_many()` | Batch persistence with duplicate filtering. |
| | `is_duplicate(url, hash)` | Checks URL and content fingerprint existence. |
| | `get_by_id()`, `get_by_url()`, `get_by_url_hash()` | Targeted primary and unique key lookups. |
| | `get_all_url_hashes()`, `get_all_content_hashes()` | Fast sets for batch pre-filtering. |
| | `list_projects(status, source, min_score, limit, offset)` | Paginated and filtered querying. |
| | `update_status()`, `update_score()`, `delete()`, `count()` | Lifecycle and metric mutations. |
| **`SourceRepository`** | `get_or_create(name, type)` | Retrieves or registers external data sources. |
| | `list_sources(enabled_only)`, `set_enabled()` | Source configuration management. |
| **`OpportunityRepository`** | `create_or_update()` | Scores opportunity and syncs with parent project. |
| | `list_top_opportunities(min_score, limit)` | Queries top-ranked opportunities. |
| **`CollectionRunRepository`**| `start_run()`, `complete_run()`, `fail_run()`, `get_recent_runs()` | Collector audit telemetry and metrics. |

---

## 6. Engine & Session Management

📁 **Files:** [`src/database/database.py`](file:///c:/PRIVATE%20PROJECTS/CLIENT-FINDER-SVC/src/database/database.py) / [`src/database/session.py`](file:///c:/PRIVATE%20PROJECTS/CLIENT-FINDER-SVC/src/database/session.py)

- **`get_engine()`**: Configures SQLite (`data/client_finder.db` or `:memory:`) with `check_same_thread=False` and auto-creates storage directories. Connects to PostgreSQL when `DATABASE_URL` is supplied.
- **`get_db_session()`**: Context manager providing atomic transactions:
  ```python
  with get_db_session(engine=engine) as session:
      repo = ProjectRepository(session)
      repo.add(project)
      # Automatically commits upon exit, or rolls back on exceptions
  ```
- **`init_db()` & `drop_db()`**: Idempotent table creation and test teardown utilities.

---

## 7. End-to-End Discovery Pipeline

```text
       [ External Source (e.g. Hacker News) ]
                         │
                         ▼
        [ Stage 1: Collector (HttpClient) ]
                         │
                         ▼ (Raw Opportunity Dicts)
        [ Stage 2: Cleaner (ProjectCleaner) ]
                         │
                         ▼ (Sanitized Dicts)
     [ Stage 3: Deduplicator (ProjectDeduplicator) ]
                         │  ← Checks URL & Content Fingerprints vs DB
                         ▼ (Unique Dicts)
       [ Stage 4: Extractor (ProjectExtractor) ]
                         │
                         ▼ (Validated Pydantic Models)
     [ Stage 5: Database Layer (ProjectRepository) ]
                         │
                         ▼
            [ SQLite / PostgreSQL DB ]
```

---

## 8. Verification & Test Suite

### 8.1. Automated Tests (`pytest`)
**52 passing tests** with 100% pass rate:
- [`tests/test_pipeline.py`](file:///c:/PRIVATE%20PROJECTS/CLIENT-FINDER-SVC/tests/test_pipeline.py): End-to-end integration test (Collector $\rightarrow$ Cleaner $\rightarrow$ Deduplicator $\rightarrow$ Extractor $\rightarrow$ DB $\rightarrow$ Querying).
- [`tests/unit/test_database.py`](file:///c:/PRIVATE%20PROJECTS/CLIENT-FINDER-SVC/tests/unit/test_database.py): ORM mapping, Pydantic conversions, cascade deletes, and collection run logging.
- [`tests/unit/test_repository.py`](file:///c:/PRIVATE%20PROJECTS/CLIENT-FINDER-SVC/tests/unit/test_repository.py): Repository CRUD, duplicate rejection, pagination, score updates, and filtering.
- [`tests/unit/test_deduplicator.py`](file:///c:/PRIVATE%20PROJECTS/CLIENT-FINDER-SVC/tests/unit/test_deduplicator.py): URL normalization, tracking parameter stripping, and content hashing.

### 8.2. Live End-to-End Pipeline Smoke Test
Run live against the public Hacker News Algolia API:
```powershell
python scripts/test_db_pipeline.py
```
- **Pass 1:** Collected 5 live opportunities $\rightarrow$ Persisted 5 new records into `data/client_finder.db`.
- **Pass 2 (Immediate Re-run):** Collected 5 opportunities $\rightarrow$ Deduplication engine detected existing hashes $\rightarrow$ **0 new entries inserted, 5 duplicates skipped**.
- **Query Verification:** Successfully queried and printed stored records from the database table.

---

## 9. How to Execute

```powershell
# 1. Run full test suite
pytest -v

# 2. Run static typing and linter checks
mypy src
ruff check src tests scripts
ruff format --check src tests scripts

# 3. Execute live database discovery pipeline
python scripts/test_db_pipeline.py
```
