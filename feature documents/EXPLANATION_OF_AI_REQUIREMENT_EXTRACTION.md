# Feature Documentation: AI Requirement Extraction Engine

**Project:** CLIENT FINDER SVC  
**Milestone:** Phase 3 — AI Requirement Extraction Engine  
**Status:** Complete & Verified (73/73 Tests Passing)  
**Date:** August 2026  

---

## 1. Executive Summary

Public freelance and project listings (from Hacker News, web job boards, and RSS feeds) are inherently unstructured, conversational, and noisy. Descriptions often mix technical stack details, client introductions, compensation structures, timelines, and extraneous formatting in a single text blob.

To enable **Skill Matching (Phase 4)** and **Multi-Factor Opportunity Scoring (Phase 5)**, raw listings must be transformed into strictly typed, validated domain models.

The **AI Requirement Extraction Engine** accomplishes this by:
1. **Structuring Unstructured Data:** Extracts technical skills, project classification, complexity level, payment structure, numerical budgets, and concrete deliverables.
2. **Dual-Engine Architecture:** Combines high-precision LLM extraction (Google Gemini / OpenAI / Ollama) with a high-speed, zero-dependency **Rule-Based Heuristic Engine**.
3. **Resilient Failover:** If an LLM call fails, times out, or has no API key configured, the system automatically falls back to heuristic extraction without throwing exceptions or interrupting the pipeline.
4. **Anti-Hallucination Guardrails:** Enforces strict extraction constraints—only facts explicitly mentioned in the text are extracted.

---

## 2. Extraction Pipeline Architecture

```text
               ┌────────────────────────────────────────────────────────┐
               │         Raw / Cleaned Project Opportunity              │
               │         (Title, Description, Source URL)               │
               └───────────────────────────┬────────────────────────────┘
                                           │
                                           ▼
               ┌────────────────────────────────────────────────────────┐
               │           ProjectExtractor (Coordinator)               │
               └───────────────────────────┬────────────────────────────┘
                                           │
                        Is LLM API Key Configured?
                                ┌──────────┴──────────┐
                            YES │                  NO │
                                ▼                     ▼
        ┌───────────────────────────────┐     ┌───────────────────────────────┐
        │   BaseLLMClient (LLM Mode)    │     │      HeuristicExtractor       │
        │   (Gemini / OpenAI / Custom)  │     │   (Rule-Based Regex Engine)   │
        └───────────────┬───────────────┘     └───────────────┬───────────────┘
                        │                                     │
                 LLM Call Succeeded?                          │
                 ┌──────┴──────┐                              │
             YES │          NO │ (Timeout / Error / Non-JSON) │
                 ▼             └──────────────┐               │
        ┌─────────────────┐                   │               │
        │ JSON Validation │                   ▼               │
        │ (Pydantic Model)│            [ Fallback ]           │
        └────────┬────────┘                   │               │
                 │                            └───────┬───────┘
                 │                                    │
                 ▼                                    ▼
        ┌─────────────────────────────────────────────────────────────┐
        │              ExtractedRequirements (Pydantic)               │
        │  - Category (e.g. AI Development, Web Development)          │
        │  - Required & Optional Skills (e.g. FastAPI, LangChain)     │
        │  - Estimated Complexity (Low, Medium, High, Expert)         │
        │  - Payment Type (Fixed Price, Hourly, Contract)             │
        │  - Normalized Budget (budget_min, budget_max, currency)     │
        │  - Deliverables & Risk Signals                              │
        │  - Extraction Confidence Score (0.0 to 1.0)                 │
        └──────────────────────────────┬──────────────────────────────┘
                                       │
                                       ▼
        ┌─────────────────────────────────────────────────────────────┐
        │             Enriched Domain Model: Project                  │
        └─────────────────────────────────────────────────────────────┘
```

---

## 3. Subsystem Components

### 3.1. Structured Extraction Schemas (`src/ai/schemas.py`)
Defines the target data contracts using Pydantic models and string enums:

#### Enums:
- **`ProjectCategory`**: `AI Development`, `Web Development`, `Mobile Development`, `Data Engineering`, `Automation & Scraping`, `DevOps & Cloud`, `Systems & Backend`, `Other`.
- **`ProjectComplexity`**: `Low`, `Medium`, `High`, `Expert`.
- **`PaymentType`**: `Fixed Price`, `Hourly`, `Contract`, `Full Time`, `Unknown`.
- **`ExperienceLevel`**: `Junior`, `Mid-Level`, `Senior`, `Lead/Architect`, `Not Specified`.

#### Data Model (`ExtractedRequirements`):
```python
class ExtractedRequirements(BaseModel):
    category: ProjectCategory = Field(default=ProjectCategory.OTHER)
    required_skills: list[str] = Field(default_factory=list)
    optional_skills: list[str] = Field(default_factory=list)
    estimated_complexity: ProjectComplexity = Field(default=ProjectComplexity.MEDIUM)
    project_type: PaymentType = Field(default=PaymentType.UNKNOWN)
    experience_level: ExperienceLevel = Field(default=ExperienceLevel.NOT_SPECIFIED)
    budget_min: Optional[float] = Field(default=None, ge=0)
    budget_max: Optional[float] = Field(default=None, ge=0)
    currency: Optional[str] = Field(default=None)
    deliverables: list[str] = Field(default_factory=list)
    technical_requirements: list[str] = Field(default_factory=list)
    risk_signals: list[str] = Field(default_factory=list)
    confidence_score: float = Field(default=0.85, ge=0.0, le=1.0)
    summary: Optional[str] = Field(default=None)
```

---

### 3.2. LLM Provider Subsystem (`src/ai/client.py` & `src/ai/prompts.py`)

#### Provider Implementations:
- **`GeminiLLMClient`**: Connects to the Google Gemini API with `responseMimeType="application/json"` and temperature `0.1` for deterministic structured extraction.
- **`OpenAICompatibleClient`**: Connects to OpenAI, Groq, Ollama, OpenRouter, or custom OpenAI-compatible endpoints with `response_format={"type": "json_object"}`.
- **`get_llm_client()` Factory**: Auto-discovers available environment variables (`GEMINI_API_KEY`, `OPENAI_API_KEY`, `LLM_API_BASE`).

#### Prompt Guardrails (`EXTRACTION_SYSTEM_PROMPT`):
1. **Zero Hallucination:** Strict instruction never to invent non-existent skills, budgets, or deadlines.
2. **Budget Neutrality:** If compensation is not mentioned in the listing, `budget_min`, `budget_max`, and `currency` must remain `null`.
3. **Canonical Normalization:** Normalizes acronyms and aliases (e.g. `fast-api` $\rightarrow$ `FastAPI`, `postgres` $\rightarrow$ `PostgreSQL`).
4. **Risk Signal Flagging:** Identifies red flags such as "unclear scope", "equity-only", or "unusually low budget".

---

### 3.3. Rule-Based Heuristic Subsystem (`src/ai/heuristic.py`)

When no LLM API key is present or when offline, the `HeuristicExtractor` provides instantaneous ($<5\text{ms}$) rule-based extraction:

#### 1. Technology Catalog (`SKILL_PATTERNS`):
Matches 60+ industry technologies using word-boundary regular expressions across categories:
- **AI & ML:** LangChain, LlamaIndex, RAG, OpenAI, Claude, Gemini, PyTorch, TensorFlow, HuggingFace, Vector DBs, Fine-Tuning.
- **Backend:** Python, FastAPI, Django, Flask, Node.js, Go, Rust, Java, C#, C++, PHP.
- **Frontend:** React, Next.js, Vue, Angular, Svelte, TypeScript, JavaScript, TailwindCSS, GraphQL.
- **Databases:** PostgreSQL, MySQL, SQLite, MongoDB, Redis, Snowflake, BigQuery.
- **Cloud & DevOps:** Docker, Kubernetes, AWS, GCP, Azure, Terraform, CI/CD, Linux.
- **Scraping & Automation:** Playwright, Selenium, BeautifulSoup, Web Scraping.
- **Mobile:** React Native, Flutter, iOS, Android.

#### 2. Multi-Currency Budget Parser (`BUDGET_REGEXES`):
- **Ordered Evaluation:** Evaluates range expressions (e.g. `$4,000 - $6,000` or `€1,000 - 2,000`) before single amounts to avoid truncation.
- **Hourly Rate Detection:** Identifies rates like `$80/hr`, `$50 / hour`, `75 USD per hr`.
- **Currency Mapping:** Converts `$`, `€`, `£`, `₹`, `USD`, `EUR`, `INR`, `GBP`, `CAD`, `AUD` to ISO codes.
- **Duration Collision Protection:** Prevents time duration strings (e.g. `2 - 6 month`, `30 hours`) from being falsely extracted as financial budgets.

#### 3. Category & Complexity Evaluator:
- **Category Classification:** Classifies projects based on skill density and domain triggers (`AI Development`, `Web Development`, `Mobile Development`, `Data Engineering`, `Automation & Scraping`).
- **Complexity Estimation:** Computes complexity (`Low`, `Medium`, `High`, `Expert`) based on architectural depth keywords (`distributed`, `microservices`, `high throughput`, `fine-tuning`) and technology counts.

---

### 3.4. Extraction Coordinator (`src/ai/extractor.py`)

The `ProjectExtractor` orchestrates the complete extraction lifecycle:

```python
extractor = ProjectExtractor()

# Single project extraction
enriched_project = extractor.extract(raw_project_dict_or_model)

# Batch project extraction
enriched_batch = extractor.extract_many(list_of_projects)
```

**Key Behaviors:**
- Calls `extract_requirements(title, description, source)` to produce an `ExtractedRequirements` model.
- Merges extracted skills with existing scraped tags without duplicates.
- Backfills missing budget and currency values.
- Enriches domain model fields: `category`, `complexity`, `deliverables`, and `confidence_score`.

---

## 4. Verification & Testing

### 4.1. Automated Test Suite (`pytest`)
All **73 tests** pass with 100% success:

| Test File | Test Cases | Scope |
|---|---|---|
| [`tests/unit/test_schemas.py`](file:///c:/PRIVATE%20PROJECTS/CLIENT-FINDER-SVC/tests/unit/test_schemas.py) | 5 tests | Schema defaults, custom models, negative budget validation, confidence boundaries, JSON serialization. |
| [`tests/unit/test_heuristic.py`](file:///c:/PRIVATE%20PROJECTS/CLIENT-FINDER-SVC/tests/unit/test_heuristic.py) | 8 tests | Skill extraction, fixed budget ranges, hourly rates, EUR/INR currency, category classification, complexity estimation, full pipeline. |
| [`tests/unit/test_ai_extractor.py`](file:///c:/PRIVATE%20PROJECTS/CLIENT-FINDER-SVC/tests/unit/test_ai_extractor.py) | 6 tests | Heuristic default mode, mock LLM client success, timeout exception fallback, malformed JSON fallback, Pydantic model input, batch extraction. |
| [`tests/test_pipeline.py`](file:///c:/PRIVATE%20PROJECTS/CLIENT-FINDER-SVC/tests/test_pipeline.py) | 12 tests | End-to-end collector $\rightarrow$ cleaner $\rightarrow$ deduplicator $\rightarrow$ AI extractor $\rightarrow$ database persistence. |
| `tests/unit/test_database.py` & `test_repository.py` | 21 tests | Database models, session handling, CRUD, repository queries. |
| Other Collectors & Utilities | 21 tests | Hacker News scraper, HTTP client retries, project model validation. |

### 4.2. Live Extraction Verification (`scripts/test_ai_live.py`)
Tested against live Hacker News "Ask HN: Seeking Freelancer" feeds:
- Successfully extracted tech stacks (e.g. `JavaScript, HTML/CSS`, `PHP`, `AWS, iOS, Android`, `C#, Next.js, Linux`).
- Correctly assigned categories (`Mobile Development`, `Web Development`, `Other`).
- Accurately extracted concrete deliverable bullet points.

---

## 5. How to Run & Configure

### 5.1. Run Heuristic Mode (Offline / Default)
Works immediately with zero API keys:
```powershell
# Run unit tests
pytest -v

# Run live Hacker News extraction demo
python scripts/test_ai_live.py
```

### 5.2. Run with Live LLM (Gemini or OpenAI)
To enable live LLM structured extraction, set the environment variable:

**Google Gemini:**
```powershell
$env:GEMINI_API_KEY = "your-gemini-api-key"
python scripts/test_ai_live.py
```

**OpenAI / OpenRouter / Ollama:**
```powershell
$env:OPENAI_API_KEY = "your-openai-api-key"
# Optional custom base URL (e.g. local Ollama or vLLM):
# $env:LLM_API_BASE = "http://localhost:11434/v1"
python scripts/test_ai_live.py
```
