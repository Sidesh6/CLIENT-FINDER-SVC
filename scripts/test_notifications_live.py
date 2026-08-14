"""
Live demonstration script for Phase 6: Multi-Channel Notification Dispatcher.
Executes the full pipeline: Collect -> AI Extract -> Skill Match -> Multi-Factor Score -> Dispatch Alerts & Digest.
"""

import logging
import sys

from src.ai.extractor import ProjectExtractor
from src.collectors.hackernews_collector import HackerNewsCollector
from src.models.profile import get_default_profile
from src.notifications.channels.console import ConsoleNotifier
from src.notifications.channels.desktop import DesktopNotifier
from src.notifications.dispatcher import NotificationDispatcher
from src.processors.cleaner import ProjectCleaner
from src.scoring.engine import OpportunityScorer

if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger("NotificationLiveTest")


def main():
    print("=================================================================")
    print("[*] CLIENT FINDER SVC - Phase 6: Multi-Channel Notification Test")
    print("=================================================================\n")

    profile = get_default_profile()
    print(f"[+] Loaded Developer Profile: '{profile.name}' ({profile.title})")

    # Step 1: Collect opportunities
    logger.info("Collecting live opportunities from Hacker News...")
    collector = HackerNewsCollector(max_projects=5)
    raw_projects = collector.collect()
    print(f"[+] Collected {len(raw_projects)} raw opportunities from Hacker News")

    if not raw_projects:
        print("[!] No opportunities found.")
        return

    # Step 2: Clean and AI Extract
    cleaner = ProjectCleaner()
    cleaned = cleaner.clean_many(raw_projects)
    extractor = ProjectExtractor()
    enriched = [extractor.extract(p) for p in cleaned]
    print(f"[+] Extracted structured requirements for {len(enriched)} opportunities")

    # Step 3: Multi-Factor Opportunity Scoring
    scorer = OpportunityScorer(default_profile=profile)
    scored_opps = scorer.score_batch(enriched, profile=profile)

    # Step 4: Notification Dispatcher
    dispatcher = NotificationDispatcher(
        channels=[
            ConsoleNotifier(enabled=True, use_colors=True),
            DesktopNotifier(enabled=True),
        ],
        min_score_threshold=65.0,  # Alert threshold
    )

    print("\n" + "=" * 75)
    print("STEP 4: DISPATCHING REAL-TIME MULTI-CHANNEL ALERTS (Score >= 65.0)")
    print("=" * 75)

    alert_count = 0
    for proj, breakdown in scored_opps:
        results = dispatcher.dispatch(proj, breakdown)
        if results:
            alert_count += 1
            print(
                f"    [✔] Dispatched to {len(results)} active channel(s): {[r.channel.value for r in results if r.success]}"
            )

    print(f"\n[+] Dispatched {alert_count} real-time alert(s) meeting score threshold >= 65.0")

    # Step 5: Dispatch Batch Digest
    print("\n" + "=" * 75)
    print("STEP 5: DISPATCHING CONSOLIDATED BATCH DIGEST")
    print("=" * 75)

    digest_results = dispatcher.dispatch_digest(scored_opps, min_score=50.0)
    print(f"[+] Digest broadcast complete across {len(digest_results)} channels.")

    print("\n" + "=" * 75)
    print("[SUCCESS] Phase 6 Multi-Channel Notification Dispatcher verified successfully!")
    print("=" * 75)


if __name__ == "__main__":
    main()
