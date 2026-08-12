# CLIENT-FINDER-SVC
AI-powered system for discovering, analyzing, scoring, and organizing public project opportunities from online sources.

## Objective

The system will automatically:

1. Discover public project opportunities.
2. Extract useful project information.
3. Clean and normalize the collected data.
4. Use AI to understand project requirements.
5. Score projects based on relevance and potential.
6. Store structured project information.
7. Provide the highest-value opportunities to the user.

## Current Development Phase

Phase 1 - Project Discovery Pipeline

Current components:

- Project collectors
- Data cleaning
- AI extraction
- Database model
- Testing

## Technology Stack

- Python
- FastAPI
- PostgreSQL
- SQLAlchemy
- Pydantic
- BeautifulSoup
- HTTPX
- LLM API
- Docker
- Pytest

## Project Pipeline

Internet
    ↓
Collectors
    ↓
Raw Project Data
    ↓
Cleaner
    ↓
AI Extractor
    ↓
Structured Project
    ↓
Database
    ↓
Scoring
    ↓
Project Opportunities

## Development Principle

Build each component independently, understand how it works, test it, and then integrate it into the pipeline.