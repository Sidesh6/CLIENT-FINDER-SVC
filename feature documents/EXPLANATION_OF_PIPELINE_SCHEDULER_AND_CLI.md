# Feature Document: Background Scheduler, Pipeline Coordinator & CLI Service

## 1. Overview & Architecture

The **Background Scheduler, Pipeline Coordinator, and CLI Service** forms the autonomous backbone of `CLIENT FINDER SVC`. It unifies all upstream intelligence components—Multi-Source Scraping, Heuristic & LLM Extraction, Taxonomy Normalization, Skill & Opportunity Scoring, Proposal Synthesis, and Multi-Channel Notifications—into an orchestratable, resilient, continuous background loop.

```
┌────────────────────────────────────────────────────────────────────────────┐
│                    PIPELINE COORDINATOR ARCHITECTURE                       │
└────────────────────────────────────────────────────────────────────────────┘
                                      │
  ┌───────────────────────────────────▼───────────────────────────────────┐
  │ 1. DATA COLLECTION: Fetch opportunities across all active collectors  │
  └───────────────────────────────────┬───────────────────────────────────┘
                                      │
  ┌───────────────────────────────────▼───────────────────────────────────┐
  │ 2. TEXT CLEANING: HTML stripping, formatting normalization            │
  └───────────────────────────────────┬───────────────────────────────────┘
                                      │
  ┌───────────────────────────────────▼───────────────────────────────────┐
  │ 3. METADATA & SKILL EXTRACTION: Multi-tier Heuristic + LLM Parser     │
  └───────────────────────────────────┬───────────────────────────────────┘
                                      │
  ┌───────────────────────────────────▼───────────────────────────────────┐
  │ 4. PERSISTENCE & DE-DUPLICATION: URL & Content Hash matching in DB   │
  └───────────────────────────────────┬───────────────────────────────────┘
                                      │
  ┌───────────────────────────────────▼───────────────────────────────────┐
  │ 5. OPPORTUNITY SCORING: 7-Factor Weighted Scoring against Profile    │
  └───────────────────────────────────┬───────────────────────────────────┘
                                      │
  ┌───────────────────────────────────▼───────────────────────────────────┐
  │ 6. NOTIFICATION DISPATCH: Discord, Slack, Desktop, Email alerts       │
  └───────────────────────────────────┬───────────────────────────────────┘
                                      │
  ┌───────────────────────────────────▼───────────────────────────────────┐
  │ 7. RUN AUDITING & METRICS: Audit logging & Telemetry recording        │
  └───────────────────────────────────────────────────────────────────────┘
```

---

## 2. Core Components

### 2.1 `PipelineCoordinator` (`src/scheduler/coordinator.py`)
- Coordinates the complete 8-step harvest, extraction, deduplication, scoring, notification, and audit cycle.
- Provides `run_cycle(dry_run=False, limit_per_collector=10, min_notification_score=75.0) -> PipelineRunResult`.
- Gracefully handles collector failures with individual try-catch blocks and error aggregation.

### 2.2 `PipelineScheduler` (`src/scheduler/service.py`)
- Background worker daemon thread executing periodic harvest loops without blocking REST API requests.
- Lifecycle controls:
  - `start()`: Launches thread worker.
  - `pause()`: Suspends automatic harvesting runs.
  - `resume()`: Un-pauses and resumes scheduled harvesting.
  - `stop()`: Cleanly shuts down daemon.
  - `trigger_cycle_now()`: Runs an immediate cycle outside normal timers.
  - `send_daily_digest(lookback_hours=24)`: Synthesizes top leads from the last $N$ hours and sends an executive briefing digest.

### 2.3 REST Endpoints (`src/api/routes/scheduler.py`)
- `GET /api/scheduler/status`: Operational state, interval timings, uptime, error logs, and last cycle results.
- `POST /api/scheduler/start`: Start the scheduler service.
- `POST /api/scheduler/pause`: Suspend execution cycles.
- `POST /api/scheduler/resume`: Resume scheduled execution.
- `POST /api/scheduler/stop`: Stop the scheduler service.
- `POST /api/scheduler/run-now`: Trigger an immediate on-demand harvest cycle.
- `POST /api/scheduler/digest`: Dispatch an immediate daily summary digest.

### 2.4 Command-Line Interface (`src/cli.py`)
Executable via `python -m src.cli <subcommand>`:

| Command | Arguments | Description |
| :--- | :--- | :--- |
| `harvest` | `--limit 10 --min-score 75 --dry-run` | Run immediate on-demand lead harvesting and scoring |
| `daemon` | `--interval 15 --digest-hours 24 --min-score 75` | Run long-running background scheduler daemon process |
| `score` | *None* | Batch re-score all stored projects against current developer profile |
| `pitch` | `--project-id <ID> --angle <ANGLE> --tone <TONE>` | Generate custom AI proposal in terminal |
| `stats` | *None* | Display real-time lead count, quality distributions, and KPIs |
| `digest` | `--lookback 24` | Broadcast summary digest of top recent opportunities |

---

## 3. CLI Usage Examples

### Immediate Lead Discovery & Alert Dispatch:
```bash
python -m src.cli harvest --limit 5 --min-score 80
```

### Run Continuous Daemon Service:
```bash
python -m src.cli daemon --interval 10 --digest-hours 24
```

### Generate Proposal from Terminal:
```bash
python -m src.cli pitch --project-id 1 --angle TECHNICAL_EXPERT --tone CONFIDENT
```

### Inspect Database Statistics:
```bash
python -m src.cli stats
```
