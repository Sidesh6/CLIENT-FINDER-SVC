# Feature Documentation: User Profile & Skill Matching Engine

**Project:** CLIENT FINDER SVC  
**Milestone:** Phase 4 — User Profile & Skill Matching Engine  
**Status:** Complete & Verified (87/87 Tests Passing)  
**Date:** August 2026  

---

## 1. Executive Summary

Once project requirements and technical stacks are extracted from unstructured job postings (via **Phase 3: AI Requirement Extraction**), the system needs to determine **which opportunities are truly worth pursuing** based on the developer's exact skillset, proficiency levels, and business preferences.

The **Skill Matching Engine (Phase 4)** solves this by:
1. **User Profile Modeling (`UserProfile` & `SkillProficiency`):** Encapsulates the developer's technical capabilities, proficiency ratings (1–10), hourly rate minimums, and preferred domains.
2. **Multi-Tier Skill Matching Algorithm:**
   - **Tier 1 (Exact & Synonym Normalization):** Identifies identical skills and synonym aliases (e.g. `Postgres` $\rightarrow$ `PostgreSQL`, `ReactJS` $\rightarrow$ `React`, `k8s` $\rightarrow$ `Kubernetes`).
   - **Tier 2 (Ontological Implication):** Recognizes skill relationships (e.g., having `FastAPI` implies `Python`; `Next.js` implies `React` and `TypeScript`).
   - **Tier 3 (Coverage & Proficiency Weighting):** Calculates coverage ratio, average proficiency, primary skill bonuses, and preferred category alignments.
3. **Transparent Explainability:** Produces human-readable explanations breaking down why an opportunity fits or what critical skills are missing.
4. **Automated Batch Ranking:** Filters and ranks project batches descending by match quality ($0–100\%$).

---

## 2. Architecture & Matching Flow

```text
  ┌────────────────────────────────────────┐       ┌────────────────────────────────────────┐
  │         Extracted Project Model        │       │              User Profile              │
  │  - Required Skills: [FastAPI, Postgres]│       │  - Skills: Python (10/10), SQL (9/10)  │
  │  - Category: Web Development           │       │  - Preferred Categories: [Web, AI]     │
  │  - Budget: $80/hr                      │       │  - Min Rate: $50/hr                    │
  └───────────────────┬────────────────────┘       └───────────────────┬────────────────────┘
                      │                                                │
                      └───────────────────────┬────────────────────────┘
                                              ▼
                      ┌────────────────────────────────────────────────┐
                      │              SkillMatcher Engine               │
                      │                                                │
                      │  1. Normalize via Taxonomy (SYNONYM_MAP)       │
                      │  2. Direct & Synonym Skill Lookup              │
                      │  3. Implied Graph Traversal (RELATED_SKILLS)   │
                      │  4. Weighted Coverage & Proficiency Scoring    │
                      │  5. Category Alignment & Rate Verification     │
                      │  6. Natural Language Explanation Generation    │
                      └───────────────────────┬────────────────────────┘
                                              │
                                              ▼
                      ┌────────────────────────────────────────────────┐
                      │               SkillMatchResult                 │
                      │  - match_score: 92.5 / 100                     │
                      │  - matched_skills: ["PostgreSQL"]              │
                      │  - implied_skills: ["Python" via FastAPI]      │
                      │  - missing_skills: []                          │
                      │  - coverage_ratio: 1.0 (100%)                  │
                      │  - average_proficiency: 9.5 / 10               │
                      │  - category_match: True | budget_fit: True     │
                      │  - explanation: "Outstanding 92.5% match..."   │
                      └────────────────────────────────────────────────┘
```

---

## 3. Subsystem Components

### 3.1. User Profile Data Models (`src/models/profile.py`)

#### `SkillProficiency`
Represents an individual skill with granular proficiency ratings:
- `name: str`: Canonical skill name (e.g. `Python`, `FastAPI`, `LangChain`).
- `proficiency: int`: 1 to 10 scale (1 = Novice, 10 = Expert/Master).
- `years_of_experience: Optional[float]`: Years of professional usage.
- `is_primary: bool`: Core primary competency vs. secondary capability.

#### `UserProfile`
- `name: str`, `title: str`, `bio: Optional[str]`.
- `skills: list[SkillProficiency]`: Full list of proficiencies.
- `preferred_categories: list[ProjectCategory]`: Target domains (`AI Development`, `Web Development`, `Automation & Scraping`, `Systems & Backend`).
- `minimum_hourly_rate`, `target_hourly_rate`, `minimum_fixed_budget`.
- `preferred_payment_types`: `Hourly`, `Fixed Price`, `Contract`.
- `get_default_profile()`: Out-of-the-box profile preconfigured for a Senior AI & Python Full-Stack Engineer.

---

### 3.2. Taxonomy & Ontology Graph (`src/matching/taxonomy.py`)

#### Synonym Normalizer (`SYNONYM_MAP`)
Normalizes over 100+ aliases and case variations to canonical names:
- `postgres`, `postgresql`, `psql` $\rightarrow$ `PostgreSQL`
- `fastapi`, `fast-api` $\rightarrow$ `FastAPI`
- `reactjs`, `react.js` $\rightarrow$ `React`
- `nextjs`, `next.js` $\rightarrow$ `Next.js`
- `k8s`, `kubernetes` $\rightarrow$ `Kubernetes`
- `py`, `python3` $\rightarrow$ `Python`
- `chatgpt`, `gpt-4`, `gpt-4o` $\rightarrow$ `OpenAI`

#### Related Skills Graph (`RELATED_SKILLS_GRAPH`)
Maps specialized frameworks to foundational languages and domains:
- `FastAPI` $\rightarrow$ `["Python", "SQL"]`
- `LangChain` $\rightarrow$ `["Python", "LLM", "RAG", "OpenAI"]`
- `LlamaIndex` $\rightarrow$ `["Python", "LLM", "RAG", "Vector Database"]`
- `Next.js` $\rightarrow$ `["React", "TypeScript", "JavaScript", "HTML/CSS"]`
- `Playwright` $\rightarrow$ `["Web Scraping", "Python", "TypeScript", "JavaScript"]`
- `PyTorch` $\rightarrow$ `["Python", "Machine Learning"]`

---

### 3.3. Skill Matching Engine (`src/matching/matcher.py`)

#### Scoring Algorithm Formulation:
1. **Effective Match Count:**
   $$\text{Effective Matches} = \text{len}(\text{Matched}) + 0.80 \times \text{len}(\text{Implied})$$
2. **Coverage Ratio:**
   $$\text{Coverage} = \min\left(1.0, \frac{\text{Effective Matches}}{\text{Total Required Skills}}\right)$$
3. **Proficiency Factor:**
   $$\text{Prof Factor} = \frac{\text{Average Proficiency on Matched Skills}}{10.0}$$
4. **Base Score Calculation:**
   $$\text{Base Score} = (\text{Coverage} \times 70.0) + (\text{Prof Factor} \times 30.0)$$
5. **Multipliers & Adjustments:**
   - **Primary Skill Bonus:** $+5\%$ if all matched skills are primary core competencies.
   - **Category Preference:** $+5\%$ if project category is in `preferred_categories`, $-8\%$ if outside.
   - **Budget Threshold:** $-5\%$ if specified budget is below user minimum hourly/fixed rate.
   - Score bounded strictly between $0.0$ and $100.0$.

---

## 4. Verification & Testing

### 4.1. Automated Test Suite (`pytest`)
All **87 tests** pass with 100% success:

| Test File | Tests | Scope |
|---|---|---|
| [`tests/unit/test_profile.py`](file:///c:/PRIVATE%20PROJECTS/CLIENT-FINDER-SVC/tests/unit/test_profile.py) | 4 tests | Skill proficiency boundaries (1-10), profile lookups, default profile instantiation. |
| [`tests/unit/test_taxonomy.py`](file:///c:/PRIVATE%20PROJECTS/CLIENT-FINDER-SVC/tests/unit/test_taxonomy.py) | 4 tests | Synonym normalization, unmapped skill handling, ontology graph traversal. |
| [`tests/unit/test_matcher.py`](file:///c:/PRIVATE%20PROJECTS/CLIENT-FINDER-SVC/tests/unit/test_matcher.py) | 6 tests | Perfect match, implied skill matching, missing skill penalties, category preferences, budget thresholds, batch ranking. |
| Other Subsystem Tests | 73 tests | Phase 1 collectors, Phase 2 database, Phase 3 AI extraction. |

### 4.2. Live Hacker News Matching Demonstration (`scripts/test_matching_live.py`)
Tested live against real Hacker News opportunity posts:
- Ranked top opportunities by overall developer alignment.
- Clearly identified matched vs. missing skills and generated transparent natural language explanations.

---

## 5. How to Run

```powershell
# 1. Execute full unit test suite
pytest -v

# 2. Run static typing & formatting validation
mypy src/
ruff check src/ tests/ scripts/
ruff format --check src/ tests/ scripts/

# 3. Run live matching demonstration
python scripts/test_matching_live.py
```
