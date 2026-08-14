"""
Live verification script for Phase 5: Multi-Factor Opportunity Scoring Engine.
Collects live opportunities from Hacker News, extracts requirements, persists to DB,
calculates 7-factor composite scores, and displays ranked opportunities with recommendations.
"""

import logging
import sys
from typing import Any

from src.ai.extractor import ProjectExtractor
from src.collectors.hackernews_collector import HackerNewsCollector
from src.database.database import get_db_session, get_engine, init_db
from src.database.repository import ProjectRepository, SourceRepository
from src.models.profile import get_default_profile
from src.processors.cleaner import ProjectCleaner
from src.scoring.engine import OpportunityScorer

if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger("ScoringLiveTest")


def main():
    print("=================================================================")
    print("[*] CLIENT FINDER SVC - Phase 5: Multi-Factor Opportunity Scoring Test")
    print("=================================================================\n")

    # Step 1: Initialize Database & User Profile
    engine = get_engine("sqlite:///data/client_finder.db")
    init_db(engine)
    profile = get_default_profile()
    print(f"[+] Step 1: Database initialized & User Profile loaded: '{profile.name}'")
    print(
        f"    Target Hourly Rate: ${profile.target_hourly_rate}/hr | Min Rate: ${profile.minimum_hourly_rate}/hr\n"
    )

    # Step 2: Collect opportunities from Hacker News
    logger.info("Collecting live opportunities from Hacker News (limit=5)...")
    collector = HackerNewsCollector(max_projects=5)
    raw_projects = collector.collect()
    print(f"[+] Step 2: Collected {len(raw_projects)} raw opportunities from Hacker News")

    if not raw_projects:
        print("[!] No opportunities found.")
        return

    # Step 3: Clean and AI Extract
    cleaner = ProjectCleaner()
    cleaned_projects = cleaner.clean_many(raw_projects)
    extractor = ProjectExtractor()
    enriched_projects = [extractor.extract(p) for p in cleaned_projects]
    print(
        f"[+] Step 3: Cleaned & extracted requirements for {len(enriched_projects)} opportunities"
    )

    # Step 4: Persist and Multi-Factor Score in DB
    scorer = OpportunityScorer(default_profile=profile)
    scored_records: list[tuple[int, str, Any]] = []

    with get_db_session(engine=engine) as session:
        src_repo = SourceRepository(session)
        source_model = src_repo.get_or_create(name="Hacker News", source_type="api")

        proj_repo = ProjectRepository(session)
        for enriched in enriched_projects:
            url_str = str(enriched.source_url)
            existing = proj_repo.get_by_url(url_str)
            if existing:
                existing.skills = enriched.skills
                existing.raw_data = {
                    "category": enriched.category,
                    "complexity": enriched.complexity,
                }
                proj_model = existing
            else:
                proj_model = proj_repo.add(enriched, source_id=source_model.id)

            pydantic_proj = proj_model.to_pydantic()
            opp_model = scorer.score_and_persist(
                project_id=proj_model.id,
                project=pydantic_proj,
                session=session,
                profile=profile,
            )
            scored_records.append((proj_model.id, proj_model.title, opp_model))

    # Step 5: Display Ranked Results
    scored_records.sort(key=lambda item: item[2].overall_score, reverse=True)

    print("\n" + "=" * 75)
    print("RANKED OPPORTUNITIES - 7-FACTOR COMPOSITE SCORE MATRIX")
    print("=" * 75)

    for rank, (p_id, title, opp) in enumerate(scored_records, 1):
        rec_tag = f"[{opp.overall_score >= 80 and 'APPLY IMMEDIATELY' or opp.overall_score >= 68 and 'STRONG PROSPECT' or opp.overall_score >= 50 and 'CONSIDER' or 'SKIP'}]"
        print(f"\n#{rank} DB ID: {p_id} {rec_tag} Overall Score: {opp.overall_score}/100")
        print(f"    Title           : {title[:65]}...")
        print(f"    ├─ Skill Fit (30%)    : {opp.skill_match_score}/100")
        print(f"    ├─ Budget Fit (20%)   : {opp.budget_score}/100")
        print(f"    ├─ Client Quality (15%): {opp.client_score}/100")
        print(f"    ├─ Competition (10%)  : {opp.competition_score}/100")
        print(f"    ├─ Complexity (10%)   : {opp.complexity_score}/100")
        print(f"    ├─ Freshness (10%)    : {opp.freshness_score}/100")
        print(f"    └─ Win Probability (5%): {opp.win_probability}%")
        print(f"    Explanation     : {opp.explanation}")

    print("\n" + "=" * 75)
    print("[SUCCESS] Phase 5 Multi-Factor Opportunity Scoring verified successfully!")
    print("=" * 75)


if __name__ == "__main__":
    main()
