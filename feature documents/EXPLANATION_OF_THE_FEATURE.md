# Explanation of the Feature: HTTP Infrastructure & Hacker News Opportunity Discovery

**Project:** CLIENT FINDER SVC  
**Milestone:** Phase 3 (HTTP Infrastructure) & Phase 8 (First Real Public Collector)  
**Date:** August 2026  

---

## 1. Overview & Purpose

The goal of **CLIENT-FINDER-SVC** is not merely to build a scraper, but to create an **intelligent client and project discovery platform** that:
1. Continuously discovers public opportunities from diverse sources.
2. Resiliently handles network connections, rate limits, and remote downtime.
3. Cleans and normalizes unstructured public text into validated data models.
4. Prepares records for deduplication, database persistence, capability matching, and AI scoring.

This feature milestone bridges the gap between toy local mock data and real-world public opportunity discovery.

---

## 2. Feature Breakdown

### 2.1. Feature: Production-Grade HTTP Infrastructure
* **File:** [`src/utils/http_client.py`](file:///c:/PRIVATE%20PROJECTS/CLIENT-FINDER-SVC/src/utils/http_client.py)
* **Problem Addressed:** The initial client was a rudimentary wrapper around `httpx` with no resilience against network drops, rate limits, or intermittent server errors.
* **Key Capabilities Implemented:**
  1. **Exponential Backoff & Retries:** Automatically retries transient network failures (timeouts, 5xx server errors) up to 3 times before failing.
  2. **Rate Limit Management (HTTP 429):** Identifies when a server rate-limits requests, applies an exponential sleep interval, and retries gracefully.
  3. **Throttling (`rate_limit_delay`):** Allows collectors to enforce mandatory spacing between requests to comply with website policies and prevent IP bans.
  4. **Structured Exception Hierarchy:**
     * `HttpClientError`: Base exception for all client operations.
     * `HttpTimeoutError`: Raised when timeouts are exhausted.
     * `HttpRateLimitError`: Raised when rate limits persist after retries.
     * `HttpStatusError`: Contains status code and URL information.
  5. **Data Extraction Helpers:** Provides `get()`, `get_text()`, and `get_json()`.
  6. **Observability:** Logs latency (ms), HTTP status codes, and attempt counters.

---

### 2.2. Feature: Hacker News Public Collector
* **File:** [`src/collectors/hackernews_collector.py`](file:///c:/PRIVATE%20PROJECTS/CLIENT-FINDER-SVC/src/collectors/hackernews_collector.py)
* **Problem Addressed:** Needed our first real-world collector to pull live public opportunities without requiring complex auth or unstable browser scraping.
* **Key Capabilities Implemented:**
  1. **Public Algolia API Integration:** Communicates with `https://hn.algolia.com/api/v1/` to fetch stories and comments efficiently.
  2. **Dynamic Monthly Thread Discovery:** Uses `search_by_date` to find the latest active *"Ask HN: Freelancer? Seeking Freelancer?"* or *"Ask HN: Who is hiring?"* threads.
  3. **Hiring Intent Filtering:** Filters for client opportunities (`SEEKING FREELANCER`, `LOOKING FOR FREELANCER`, `HIRING`) and rejects candidate self-promotions (`SEEKING WORK`).
  4. **HTML Sanitization:** Converts HTML markup and entities (`&gt;`, `&#x27;`, `<p>`, `<a>`, `<br>`) into clean, normalized plain text.
  5. **Standardized Dictionary Output:** Outputs dictionaries containing `title`, `description`, `source`, `source_url`, `client_name`, and `project_type`.

---

### 2.3. Feature: End-to-End Pipeline Integration
* **Files:**
  * [`src/processors/cleaner.py`](file:///c:/PRIVATE%20PROJECTS/CLIENT-FINDER-SVC/src/processors/cleaner.py) (`ProjectCleaner`)
  * [`src/ai/extractor.py`](file:///c:/PRIVATE%20PROJECTS/CLIENT-FINDER-SVC/src/ai/extractor.py) (`ProjectExtractor`)
  * [`src/models/project.py`](file:///c:/PRIVATE%20PROJECTS/CLIENT-FINDER-SVC/src/models/project.py) (`Project` Pydantic model)
* **Pipeline Flow:**

```text
Hacker News (Algolia API)
            │
            ▼
   [HttpClient]            ← Handles retries, timeouts, rate-limits
            │
            ▼
[HackerNewsCollector]      ← Filters "SEEKING FREELANCER", cleans HTML
            │
            ▼ (Raw dicts)
   [ProjectCleaner]        ← Strips whitespace, normalizes fields
            │
            ▼ (Cleaned dicts)
  [ProjectExtractor]       ← Structures into fields
            │
            ▼
   [Project Model]         ← Validated Pydantic Object (Ready for DB / Scoring)
```

---

### 2.4. Feature: Testing & Live Smoke Verification
* **Automated Unit Tests:**
  * [`tests/unit/test_http_client.py`](file:///c:/PRIVATE%20PROJECTS/CLIENT-FINDER-SVC/tests/unit/test_http_client.py): 7 tests covering JSON parsing, status codes, 429 rate limit backoff, 500 error retries, and timeouts.
  * [`tests/unit/test_hackernews_collector.py`](file:///c:/PRIVATE%20PROJECTS/CLIENT-FINDER-SVC/tests/unit/test_hackernews_collector.py): 5 tests covering HTML stripping, thread discovery, comment parsing, and network error handling.
  * [`tests/test_pipeline.py`](file:///c:/PRIVATE%20PROJECTS/CLIENT-FINDER-SVC/tests/test_pipeline.py): End-to-end integration test verifying the full pipeline through Pydantic validation.
  * **Result:** **30 / 30 tests passing**.
* **Live Smoke Test Script:**
  * [`scripts/test_hn_live.py`](file:///c:/PRIVATE%20PROJECTS/CLIENT-FINDER-SVC/scripts/test_hn_live.py): A CLI utility that tests real-time connection to Hacker News, executes cleaning, and validates Pydantic models with actual live postings.

---

## 3. How to Run and Verify

1. **Run Automated Tests:**
   ```powershell
   pytest
   ```
2. **Run Static Type Checks and Linter:**
   ```powershell
   ruff check .
   mypy src
   ```
3. **Execute Live Opportunity Discovery:**
   ```powershell
   python scripts/test_hn_live.py
   ```
