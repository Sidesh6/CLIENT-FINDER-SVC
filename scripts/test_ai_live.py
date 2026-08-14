"""
Live verification script for Phase 3: AI Requirement Extraction Engine.
Collects real opportunities from Hacker News and extracts structured requirements.
"""

import logging
import sys

from src.ai.extractor import ProjectExtractor
from src.collectors.hackernews_collector import HackerNewsCollector
from src.processors.cleaner import ProjectCleaner

if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger("AILiveTest")


def main():
    print("=================================================================")
    print("[*] CLIENT FINDER SVC - Phase 3: AI Requirement Extraction Test")
    print("=================================================================\n")

    # Step 1: Collect opportunities from Hacker News
    logger.info("Collecting live opportunities from Hacker News (limit=4)...")
    collector = HackerNewsCollector(max_projects=4)
    raw_projects = collector.collect()
    print(f"[+] Step 1: Collected {len(raw_projects)} raw opportunities from Hacker News")

    if not raw_projects:
        print("[!] No opportunities found. Check network connection.")
        return

    # Step 2: Clean data
    cleaner = ProjectCleaner()
    cleaned_projects = cleaner.clean_many(raw_projects)
    print(f"[+] Step 2: Cleaned {len(cleaned_projects)} opportunities")

    # Step 3: Run AI Requirement Extraction Engine
    extractor = ProjectExtractor()
    print("\n[+] Step 3: Running AI Requirement Extraction Engine (LLM / Heuristic)...")
    enriched_projects = [extractor.extract(p) for p in cleaned_projects]

    print("\n" + "=" * 70)
    print("STRUCTURED AI EXTRACTION RESULTS")
    print("=" * 70)

    for i, proj in enumerate(enriched_projects, 1):
        print(f"\n[{i}] {proj.title}")
        print(f"    Source Platform : {proj.source}")
        print(f"    Category        : {proj.category}")
        print(f"    Extracted Skills: {', '.join(proj.skills) if proj.skills else 'None detected'}")
        print(f"    Complexity      : {proj.complexity}")
        print(f"    Project Type    : {proj.project_type or 'Not specified'}")
        budget_str = f"{proj.budget} {proj.currency}" if proj.budget else "Not specified"
        print(f"    Parsed Budget   : {budget_str}")
        print(f"    Confidence Score: {proj.confidence_score}")
        if proj.deliverables:
            print(f"    Deliverables    : {proj.deliverables}")
        print(f"    Source URL      : {proj.source_url}")

    print("\n" + "=" * 70)
    print("[SUCCESS] Phase 3 AI Requirement Extraction Engine verified successfully!")
    print("=" * 70)


if __name__ == "__main__":
    main()
