# Feature Documentation: Multi-Factor Opportunity Scoring Engine

**Project:** CLIENT FINDER SVC  
**Milestone:** Phase 5 — Multi-Factor Opportunity Scoring Engine  
**Status:** Complete & Verified (96/96 Tests Passing)  
**Date:** August 2026  

---

## 1. Executive Summary

In a competitive freelancing market, evaluating opportunities solely by keywords or skill matching leads to sub-optimal decisions (e.g. applying to high-friction clients, low-budget gigs, or stale job posts).

The **Multi-Factor Opportunity Scoring Engine (Phase 5)** evaluates discovered projects across **7 weighted criteria** to produce a holistic composite score ($0–100$), actionable recommendation tier (`APPLY_IMMEDIATELY`, `STRONG_PROSPECT`, `CONSIDER`, `SKIP`), and risk flag analysis.

Scores and factor breakdowns are persisted directly into the relational database (`OpportunityModel` and `ProjectModel.score`).

---

## 2. Multi-Criteria Scoring Architecture

### 2.1 Criteria Weighting Distribution

| Criteria Factor | Weight | Evaluation Method |
|---|---|---|
| **1. Skill Match Fit** | **$30\%$** | Multi-tier coverage, proficiency depth, and taxonomy ontology traversal ([`src/matching/matcher.py`](file:///c:/PRIVATE%20PROJECTS/CLIENT-FINDER-SVC/src/matching/matcher.py)). |
| **2. Budget Attractiveness** | **$20\%$** | Rate alignment vs. developer target rate ($95/hr) and minimum threshold ($50/hr). |
| **3. Client Quality & Spec Detail** | **$15\%$** | Credibility signals (company identity, detailed deliverables, application CTA) vs. negative risk flags (equity-only, vague scope, aggressive urgency). |
| **4. Competition Friction** | **$10\%$** | Barrier-to-entry index (niche technologies like LangChain, RAG, PyTorch have lower competition; saturated stacks like WordPress have higher competition). |
| **5. Complexity Fit** | **$10\%$** | Alignment between project difficulty (High/Medium/Low) and developer seniority level (Senior/Lead). |
| **6. Freshness & Urgency** | **$10\%$** | Non-linear time-decay curve based on posting timestamp ($<6\text{h} = 100$, $<24\text{h} = 90$, $<3\text{d} = 75$, $<7\text{d} = 55$, $>14\text{d} = 20$). |
| **7. Win Probability** | **$5\%$** | Composite estimator combining skill coverage ($50\%$), low competition ($30\%$), and complexity fit ($20\%$). |

$$\text{Overall Score} = 0.30 S_{\text{skill}} + 0.20 S_{\text{budget}} + 0.15 S_{\text{client}} + 0.10 S_{\text{competition}} + 0.10 S_{\text{complexity}} + 0.10 S_{\text{freshness}} + 0.05 S_{\text{win\_prob}}$$

---

### 2.2 Decision Recommendation Tiers

| Composite Score | Recommendation Tier | Action Required |
|---|---|---|
| **$80.0 - 100.0$** | **`APPLY_IMMEDIATELY`** | Highest fit, top-tier budget, strong client signals. Prioritize instant proposal submission. |
| **$68.0 - 79.9$** | **`STRONG_PROSPECT`** | Solid skill match and viable commercial terms. Submit standard proposal. |
| **$50.0 - 67.9$** | **`CONSIDER`** | Viable backup opportunity. Proceed if capacity allows. |
| **$< 50.0$** | **`SKIP`** | Low alignment, missing critical skills, or high risk signals. Ignore. |

---

## 3. Subsystem Implementation

📁 **Directory:** [`src/scoring/`](file:///c:/PRIVATE%20PROJECTS/CLIENT-FINDER-SVC/src/scoring/)

### 3.1. Schemas & Enums ([`src/scoring/schemas.py`](file:///c:/PRIVATE%20PROJECTS/CLIENT-FINDER-SVC/src/scoring/schemas.py))
- `OpportunityScoreBreakdown`: Pydantic model returning `overall_score`, `skill_match_score`, `budget_score`, `client_score`, `competition_score`, `complexity_score`, `freshness_score`, `win_probability`, `recommendation`, `risk_flags`, and `explanation`.
- `ScoringRecommendation`: `StrEnum` covering `APPLY_IMMEDIATELY`, `STRONG_PROSPECT`, `CONSIDER`, `SKIP`.

### 3.2. Factor Calculators ([`src/scoring/calculators.py`](file:///c:/PRIVATE%20PROJECTS/CLIENT-FINDER-SVC/src/scoring/calculators.py))
- `calculate_budget_score(budget, currency, payment_type, profile)`: Proportional scaling against profile hourly and fixed minimums.
- `calculate_client_score(title, description, client_name, source)`: Pattern analyzer detecting company names, structured bullets, application contact methods, and tagging risks (equity-only, overly brief specs, scope creep triggers).
- `calculate_competition_score(skills, complexity, category)`: Niche skill detection vs. low-barrier saturation penalties.
- `calculate_complexity_score(complexity, profile)`: Seniority fit rating.
- `calculate_freshness_score(posted_at)`: Time-decay curve calculating elapsed hours from UTC timestamp.
- `calculate_win_probability(skill_score, competition_score, complexity_score)`: Win probability percentage.

### 3.3. Scoring Engine ([`src/scoring/engine.py`](file:///c:/PRIVATE%20PROJECTS/CLIENT-FINDER-SVC/src/scoring/engine.py))
- `OpportunityScorer`:
  - `score(project, profile)`: Runs 7 criteria evaluations and generates narrative audit explanation.
  - `score_and_persist(project_id, project, session, profile)`: Persists multi-criteria scores to `OpportunityModel` and updates `ProjectModel.score`.
  - `rank_opportunities(projects, profile, min_score)`: Batch sorting descending by overall score.

---

## 4. Verification & Testing

### 4.1. Automated Test Suite (`pytest`)
All **96 tests** pass with 100% success rate:

| Test File | Tests | Scope |
|---|---|---|
| [`tests/unit/test_scoring.py`](file:///c:/PRIVATE%20PROJECTS/CLIENT-FINDER-SVC/tests/unit/test_scoring.py) | 9 tests | Individual factor calculators (budget, client, competition, complexity, freshness, win prob), composite weighting, recommendation tiers, database persistence sync. |
| [`tests/unit/test_profile.py`](file:///c:/PRIVATE%20PROJECTS/CLIENT-FINDER-SVC/tests/unit/test_profile.py) | 4 tests | Profile schemas & proficiency boundaries. |
| [`tests/unit/test_taxonomy.py`](file:///c:/PRIVATE%20PROJECTS/CLIENT-FINDER-SVC/tests/unit/test_taxonomy.py) | 4 tests | Skill taxonomy & graph traversal. |
| [`tests/unit/test_matcher.py`](file:///c:/PRIVATE%20PROJECTS/CLIENT-FINDER-SVC/tests/unit/test_matcher.py) | 6 tests | Skill matching & ranking. |
| Other Subsystem Tests | 73 tests | Collectors, cleaner, deduplication, database repositories, AI extractor. |

```text
============================= 96 passed in 4.74s ==============================
```

### 4.2. Live Hacker News Demonstration ([`scripts/test_scoring_live.py`](file:///c:/PRIVATE%20PROJECTS/CLIENT-FINDER-SVC/scripts/test_scoring_live.py))
Scored and ranked live Hacker News project posts with full 7-factor breakdown:

```text
#1 DB ID: 5 [STRONG PROSPECT] Overall Score: 75.8/100
    Title           : SEEKING FREELANCER - Tootter - Full Stack Web - NYC (Remote)...
    ├─ Skill Fit (30%)    : 81.5/100
    ├─ Budget Fit (20%)   : 55.0/100
    ├─ Client Quality (15%): 100.0/100
    ├─ Competition (10%)  : 65.0/100
    ├─ Complexity (10%)   : 85.0/100
    ├─ Freshness (10%)    : 65.0/100
    └─ Win Probability (5%): 77.2%
    Explanation     : Overall rating: 75.8/100 [Strong Opportunity Prospect]. Skill Fit: 81.5/100 (Strong opportunity match (81.5%). Satisfies core skills: JavaScript (8/10), Next.js (8/10), AWS (8/10). Missing required skills: Ruby. Category 'Web Development' matches your preferred focus.). Budget: 55.0/100 (Unstated). Client Quality: 100.0/100. Competition Friction: 65.0/100 (Est. Win Probability: 77.2%).

#5 DB ID: 2 [SKIP] Overall Score: 48.6/100
    Title           : SEEKING FREELANCER | PHP developer (WordPress) | REMOTE | EU or East Asian timezone
    ├─ Skill Fit (30%)    : 5.0/100
    ├─ Budget Fit (20%)   : 55.0/100
    ├─ Client Quality (15%): 100.0/100
    ├─ Competition (10%)  : 45.0/100
    ├─ Complexity (10%)   : 85.0/100
    ├─ Freshness (10%)    : 65.0/100
    └─ Win Probability (5%): 33.0%
    Explanation     : Overall rating: 48.6/100 [Low Priority (Skip)]. Skill Fit: 5.0/100 (Low match (5.0%). Missing required skills: PHP. Category 'Web Development' matches your preferred focus.). Budget: 55.0/100 (Unstated). Client Quality: 100.0/100. Competition Friction: 45.0/100 (Est. Win Probability: 33.0%).
```

---

## 5. How to Run

```powershell
# 1. Run full unit test suite
pytest -v

# 2. Run static typing & linting
mypy src/
ruff check src/ tests/ scripts/
ruff format --check src/ tests/ scripts/

# 3. Run live opportunity scoring script
python scripts/test_scoring_live.py
```
