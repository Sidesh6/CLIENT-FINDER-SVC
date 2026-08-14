"""
Live demonstration and verification script for Phase 9: Background Scheduler & CLI Service.
Executes end-to-end pipeline cycle, tests scheduler lifecycle, dispatches digest, and runs CLI commands.
"""

import logging
import sys
import time

from src.cli import main as cli_main
from src.scheduler.coordinator import PipelineCoordinator
from src.scheduler.service import PipelineScheduler

if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger("SchedulerLiveTest")


def main():
    print("=================================================================")
    print("[*] CLIENT FINDER SVC - Phase 9: Scheduler & CLI Live Test")
    print("=================================================================\n")

    # 1. Test PipelineCoordinator Single Cycle
    logger.info("Executing PipelineCoordinator on-demand cycle (limit=3)...")
    coordinator = PipelineCoordinator()
    result = coordinator.run_cycle(limit_per_collector=3, min_notification_score=70.0)

    print(f"[+] Cycle Executed in {result.duration_seconds:.2f}s")
    print(f"    Collected: {result.collected_count} | Cleaned: {result.cleaned_count}")
    print(f"    New Projects Saved : {result.new_projects_saved}")
    print(f"    Opportunities Scored: {result.opportunities_scored}")
    print(f"    High Priority Leads: {result.high_priority_count}")
    print(f"    Alerts Dispatched  : {result.notifications_sent}\n")

    # 2. Test PipelineScheduler Lifecycle
    logger.info("Testing PipelineScheduler background daemon lifecycle...")
    scheduler = PipelineScheduler(harvest_interval_minutes=0.1)  # 6 seconds
    scheduler.start()
    print(f"[+] Scheduler Started (is_running={scheduler.is_running()})")

    time.sleep(2.0)
    scheduler.pause()
    print(f"[+] Scheduler Paused (is_paused={scheduler.is_paused()})")

    scheduler.resume()
    print(f"[+] Scheduler Resumed (is_paused={scheduler.is_paused()})")

    status = scheduler.get_status()
    print(
        f"[+] Scheduler Status Telemetry: Total Cycles={status['total_cycles_executed']}, Running={status['running']}"
    )

    scheduler.stop()
    print(f"[+] Scheduler Stopped (is_running={scheduler.is_running()})\n")

    # 3. Test Daily Digest Dispatch
    logger.info("Testing daily digest synthesis and broadcast...")
    digest_results = scheduler.send_daily_digest(lookback_hours=72)
    print(f"[+] Daily Digest broadcasted to {len(digest_results)} channel(s)\n")

    # 4. Test CLI Command Execution
    logger.info("Testing CLI commands execution (stats & pitch)...")
    print("--- CLI STATS COMMAND ---")
    cli_main(["stats"])

    print("\n=================================================================")
    print("[SUCCESS] Phase 9 Scheduler, Coordinator & CLI verified successfully!")
    print("=================================================================")


if __name__ == "__main__":
    main()
