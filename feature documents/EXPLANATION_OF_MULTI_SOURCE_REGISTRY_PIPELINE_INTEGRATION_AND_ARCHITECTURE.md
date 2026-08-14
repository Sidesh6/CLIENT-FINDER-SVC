# Multi-Source Registry Pipeline Integration & System Architecture Suite

## Executive Summary

Phase 12 completes the multi-source orchestration layer by wiring the centralized `CollectorRegistry` directly into `PipelineCoordinator`, establishing automated continuous health telemetry across all active harvesters, and providing a comprehensive system architecture reference.

---

## 1. Architectural Overview & Ingestion Flow

```mermaid
flowchart TD
    subgraph Multi-Source Ingestion
        HN["Hacker News Collector"]
        ROK["RemoteOK Collector"]
        WWR["WeWorkRemotely Collector"]
        RSS["Generic RSS / Atom Collector"]
        REG["CollectorRegistry (Health & Circuit Breaker)"]
    end

    subgraph Pipeline Orchestration
        Coord["PipelineCoordinator (run_cycle)"]
        Sources["result.sources_used Tracking"]
        TelSuccess["registry.record_success(source, count)"]
        TelFail["registry.record_failure(source, error)"]
    end

    subgraph Processing, Scoring & Conversion
        Clean["Data Cleaning & Deduplication"]
        Extract["AI / Heuristic Extraction"]
        Score["Multi-Factor Scoring (0-100)"]
        Alert["Multi-Channel Alerts (>=75)"]
        Prop["Portfolio Case-Study RAG Proposals"]
        Track["12-State Application Tracking"]
    end

    REG -->|get_active_collectors| Coord
    Coord --> HN
    Coord --> ROK
    Coord --> WWR
    Coord --> RSS
    HN --> TelSuccess
    ROK --> TelSuccess
    WWR --> TelFail
    TelSuccess --> REG
    TelFail --> REG
    Coord --> Sources
    Coord --> Clean
    Clean --> Extract
    Extract --> Score
    Score --> Alert
    Score --> Prop
    Prop --> Track
```

---

## 2. Key Technical Improvements

### 2.1 Unified Registry Resolution in `PipelineCoordinator`
- Previously, `PipelineCoordinator` defaulted to only `[HackerNewsCollector()]`, bypassing other active sources.
- Now, when no explicit list of collectors is provided, `PipelineCoordinator` queries `self.registry.get_active_collectors()`, ensuring all enabled, healthy sources are queried during each harvest cycle.

### 2.2 Continuous Collector Health Telemetry
- During every harvest cycle, after querying each collector:
  - On success: `registry.record_success(col_name, len(items))` records total items harvested, updates `last_scrape_at`, increments `success_count`, and resets `consecutive_failures` to 0.
  - On failure: `registry.record_failure(col_name, str(exc))` logs `last_error`, increments `failure_count`, and increments `consecutive_failures`.
- When `consecutive_failures >= 3`, the circuit breaker trips, isolating the failing feed and preventing pipeline blockages.

### 2.3 `PipelineRunResult.sources_used`
- The pipeline telemetry dataclass now tracks all sources queried during a cycle (`sources_used: list[str]`), providing full visibility in logging, CLI reports, and REST telemetry.

---

## 3. End-to-End System Specifications

### 3.1 15-Module Core Architecture
| Subpackage | Responsibilities |
| :--- | :--- |
| `src/ai/` | LLM client integrations (OpenAI, Gemini, Ollama) and extraction schemas (`ExtractedRequirements`). |
| `src/analytics/` | Conversion funnel analytics (`AnalyticsEngine`), velocity metrics, and Bayesian win-probability calibration. |
| `src/api/` | FastAPI REST service (`/api/...`), 11 route routers, and modern glassmorphic web dashboard. |
| `src/collectors/` | Multi-source collectors (HN, RemoteOK, WWR, RSS/Atom) and `CollectorRegistry`. |
| `src/database/` | SQLAlchemy 2.0 models (`ProjectModel`, `OpportunityModel`, `SourceModel`, `ApplicationModel`) and repositories. |
| `src/matching/` | Skill matching engine (`SkillMatcher`), hierarchical synonym dictionary, and implied skill graph. |
| `src/models/` | Domain entities: `Project`, `UserProfile`, `SkillProficiency`, `PortfolioProject`. |
| `src/notifications/`| Multi-channel dispatcher (Discord, Slack, SMTP Email, Desktop toasts) with rate limiting. |
| `src/processors/` | Text cleaning, unicode normalization, HTML stripping, and URL extraction. |
| `src/proposal/` | AI proposal generator, dynamic portfolio case-study RAG, and 5 pitch angle strategies. |
| `src/scheduler/` | `PipelineCoordinator` and background recurring daemon thread `PipelineScheduler`. |
| `src/scoring/` | Multi-factor opportunity scoring algorithms ($S_{\text{skill}}, S_{\text{budget}}, S_{\text{client}}, S_{\text{comp}}, S_{\text{complex}}, S_{\text{fresh}}$). |
| `src/tracking/` | 12-stage application lifecycle state machine (`ApplicationTracker`). |
| `src/utils/` | Retry-enabled `HttpClient`, date/currency conversion, and logging formatters. |

---

## 4. Verification & Testing Summary

- **183 Unit Tests Passing**: 100% test pass rate across all modules.
- **Linter & Types**: Passed `ruff check`, `ruff format`, and `mypy src/` with zero errors across 78 source files.
- **Live Ingestion Verified**: Real HTTP tests confirmed against Hacker News, RemoteOK, and WeWorkRemotely feeds.
