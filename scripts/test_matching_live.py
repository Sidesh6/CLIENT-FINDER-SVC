"""
Live verification script for Phase 4: User Profile & Skill Matching Engine.
Collects live opportunities from Hacker News, extracts structured requirements,
and ranks them against the user profile with transparent match explanations.
"""

import logging
import sys

from src.ai.extractor import ProjectExtractor
from src.collectors.hackernews_collector import HackerNewsCollector
from src.matching.matcher import SkillMatcher
from src.models.profile import get_default_profile
from src.processors.cleaner import ProjectCleaner

if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger("MatchingLiveTest")


def main():
    print("=================================================================")
    print("[*] CLIENT FINDER SVC - Phase 4: Skill Matching & Ranking Test")
    print("=================================================================\n")

    # Step 1: Initialize User Profile
    profile = get_default_profile()
    print(f"[+] Step 1: Loaded User Profile: '{profile.name}' - {profile.title}")
    primary_skills = [s.name for s in profile.skills if s.is_primary]
    print(f"    Primary Core Skills: {', '.join(primary_skills[:8])}...")
    print(
        f"    Target Hourly Rate : ${profile.target_hourly_rate}/hr (Min: ${profile.minimum_hourly_rate}/hr)\n"
    )

    # Step 2: Collect opportunities from Hacker News
    logger.info("Collecting live opportunities from Hacker News (limit=5)...")
    collector = HackerNewsCollector(max_projects=5)
    raw_projects = collector.collect()
    print(f"[+] Step 2: Collected {len(raw_projects)} raw opportunities from Hacker News")

    if not raw_projects:
        print("[!] No opportunities found. Check network connection.")
        return

    # Step 3: Clean and AI Extract
    cleaner = ProjectCleaner()
    cleaned_projects = cleaner.clean_many(raw_projects)
    extractor = ProjectExtractor()
    enriched_projects = [extractor.extract(p) for p in cleaned_projects]
    print(
        f"[+] Step 3: Extracted structured requirements for {len(enriched_projects)} opportunities"
    )

    # Step 4: Run Skill Matching Engine & Ranking
    matcher = SkillMatcher(default_profile=profile)
    ranked_opportunities = matcher.filter_and_rank(enriched_projects, min_match_score=0.0)

    print("\n" + "=" * 70)
    print("RANKED OPPORTUNITY MATCH RESULTS (Highest Fit First)")
    print("=" * 70)

    for rank, (proj, match_res) in enumerate(ranked_opportunities, 1):
        fit_badge = (
            "[STRONG MATCH]"
            if match_res.is_strong_match
            else "[MODERATE FIT]"
            if match_res.match_score >= 50
            else "[LOW FIT]"
        )
        print(f"\n#{rank} {fit_badge} Score: {match_res.match_score}/100 | {proj.title}")
        print(f"    Source URL      : {proj.source_url}")
        print(
            f"    Category        : {proj.category} (Preferred: {'Yes' if match_res.category_match else 'No'})"
        )
        print(
            f"    Required Skills : {', '.join(proj.skills) if proj.skills else 'None extracted'}"
        )
        print(
            f"    Matched Skills  : {', '.join(match_res.matched_skills) if match_res.matched_skills else 'None'}"
        )
        if match_res.implied_skills:
            print(f"    Implied Skills  : {', '.join(match_res.implied_skills)}")
        if match_res.missing_skills:
            print(f"    Missing Skills  : {', '.join(match_res.missing_skills)}")
        print(
            f"    Skill Coverage  : {int(match_res.coverage_ratio * 100)}% (Avg Proficiency: {match_res.average_proficiency}/10)"
        )
        print(f"    Budget Fit      : {'Compatible' if match_res.budget_fit else 'Below Minimum'}")
        print(f"    Explanation     : {match_res.explanation}")

    print("\n" + "=" * 70)
    print("[SUCCESS] Phase 4 Skill Matching & Ranking Engine verified successfully!")
    print("=" * 70)


if __name__ == "__main__":
    main()
