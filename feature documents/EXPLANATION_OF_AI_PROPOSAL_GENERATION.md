# Feature Documentation: AI Proposal & Cover Letter Generator

**Project:** CLIENT FINDER SVC  
**Milestone:** Phase 7 — AI Proposal & Cover Letter Generator  
**Status:** Complete & Verified (118/118 Tests Passing)  
**Date:** August 2026  

---

## 1. Executive Summary

Once high-scoring project opportunities are discovered and scored (via **Phase 5: Opportunity Scoring** and **Phase 6: Multi-Channel Alerts**), developers need to submit **compelling, personalized proposals** that win client trust and maximize conversion rates.

The **AI Proposal & Cover Letter Generator (Phase 7)** produces bespoke, context-aware proposals tailored to the client's exact requirements, technical stack, budget, and project urgency.

### Core Highlights:
1. **Strategic Pitch Angles:** Supports 5 distinct positioning frameworks (`TECHNICAL_EXPERT`, `FAST_DELIVERY`, `VALUE_ROI`, `PORTFOLIO_PROOF`, `CONSULTATIVE_ADVISOR`).
2. **Dynamic Context Injection:** Fuses extracted project requirements, client goals, and developer skills/rates into a cohesive pitch.
3. **Dual Engine Architecture (AI + Offline Fallback):** Integrates LLM generation with a deterministic rule-based heuristic synthesizer that guarantees high-quality proposals even without active API credentials.
4. **Built-in Quality Scoring:** Evaluates proposal completeness, hook punchiness, case study relevance, and clear calls-to-action on a 0–100 quality scale.

---

## 2. Proposal Architecture & Generation Flow

```text
  ┌─────────────────────────────────────────┐       ┌─────────────────────────────────────────┐
  │        Extracted Project Model          │       │              User Profile               │
  │  - Title: "FastAPI & RAG Microservice"  │       │  - Name: "Alex Mercer"                  │
  │  - Required Tech: [Python, FastAPI, RAG]│       │  - Core Skills: Python (10/10), SQL     │
  │  - Budget: $5,000 (Fixed Price)         │       │  - Target Rate: $95/hr                  │
  └────────────────────┬────────────────────┘       └────────────────────┬────────────────────┘
                       │                                                 │
                       └────────────────────────┬────────────────────────┘
                                                │
                                                ▼
                       ┌─────────────────────────────────────────────────┐
                       │          ProposalGenerator Coordinator          │
                       │                                                 │
                       │  1. Auto-select or apply requested Pitch Angle  │
                       │  2. Build Context-Aware Dynamic Prompt          │
                       │  3. Execute LLM Call (Gemini / OpenAI API)      │
                       │  4. Graceful Failover to Heuristic Synthesizer  │
                       │  5. Validate Sections & Evaluate Quality Score  │
                       └────────────────────────┬────────────────────────┘
                                                │
                                                ▼
                       ┌─────────────────────────────────────────────────┐
                       │                 ProposalResult                  │
                       │  - subject_line: "Senior FastAPI Specialist..." │
                       │  - hook: "I reviewed your requirements..."      │
                       │  - body: "As a Senior AI Engineer..."           │
                       │  - relevant_projects: ["Built enterprise RAG..."]│
                       │  - pricing_quote: "USD 5,000 (Fixed Price)"     │
                       │  - call_to_action: "Let's connect for 15-min..."│
                       │  - full_proposal_text: Complete Markdown Letter │
                       │  - quality_score: 90.0 / 100                    │
                       └─────────────────────────────────────────────────┘
```

---

## 3. Subsystem Implementation

📁 **Directory:** [`src/proposal/`](file:///c:/PRIVATE%20PROJECTS/CLIENT-FINDER-SVC/src/proposal/)

### 3.1. Strategic Pitch Angles ([`src/proposal/schemas.py`](file:///c:/PRIVATE%20PROJECTS/CLIENT-FINDER-SVC/src/proposal/schemas.py))

| Pitch Angle | Target Client Scenario | Positioning Focus |
|---|---|---|
| **`TECHNICAL_EXPERT`** | Complex backends, AI pipelines, system architectures. | Production resilience, type safety, sub-second latency, clean code standards. |
| **`FAST_DELIVERY`** | Urgent deadlines, rapid prototypes, fast MVPs. | Immediate start, sprint schedules (Day 1-2 / 3-5 / 6-7), rapid feedback loops. |
| **`VALUE_ROI`** | Enterprise automation, commercial products, high budgets. | Reducing operational cloud costs, eliminating tech debt, maximizing business impact. |
| **`PORTFOLIO_PROOF`** | Clients requesting verifiable past track records. | Measurable past metrics (e.g. 50k daily transactions), live demo references. |
| **`CONSULTATIVE_ADVISOR`** | Open-ended scopes, advisory engagements, strategy. | Posing architectural discovery questions, outlining tradeoffs and roadmaps. |

---

### 3.2. Heuristic & Rule-Based Proposal Synthesizer ([`src/proposal/heuristic.py`](file:///c:/PRIVATE%20PROJECTS/CLIENT-FINDER-SVC/src/proposal/heuristic.py))
- Provides high-converting proposal generation without external API dependencies.
- Synthesizes personalized opening hooks matching the project's primary technologies.
- Pulls matched case studies from developer competencies.
- Generates transparent commercial investment estimates.
- Formats closing calls-to-action.

---

### 3.3. Proposal Generator Coordinator ([`src/proposal/generator.py`](file:///c:/PRIVATE%20PROJECTS/CLIENT-FINDER-SVC/src/proposal/generator.py))
- `auto_select_pitch_angle(project, score_breakdown)`: Automatically selects the most persuasive pitch angle based on keywords, category, budget, and urgency signals.
- `generate(request)`: Executes prompt against LLM provider with fallback to heuristic generator.
- `evaluate_quality(proposal, project)`: Assesses proposal length, tech stack relevance, and actionability on a 0–100 scale.

---

## 4. Verification & Testing

### 4.1. Automated Test Suite (`pytest`)
All **118 tests** pass with 100% success rate:

| Test File | Tests | Scope |
|---|---|---|
| [`tests/unit/test_proposal.py`](file:///c:/PRIVATE%20PROJECTS/CLIENT-FINDER-SVC/tests/unit/test_proposal.py) | 9 tests | Proposal schemas, 5 pitch angles (Technical, Fast, ROI, Portfolio, Consultative), prompt builder, pitch angle auto-selection, LLM mock handling, fallback resilience, quality scoring. |
| Other Subsystem Tests | 109 tests | Multi-channel notifications, opportunity scoring, skill matching, AI extractor, database repositories, collectors. |

```text
============================= 118 passed in 5.30s =============================
```

### 4.2. Live Demonstration ([`scripts/test_proposal_live.py`](file:///c:/PRIVATE%20PROJECTS/CLIENT-FINDER-SVC/scripts/test_proposal_live.py))
Demonstrated against real Hacker News project opportunities across multiple pitch angle variants:
- **Technical Expert Variant:** Structured around clean architecture, latency optimization, and automated test coverage.
- **Fast Delivery Variant:** Structured around immediate start and milestone delivery roadmap.
- **Value ROI Variant:** Structured around operational efficiency, cost reduction, and engineering velocity.

---

## 5. How to Run

```powershell
# 1. Run full unit test suite
pytest -v

# 2. Run static analysis & type checking
mypy src/
ruff check src/ tests/ scripts/
ruff format --check src/ tests/ scripts/

# 3. Execute live proposal generation demonstration
python scripts/test_proposal_live.py
```
