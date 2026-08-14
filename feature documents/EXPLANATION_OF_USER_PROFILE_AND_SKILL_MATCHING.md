# Feature Documentation: User Profile & Skill Matching Engine

**Project:** CLIENT FINDER SVC  
**Milestone:** Phase 4 — User Profile & Skill Matching Engine  
**Status:** Complete & Verified (87/87 Tests Passing)  
**Date:** August 2026  

---

## 1. Executive Summary

In automated project discovery, simply extracting technical requirements (via **Phase 3: AI Requirement Extraction**) is not enough. An engineer or agency needs to identify **which opportunities have the highest win probability and provide the greatest return on effort**.

The **User Profile & Skill Matching Engine (Phase 4)** solves this by evaluating discovered project requirements against a personalized developer profile.

### Core Objectives:
1. **Model Developer Capabilities:** Encapsulates technical skills with granular proficiency ratings (1–10 scale), experience years, primary/secondary competency flags, target rates, and preferred project categories.
2. **Multi-Tier Matching Algorithm:**
   - **Tier 1 (Exact & Synonym Normalization):** Normalizes case variations and aliases (`Postgres` $\rightarrow$ `PostgreSQL`, `ReactJS` $\rightarrow$ `React`, `k8s` $\rightarrow$ `Kubernetes`, `py` $\rightarrow$ `Python`).
   - **Tier 2 (Ontological Implication):** Evaluates parent-child relationships in technology stacks (e.g. having `FastAPI` implies `Python`; `Next.js` implies `React` and `TypeScript`; `LangChain` implies `LLM/RAG/Python`).
   - **Tier 3 (Weighted Coverage & Proficiency):** Weighs requirements coverage against proficiency depth:
     $$\text{Base Score} = (\text{Coverage} \times 70\%) + (\text{Proficiency} \times 30\%)$$
3. **Transparent Explainability:** Produces human-readable explanations breaking down which skills matched, which were satisfied via related experience, and what skills are missing.
4. **Automated Batch Ranking:** Filters and sorts opportunities descending by overall match quality ($0–100\%$).

---

## 2. System Architecture & Matching Workflow

```text
  ┌─────────────────────────────────────────┐       ┌─────────────────────────────────────────┐
  │        Extracted Project Model          │       │              User Profile               │
  │  - Required Skills: [FastAPI, Postgres] │       │  - Skills: Python (10/10), SQL (9/10)   │
  │  - Category: Web Development            │       │  - Preferred Categories: [Web, AI]      │
  │  - Budget: $80/hr                       │       │  - Min Rate: $50/hr                     │
  └────────────────────┬────────────────────┘       └────────────────────┬────────────────────┘
                       │                                                 │
                       └────────────────────────┬────────────────────────┘
                                                ▼
                       ┌─────────────────────────────────────────────────┐
                       │              SkillMatcher Engine                │
                       │                                                 │
                       │  1. Normalize via Taxonomy (SYNONYM_MAP)        │
                       │  2. Direct & Synonym Skill Lookup               │
                       │  3. Implied Graph Traversal (RELATED_SKILLS)    │
                       │  4. Weighted Coverage & Proficiency Scoring     │
                       │  5. Category Alignment & Rate Verification      │
                       │  6. Natural Language Explanation Generation     │
                       └────────────────────────┬────────────────────────┘
                                                │
                                                ▼
                       ┌─────────────────────────────────────────────────┐
                       │                SkillMatchResult                 │
                       │  - match_score: 92.5 / 100                      │
                       │  - matched_skills: ["PostgreSQL"]               │
                       │  - implied_skills: ["Python" via FastAPI]       │
                       │  - missing_skills: []                           │
                       │  - coverage_ratio: 1.0 (100%)                   │
                       │  - average_proficiency: 9.5 / 10                │
                       │  - category_match: True | budget_fit: True      │
                       │  - explanation: "Outstanding 92.5% match..."    │
                       └─────────────────────────────────────────────────┘
```

---

## 3. Subsystem Components

📁 **Directories:** [`src/models/`](file:///c:/PRIVATE%20PROJECTS/CLIENT-FINDER-SVC/src/models/) & [`src/matching/`](file:///c:/PRIVATE%20PROJECTS/CLIENT-FINDER-SVC/src/matching/)

### 3.1. User Profile Data Models (`src/models/profile.py`)

#### `SkillProficiency`
Represents an individual technical competency:
- `name: str`: Canonical technology name (e.g. `Python`, `FastAPI`, `LangChain`).
- `proficiency: int`: 1 to 10 scale (1 = Novice, 10 = Master).
- `years_of_experience: Optional[float]`: Years of professional experience.
- `is_primary: bool`: Designates core primary focus vs. secondary capability.

#### `UserProfile`
Encapsulates developer business rules and preferences:
- `name: str`, `title: str`, `bio: Optional[str]`.
- `skills: list[SkillProficiency]`: List of proficiencies.
- `preferred_categories: list[ProjectCategory]`: Preferred domains (`AI Development`, `Web Development`, `Automation & Scraping`, `Systems & Backend`).
- `minimum_hourly_rate: float`: Minimum acceptable rate in USD (default: `$50.0/hr`).
- `target_hourly_rate: float`: Target rate in USD (default: `$90.0/hr`).
- `minimum_fixed_budget: float`: Minimum acceptable fixed project budget (default: `$1,000.0`).
- `preferred_payment_types`: `Hourly`, `Fixed Price`, `Contract`.
- `get_default_profile() -> UserProfile`: Preconfigured profile for a Senior AI & Python Full-Stack Engineer.

---

### 3.2. Taxonomy & Ontology Graph (`src/matching/taxonomy.py`)

#### 1. Synonym & Alias Normalizer (`SYNONYM_MAP`)
Normalizes over 100+ case variations and industry aliases to canonical names:

| Raw Input / Alias | Canonical Name |
|---|---|
| `postgres`, `postgresql`, `psql` | **`PostgreSQL`** |
| `fast-api`, `fastapi` | **`FastAPI`** |
| `reactjs`, `react.js` | **`React`** |
| `nextjs`, `next.js` | **`Next.js`** |
| `k8s`, `kubernetes` | **`Kubernetes`** |
| `py`, `python3` | **`Python`** |
| `chatgpt`, `gpt-4`, `gpt-4o` | **`OpenAI`** |
| `vectordb`, `pinecone`, `chromadb`, `weaviate` | **`Vector Database`** |
| `drf`, `django rest framework` | **`Django`** |
| `nodejs`, `node.js`, `express`, `expressjs` | **`Node.js`** |

#### 2. Related Skills Graph (`RELATED_SKILLS_GRAPH`)
Captures structural relationships where specialized frameworks imply foundational languages:
- **`FastAPI`** $\rightarrow$ `["Python", "SQL"]`
- **`LangChain`** $\rightarrow$ `["Python", "LLM", "RAG", "OpenAI"]`
- **`LlamaIndex`** $\rightarrow$ `["Python", "LLM", "RAG", "Vector Database"]`
- **`RAG`** $\rightarrow$ `["LLM", "Vector Database", "Python"]`
- **`Next.js`** $\rightarrow$ `["React", "TypeScript", "JavaScript", "HTML/CSS"]`
- **`React Native`** $\rightarrow$ `["React", "JavaScript", "TypeScript"]`
- **`Playwright`** $\rightarrow$ `["Web Scraping", "Python", "TypeScript", "JavaScript"]`
- **`PyTorch`** $\rightarrow$ `["Python", "Machine Learning"]`

---

### 3.3. Multi-Tier Matching Engine (`src/matching/matcher.py`)

#### Mathematical Scoring Model:

1. **Effective Match Count:**
   $$\text{Effective Matches} = \text{len}(\text{Matched Skills}) + 0.80 \times \text{len}(\text{Implied Skills})$$

2. **Skill Coverage Ratio ($0.0 - 1.0$):**
   $$\text{Coverage} = \min\left(1.0, \frac{\text{Effective Matches}}{\text{Total Required Skills}}\right)$$

3. **Proficiency Factor ($0.1 - 1.0$):**
   $$\text{Prof Factor} = \frac{\text{Average Proficiency of Matched Skills}}{10.0}$$

4. **Base Score Calculation:**
   $$\text{Base Score} = (\text{Coverage} \times 70.0) + (\text{Prof Factor} \times 30.0)$$

5. **Multipliers & Adjustments:**
   - **Primary Skill Bonus:** $+5\%$ if all matched skills are flagged as primary core skills.
   - **Category Preference:** $+5\%$ if project category aligns with `preferred_categories`, $-8\%$ if outside preferred domains.
   - **Budget Threshold:** $-5\%$ penalty if specified compensation is below minimum hourly/fixed rate thresholds.
   - **Final Bound:** Clipped to $[0.0, 100.0]$.

---

### 3.4. Match Result Schema (`src/matching/schemas.py`)

```python
class SkillMatchResult(BaseModel):
    match_score: float = Field(ge=0.0, le=100.0)
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    implied_skills: list[str] = Field(default_factory=list)
    coverage_ratio: float = Field(default=0.0, ge=0.0, le=1.0)
    average_proficiency: float = Field(default=0.0, ge=0.0, le=10.0)
    category_match: bool = Field(default=True)
    budget_fit: bool = Field(default=True)
    is_strong_match: bool = Field(default=False)
    explanation: str = Field(description="Natural language summary")
```

---

## 4. Verification & Testing

### 4.1. Automated Test Suite (`pytest`)
All **87 tests** pass with 100% success rate:

| Test File | Tests | Scope |
|---|---|---|
| [`tests/unit/test_profile.py`](file:///c:/PRIVATE%20PROJECTS/CLIENT-FINDER-SVC/tests/unit/test_profile.py) | 4 tests | Proficiency boundaries (1-10), profile lookups, default profile instantiation. |
| [`tests/unit/test_taxonomy.py`](file:///c:/PRIVATE%20PROJECTS/CLIENT-FINDER-SVC/tests/unit/test_taxonomy.py) | 4 tests | Synonym normalization, unmapped handling, ontology graph traversal. |
| [`tests/unit/test_matcher.py`](file:///c:/PRIVATE%20PROJECTS/CLIENT-FINDER-SVC/tests/unit/test_matcher.py) | 6 tests | Perfect match, implied skill matching, missing skill penalties, category preferences, budget thresholds, batch ranking. |
| Other Subsystem Tests | 73 tests | Phase 1 collectors, Phase 2 database, Phase 3 AI extraction. |

### 4.2. Live Hacker News Matching Demonstration (`scripts/test_matching_live.py`)
Tested live against real Hacker News opportunity posts:
```text
#1 [MODERATE FIT] Score: 81.5/100 | SEEKING FREELANCER - Tootter - Full Stack Web (Remote)
    Category        : Web Development (Preferred: Yes)
    Required Skills : Ruby, JavaScript, Next.js, AWS
    Matched Skills  : JavaScript, Next.js, AWS
    Missing Skills  : Ruby
    Skill Coverage  : 75% (Avg Proficiency: 8.0/10)
    Explanation     : Strong opportunity match (81.5%). Satisfies core skills: JavaScript (8/10), Next.js (8/10), AWS (8/10). Missing required skills: Ruby. Category 'Web Development' matches your preferred focus.

#2 [STRONG MATCH] Score: 77.2/100 | SEEKING FREELANCER | Shyp | San Francisco (Remote OK)
    Category        : Other
    Required Skills : JavaScript, HTML/CSS
    Matched Skills  : JavaScript
    Implied Skills  : HTML/CSS
    Skill Coverage  : 90% (Avg Proficiency: 7.4/10)
    Explanation     : Strong opportunity match (77.2%). Satisfies core skills: JavaScript (8/10). Covered via related experience: HTML/CSS.

#5 [LOW FIT] Score: 5.0/100 | SEEKING FREELANCER | PHP developer (WordPress) | REMOTE
    Required Skills : PHP
    Matched Skills  : None
    Missing Skills  : PHP
    Skill Coverage  : 0%
    Explanation     : Low match (5.0%). Missing required skills: PHP.
```

---

## 5. How to Run

```powershell
# 1. Run complete unit test suite
pytest -v

# 2. Run static analysis & type checking
mypy src/
ruff check src/ tests/ scripts/
ruff format --check src/ tests/ scripts/

# 3. Execute live matching & ranking test
python scripts/test_matching_live.py
```
