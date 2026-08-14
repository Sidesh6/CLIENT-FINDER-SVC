# Feature Documentation: REST API & Web Dashboard Service

**Project:** CLIENT FINDER SVC  
**Milestone:** Phase 8 — REST API & Web Dashboard Service  
**Status:** Complete & Verified (136/136 Tests Passing)  
**Date:** August 2026  

---

## 1. Executive Summary

The **REST API & Web Dashboard Service (Phase 8)** exposes all backend discovery, requirement extraction, skill matching, multi-factor scoring, multi-channel notification, and context-aware proposal generation systems via an asynchronous **FastAPI REST API** and a **modern, glassmorphic single-page web dashboard**.

### Core Highlights:
1. **Full-Featured RESTful API:** 16+ production endpoints providing complete coverage over projects, opportunities, full-text searches, proposals, user profiles, collectors, and notification channels.
2. **Interactive Glassmorphic Dark Dashboard (`src/api/static/`):** Real-time opportunity feed, live search debouncing, category/status/score filters, live KPI counters, and interactive modals.
3. **1-Click AI Proposal Generator Modal:** Switch between 5 strategic pitch angles (`Technical Expert`, `Fast Delivery`, `Value & ROI`, `Portfolio Proof`, `Consultative Advisor`) with live quality scoring and 1-click clipboard copying.
4. **On-Demand Lead Harvesting:** Trigger external collectors (e.g. Hacker News) directly from the API or web interface with instant extraction and automated scoring.
5. **Interactive OpenAPI / Swagger Documentation:** Available at `/docs` and `/redoc`.

---

## 2. API Endpoints Reference

### 2.1 Health & Diagnostics
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` / `/api/health` | System health check, database connectivity, and total opportunity counts. |

### 2.2 Projects & Opportunity Management
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/projects` | Paginated listing with multi-facet filtering (`category`, `source`, `min_score`, `status`, `skill`). |
| `GET` | `/api/projects/{id}` | Detailed project view with extracted requirements and opportunity score breakdown. |
| `PATCH` | `/api/projects/{id}/status` | Update workflow status (`NEW`, `REVIEWED`, `APPLIED`, `ACCEPTED`, `REJECTED`, `ARCHIVED`). |
| `DELETE` | `/api/projects/{id}` | Remove or delete a project and its evaluations. |

### 2.3 Search & Aggregations
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/search` | Full-text keyword search across titles, descriptions, skills, and sources with filters. |
| `GET` | `/api/opportunities/top` | Top-ranked opportunities sorted by composite score. |
| `GET` | `/api/opportunities/stats` | KPI statistics (total leads, priority tiers, avg scores, top skills, category distribution). |
| `POST` | `/api/opportunities/score-all` | Batch evaluate all projects in the database against the active developer profile. |

### 2.4 Proposal Generation
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/proposals/generate` | Generate tailored proposal using a specified pitch angle, tone, pricing preference, and custom instructions. |
| `POST` | `/api/proposals/auto` | Auto-detect optimal pitch angle and synthesize proposal in a single call. |

### 2.5 Profile Management
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/profile` | Retrieve active developer profile, rates, and skill competencies. |
| `PUT` | `/api/profile` | Update profile headline, target hourly rates, minimum rates, bio, and skills. |

### 2.6 Collectors & Notifications
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/collectors` | List registered opportunity harvesting collectors. |
| `POST` | `/api/collectors/trigger` | Trigger live scraping, requirement extraction, and multi-factor scoring. |
| `POST` | `/api/notifications/test` | Test dispatch an opportunity alert across active channels. |
| `POST` | `/api/notifications/broadcast/{id}` | Broadcast an alert for a specific project opportunity. |

---

## 3. Web Dashboard Interface (`src/api/static/`)

The web dashboard is delivered as a zero-dependency, ultra-fast single-page web app at `http://127.0.0.1:8000/`.

- **Design System:** Glassmorphism (`backdrop-filter: blur(16px)`), curated dark theme (`#090d16`), vibrant neon accents (Indigo, Emerald, Violet, Amber).
- **Typography:** `Outfit` for prominent typography and `Inter` for data density.
- **Micro-Interactions:** Smooth slide-over drawer for profile customization, animated lead harvesting states, toast alerts, and responsive grid layouts.

---

## 4. Verification & Testing

### 4.1 Automated Test Suite (`pytest`)
All **136 tests** pass with 100% success rate:

```text
======================= 136 passed, 1 warning in 9.30s ========================
```

| Test File | Tests | Scope |
|---|---|---|
| [`tests/unit/test_api.py`](file:///c:/PRIVATE%20PROJECTS/CLIENT-FINDER-SVC/tests/unit/test_api.py) | 18 tests | Health endpoints, project CRUD, keyword search, top opportunities & KPIs, proposal generation, profile management, collector execution, and static UI serving. |
| Other Subsystem Tests | 118 tests | Proposals, notifications, scoring, matching, extraction, database, and collectors. |

### 4.2 Static Analysis & Quality Validation
- **`mypy src/`**: 0 errors across 60 source files.
- **`ruff check`**: All checks passed cleanly.
- **`ruff format`**: All files formatted.

---

## 5. How to Run the Server

```powershell
# 1. Start the FastAPI development server
uvicorn src.api.main:app --reload --port 8000

# 2. Open the Web Dashboard in your browser
http://127.0.0.1:8000/

# 3. Access Interactive Swagger API Docs
http://127.0.0.1:8000/docs
```
