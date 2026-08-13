# Feature Explanation: Deduplication Engine & Database Persistence Layer

**Project:** CLIENT FINDER SVC  
**Milestones:** Phase 11 (Deduplication Engine) & Phase 12 (Database Layer)  
**Date:** August 2026  

---

## 1. Executive Summary

In a continuous project discovery architecture, collectors run periodically (e.g., every 30 minutes or daily). In any public source (like Hacker News, GitHub, or RSS feeds), the majority of items retrieved in subsequent runs will be identical to previous runs.

Without a dedicated deduplication and database persistence layer:
1. **Redundant Data:** The system would re-store duplicate project entries indefinitely.
2. **Wasted AI Spend:** Future LLM extraction and scoring calls would process the exact same opportunity repeatedly, multiplying token costs.
3. **Data Loss on Restart:** Projects only existed in transient Python memory during script execution.

This feature establishes **Phase 11 (Deduplication Engine)** and **Phase 12 (SQLAlchemy 2.0 Database Layer)** to ensure that every opportunity is fingerprinted, deduplicated, and stored persistently in SQLite (PostgreSQL ready).

---

## 2. Deduplication Engine Subsystem

📁 **File:** [`src/processors/deduplicator.py`](file:///c:/PRIVATE%20PROJECTS/CLIENT-FINDER-SVC/src/processors/deduplicator.py)

### 2.1. Canonical URL Normalization & Hashing
Different platforms and scrapers often point to the exact same opportunity via variations of a URL (e.g., trailing slashes, capitalizations, or marketing tracking parameters like `utm_source`).

* **`normalize_url(url: str) -> str`**:
  * Strips marketing and session trackers (`utm_source`, `utm_medium`, `utm_campaign`, `utm_term`, `utm_content`, `ref`, `fbclid`, `gclid`, `source`).
  * Lowercases the protocol scheme (`https://`) and hostname (`news.ycombinator.com`).
  * Sorts remaining functional query parameters deterministically.
  * Strips trailing slashes from the path.
* **`compute_url_hash(url: str) -> str`**:
  * Calculates a deterministic **SHA-256** hex digest of the canonical URL string for $O(1)$ database indexing and lookup.

### 2.2. Content Fingerprinting
Some opportunities appear across different URLs or are re-posted with identical descriptions under different threads.

* **`normalize_content(title: str, description: str) -> str`**:
  * Lowercases the title and description text.
  * Strips punctuation and non-alphanumeric noise.
  * Collapses multi-line breaks and redundant spaces into a single space.
* **`compute_content_hash(title: str, description: str) -> str`**:
  * Calculates a **SHA-256** content fingerprint from the normalized text.

### 2.3. Batch Deduplication
* **`ProjectDeduplicator.deduplicate_batch(projects, existing_url_hashes, existing_content_hashes)`**:
  * Cross-checks a incoming batch of raw project dictionaries against in-memory session caches AND existing database hashes.
  * Drops duplicates within the same batch and across historical runs.
  * Returns `(unique_projects, duplicate_count)`.

---

## 3. Database & Repository Subsystem

📁 **Directory:** [`src/database/`](file:///c:/PRIVATE%20PROJECTS/CLIENT-FINDER-SVC/src/database/)

### 3.1. SQLAlchemy 2.0 Declarative Models
📁 **File:** [`src/database/models.py`](file:///c:/PRIVATE%20PROJECTS/CLIENT-FINDER-SVC/src/database/models.py)

* **`ProjectRecord` (`projects` table):**
  * `id`: Auto-incrementing primary key.
  * `title`, `description`: Project details.
  * `source`: Source platform (e.g., "Hacker News").
  * `source_url`: Full link to the original opportunity.
  * `url_hash`: Unique SHA-256 indexed hash (guarantees DB-level uniqueness).
  * `content_hash`: Indexed SHA-256 content fingerprint.
  * `client_name`, `budget`, `currency`, `project_type`: Opportunity metadata.
  * `skills_json`: Serialized JSON array of extracted skills with a typed `@property def skills(self) -> list[str]` getter/setter.
  * `score`: Calculated opportunity rating (0–100).
  * `status`: Workflow state (`DISCOVERED`, `ANALYZED`, `APPLIED`, `ARCHIVED`).
  * `created_at`, `updated_at`: UTC timestamps.

* **`SourceRecord` (`sources` table):**
  * `id`, `name`, `source_type`, `is_active`, `created_at`.

* **`CollectionRunRecord` (`collection_runs` table):**
  * Logs execution metadata for every collector cycle: `source_name`, `started_at`, `completed_at`, `status`, `items_collected`, `items_saved`, `duplicates_skipped`, and `error_message`.

### 3.2. Engine & Session Management
📁 **File:** [`src/database/database.py`](file:///c:/PRIVATE%20PROJECTS/CLIENT-FINDER-SVC/src/database/database.py)

* **`get_engine(db_url)`**: Creates a SQLAlchemy engine (defaulting to local `sqlite:///client_finder.db`, or PostgreSQL via `DATABASE_URL`).
* **`init_db(engine)`**: Idempotently creates database tables on startup.
* **`get_db_session(session_factory)`**: Context manager providing automatic transaction commit and rollback on exceptions.

### 3.3. Repository Pattern
📁 **File:** [`src/database/repository.py`](file:///c:/PRIVATE%20PROJECTS/CLIENT-FINDER-SVC/src/database/repository.py)

* **`ProjectRepository`**:
  * `save_project(project: Project) -> ProjectRecord | None`
  * `save_many(projects: list[Project]) -> tuple[list[ProjectRecord], int]` (efficient batch insertion that skips existing URL or content hashes).
  * `get_all_url_hashes() -> set[str]` & `get_all_content_hashes() -> set[str]`
  * `get_by_id(id)` & `get_by_url_hash(url_hash)`
  * `list_projects(limit, offset, source, min_score)` (supports filtered querying)
  * `count(source)` (total count metrics)
* **`CollectionRunRepository`**:
  * `start_run(source_name)` & `complete_run(run_id, ...)`

---

## 4. End-to-End Discovery Pipeline

```text
       [ Public Source (e.g. Hacker News) ]
                        │
                        ▼
      [ Step 1: Collector (HttpClient) ]
                        │
                        ▼ (Raw Project Dicts)
      [ Step 2: Cleaner (ProjectCleaner) ]
                        │
                        ▼ (Sanitized Dicts)
    [ Step 3: Deduplicator (ProjectDeduplicator) ]
                        │  ← Checks URL & Content Hashes vs DB
                        ▼ (Unique Dicts)
     [ Step 4: Extractor (ProjectExtractor) ]
                        │
                        ▼ (Pydantic Project Models)
  [ Step 5: Database Layer (ProjectRepository) ]
                        │
                        ▼
            [ SQLite / PostgreSQL DB ]
```

---

## 5. Testing & Verification

### Automated Unit Tests (`pytest`)
Expanded the test suite to **42 passing tests**:
* [`tests/unit/test_deduplicator.py`](file:///c:/PRIVATE%20PROJECTS/CLIENT-FINDER-SVC/tests/unit/test_deduplicator.py): Tests URL normalization, tracking parameter stripping, content hashing, and duplicate filtering.
* [`tests/unit/test_database.py`](file:///c:/PRIVATE%20PROJECTS/CLIENT-FINDER-SVC/tests/unit/test_database.py): Tests in-memory SQLite table creation, CRUD operations, duplicate prevention, filtering, and collection run logs.
* [`tests/test_pipeline.py`](file:///c:/PRIVATE%20PROJECTS/CLIENT-FINDER-SVC/tests/test_pipeline.py): Full integration test executing all 5 stages from collector to SQLite database.

### Live Smoke Verification (`scripts/test_hn_live.py`)
Tested with actual live Hacker News data:
* **First Run:** Discovered 5 live opportunities $\rightarrow$ **Stored 5 records in SQLite (`client_finder.db`)**.
* **Second Run (Immediate):** Discovered 5 opportunities $\rightarrow$ **Deduplicator detected all 5 existing URL hashes $\rightarrow$ 0 re-saved, 5 skipped**.

---

## 6. How to Run

1. **Execute Test Suite:**
   ```powershell
   pytest -v
   ```
2. **Execute Static Analysis & Formatting:**
   ```powershell
   ruff check .
   ruff format --check src/ tests/ scripts/
   mypy src
   ```
3. **Execute Live Discovery & Storage:**
   ```powershell
   python scripts/test_hn_live.py
   ```
