"""
End-to-end database persistence verification script.
Tests: Collector -> Cleaner -> Extractor -> DB Persistence & Deduplication -> DB Querying.
"""

import logging
import sys

from src.ai.extractor import ProjectExtractor
from src.collectors.hackernews_collector import HackerNewsCollector
from src.database.repository import ProjectRepository, SourceRepository
from src.database.session import get_db_session, get_engine, init_db
from src.processors.cleaner import ProjectCleaner

if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger("DBPipelineTest")


def main():
    print("=================================================================")
    print("[*] CLIENT FINDER SVC - Database Persistence & Deduplication Test")
    print("=================================================================\n")

    # Use SQLite database in data/ directory
    engine = get_engine()
    init_db(engine=engine)
    logger.info("Database schema initialized successfully.")

    proj_repo = ProjectRepository()
    src_repo = SourceRepository()

    # Step 1: Register or fetch Source
    with get_db_session(engine=engine) as session:
        hn_source = src_repo.get_or_create(
            name="Hacker News",
            source_type="api",
            session=session,
            base_url="https://hn.algolia.com/api/v1/",
        )
        source_id = hn_source.id
        print(f"[+] Step 1: Registered/Retrieved Source '{hn_source.name}' (ID: {source_id})")

    # Step 2: Collect opportunities
    logger.info("Collecting live opportunities from Hacker News (limit=5)...")
    collector = HackerNewsCollector(max_projects=5)
    raw_projects = collector.collect()
    print(f"[+] Step 2: Collected {len(raw_projects)} raw opportunities from Hacker News")

    if not raw_projects:
        print("[!] No projects found. Ensure internet connection is active.")
        return

    # Step 3: Clean & Extract
    cleaner = ProjectCleaner()
    cleaned = cleaner.clean_many(raw_projects)

    extractor = ProjectExtractor()
    validated_projects = [extractor.extract(p) for p in cleaned]
    print(f"[+] Step 3: Cleaned and validated {len(validated_projects)} projects")

    # Step 4: Persist into database with duplicate skipping
    with get_db_session(engine=engine) as session:
        initial_count = proj_repo.count(session=session)
        print(f"\n[*] Projects currently in database: {initial_count}")

        persisted = proj_repo.add_many(
            validated_projects,
            session=session,
            skip_duplicates=True,
            source_id=source_id,
        )
        print(f"[+] Step 4: Persisted {len(persisted)} new opportunities to database")

    # Step 5: Test Deduplication - re-inserting the same list
    with get_db_session(engine=engine) as session:
        duplicate_attempt = proj_repo.add_many(
            validated_projects,
            session=session,
            skip_duplicates=True,
            source_id=source_id,
        )
        print(
            f"[+] Step 5: Deduplication check: re-inserted batch produced {len(duplicate_attempt)} new records (0 expected)"
        )
        assert len(duplicate_attempt) == 0, "Duplicate projects were incorrectly inserted!"

    # Step 6: Query stored projects from DB
    with get_db_session(engine=engine) as session:
        total_projects = proj_repo.count(session=session)
        recent_projects = proj_repo.list_projects(session=session, limit=5)

        print("\n" + "=" * 65)
        print(f"STORED PROJECTS IN DATABASE (Total: {total_projects})")
        print("=" * 65)

        for i, p in enumerate(recent_projects, 1):
            print(f"\n[{i}] DB ID: {p.id} | Status: {p.status}")
            print(f"    Title       : {p.title}")
            print(f"    Source      : {p.source_name} (Source ID: {p.source_id})")
            print(f"    Author/User : {p.client_name}")
            print(f"    Source URL  : {p.source_url}")
            print(f"    Content Hash: {p.content_hash[:16]}...")
            summary = (
                p.description.replace("\n", " ")[:120] + "..."
                if len(p.description) > 120
                else p.description
            )
            print(f"    Snippet     : {summary}")

    print("\n" + "=" * 65)
    print("[SUCCESS] Full Database Pipeline verified with zero duplicate insertions!")
    print("=" * 65)


if __name__ == "__main__":
    main()
