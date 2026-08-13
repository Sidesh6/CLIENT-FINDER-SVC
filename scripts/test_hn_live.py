"""
Live verification script for HackerNewsCollector and discovery pipeline.
Fetches real public opportunities from Hacker News without mock data.
"""

import logging
import sys

from src.ai.extractor import ProjectExtractor
from src.collectors.hackernews_collector import HackerNewsCollector
from src.processors.cleaner import ProjectCleaner

# Configure UTF-8 handling for Windows stdout if available
if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger("HNLiveTest")


def main():
    print("=================================================================")
    print("[*] CLIENT FINDER SVC - Hacker News Live Opportunity Discovery")
    print("=================================================================\n")

    # Step 1: Collect from public Hacker News API
    logger.info("Initializing HackerNewsCollector (max_projects=5)...")
    collector = HackerNewsCollector(max_projects=5)
    raw_projects = collector.collect()
    print(f"\n[+] Step 1: Collected {len(raw_projects)} raw opportunities from Hacker News")

    if not raw_projects:
        print("[!] No opportunities found in current run. Check network connection.")
        return

    # Step 2: Clean
    cleaner = ProjectCleaner()
    cleaned_projects = cleaner.clean_many(raw_projects)
    print(f"[+] Step 2: Cleaned {len(cleaned_projects)} opportunities")

    # Step 3: Extract & Validate into Pydantic Project models
    extractor = ProjectExtractor()
    validated_projects = [extractor.extract(p) for p in cleaned_projects]
    print(f"[+] Step 3: Validated {len(validated_projects)} Pydantic Project models\n")

    # Step 4: Display discovered opportunities
    print("=" * 65)
    print("DISCOVERED OPPORTUNITIES")
    print("=" * 65)

    for i, proj in enumerate(validated_projects, 1):
        print(f"\n[{i}] {proj.title}")
        print(f"    Source      : {proj.source}")
        print(f"    Client/User : {proj.client_name}")
        print(f"    Type        : {proj.project_type}")
        print(f"    Source URL  : {proj.source_url}")
        snippet = proj.description.replace("\n", " ")[:160] + "..." if len(proj.description) > 160 else proj.description
        print(f"    Summary     : {snippet}")

    print("\n" + "=" * 65)
    print("[SUCCESS] Pipeline executed successfully!")
    print("=" * 65)


if __name__ == "__main__":
    main()
