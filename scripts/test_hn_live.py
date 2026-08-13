"""
Live verification script for HackerNewsCollector, Deduplicator, and Database persistence.
Fetches real public opportunities from Hacker News and stores them in SQLite.
"""

import logging
import sys

from src.ai.extractor import ProjectExtractor
from src.collectors.hackernews_collector import HackerNewsCollector
from src.database.database import get_db_session, get_engine, get_session_factory, init_db
from src.database.repository import CollectionRunRepository, ProjectRepository
from src.processors.cleaner import ProjectCleaner
from src.processors.deduplicator import ProjectDeduplicator

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
    print("[*] CLIENT FINDER SVC - Live Discovery & Persistence Pipeline")
    print("=================================================================\n")

    # Step 0: Initialize Database
    engine = get_engine()
    init_db(engine)
    session_factory = get_session_factory(engine)

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

    # Step 3: Deduplicate against existing Database hashes
    with get_db_session(session_factory) as session:
        proj_repo = ProjectRepository(session)
        existing_url_hashes = proj_repo.get_all_url_hashes()
        existing_content_hashes = proj_repo.get_all_content_hashes()

    deduplicator = ProjectDeduplicator()
    unique_projects, dup_count = deduplicator.deduplicate_batch(
        cleaned_projects,
        existing_url_hashes=existing_url_hashes,
        existing_content_hashes=existing_content_hashes,
    )
    print(
        f"[+] Step 3: Deduplication complete: {len(unique_projects)} new unique, {dup_count} duplicates skipped"
    )

    # Step 4: Extract & Validate into Pydantic Project models
    extractor = ProjectExtractor()
    validated_projects = [extractor.extract(p) for p in unique_projects]
    print(f"[+] Step 4: Validated {len(validated_projects)} Pydantic Project models\n")

    # Step 5: Persist to Database & Log Collection Run
    with get_db_session(session_factory) as session:
        proj_repo = ProjectRepository(session)
        run_repo = CollectionRunRepository(session)

        run = run_repo.start_run(collector.get_source_name())
        saved_records, skipped_in_db = proj_repo.save_many(validated_projects)
        total_skipped = dup_count + skipped_in_db

        run_repo.complete_run(
            run_id=run.id,
            items_collected=len(raw_projects),
            items_saved=len(saved_records),
            duplicates_skipped=total_skipped,
            status="SUCCESS",
        )

        total_db_count = proj_repo.count()
        recent_records = proj_repo.list_projects(limit=5)

    print(
        f"[+] Step 5: Database updated: {len(saved_records)} newly saved, Total in DB: {total_db_count}"
    )

    # Display summary of stored opportunities
    print("\n" + "=" * 65)
    print("📋 LATEST STORED OPPORTUNITIES IN DATABASE")
    print("=" * 65)

    for i, rec in enumerate(recent_records, 1):
        print(f"\n[{i}] {rec.title}")
        print(f"    DB ID       : {rec.id}")
        print(f"    Source      : {rec.source}")
        print(f"    Client/User : {rec.client_name}")
        print(f"    URL Hash    : {rec.url_hash[:12]}...")
        print(f"    Source URL  : {rec.source_url}")
        snippet = (
            rec.description.replace("\n", " ")[:140] + "..."
            if len(rec.description) > 140
            else rec.description
        )
        print(f"    Summary     : {snippet}")

    print("\n" + "=" * 65)
    print("[SUCCESS] Pipeline executed and stored successfully!")
    print("=" * 65)


if __name__ == "__main__":
    main()
