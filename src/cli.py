"""
Command-Line Interface (CLI) for CLIENT FINDER SVC.
Provides terminal commands for autonomous lead harvesting, daemon execution, proposal generation, and analytics.
"""

import argparse
import logging
import sys
import time

from src.database.connection import SessionLocal, init_db
from src.database.models import ProjectModel
from src.models.profile import get_default_profile
from src.proposal.generator import ProposalGenerator
from src.proposal.schemas import PitchAngle, ProposalTone
from src.scheduler.coordinator import PipelineCoordinator
from src.scheduler.service import PipelineScheduler
from src.scoring.engine import OpportunityScorer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ClientFinderCLI")


def cmd_harvest(args: argparse.Namespace) -> int:
    """Execute immediate on-demand lead harvesting and scoring cycle."""
    print("=" * 70)
    print("[*] CLIENT FINDER SVC — Lead Harvest Cycle")
    print("=" * 70)

    init_db()
    coordinator = PipelineCoordinator()
    result = coordinator.run_cycle(
        min_notification_score=args.min_score,
        dry_run=args.dry_run,
        limit_per_collector=args.limit,
    )

    print(f"\n[+] Cycle Completed in {result.duration_seconds:.2f}s")
    print(f"    Raw Items Harvested   : {result.collected_count}")
    print(f"    New Projects Persisted: {result.new_projects_saved}")
    print(f"    Duplicates Skipped    : {result.duplicates_skipped}")
    print(f"    Opportunities Scored  : {result.opportunities_scored}")
    print(f"    High Priority Leads   : {result.high_priority_count} (≥{args.min_score})")
    print(f"    Alerts Dispatched     : {result.notifications_sent}")

    if result.errors:
        print("\n[!] Errors encountered during run:")
        for err in result.errors:
            print(f"    - {err}")
        return 1

    return 0


def cmd_daemon(args: argparse.Namespace) -> int:
    """Run autonomous background scheduler daemon until interrupted."""
    print("=" * 70)
    print("[*] CLIENT FINDER SVC — Background Scheduler Daemon")
    print(
        f"[*] Harvest Interval: {args.interval} min(s) | Digest Interval: {args.digest_hours} hr(s)"
    )
    print("=" * 70)
    print("Press Ctrl+C to terminate the daemon service...\n")

    init_db()
    scheduler = PipelineScheduler(
        harvest_interval_minutes=args.interval,
        digest_interval_hours=args.digest_hours,
        min_notification_score=args.min_score,
    )

    scheduler.start()

    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\n[!] Interruption signal received. Stopping scheduler gracefully...")
        scheduler.stop()
        print("[+] Scheduler daemon terminated successfully.")

    return 0


def cmd_score(args: argparse.Namespace) -> int:
    """Re-score all stored projects against current developer profile."""
    print("=" * 70)
    print("[*] CLIENT FINDER SVC — Batch Opportunity Scorer")
    print("=" * 70)

    init_db()
    profile = get_default_profile()
    scorer = OpportunityScorer(default_profile=profile)
    scored_count = 0

    with SessionLocal() as session:
        from sqlalchemy import select

        projects = session.scalars(select(ProjectModel)).all()
        print(f"[+] Re-scoring {len(projects)} projects against profile '{profile.name}'...")

        for pm in projects:
            p_obj = pm.to_pydantic()
            scorer.score_and_persist(
                project_id=pm.id, project=p_obj, session=session, profile=profile
            )
            scored_count += 1

    print(f"[SUCCESS] Successfully re-scored {scored_count} opportunities in the database.")
    return 0


def cmd_pitch(args: argparse.Namespace) -> int:
    """Generate customized AI proposal for a given project ID."""
    print("=" * 70)
    print(f"[*] CLIENT FINDER SVC — Proposal Generator (Project #{args.project_id})")
    print("=" * 70)

    init_db()
    with SessionLocal() as session:
        pm = session.get(ProjectModel, args.project_id)
        if not pm:
            print(f"[!] Error: Project with ID {args.project_id} not found.")
            return 1
        project = pm.to_pydantic()

    profile = get_default_profile()
    generator = ProposalGenerator(default_profile=profile)

    angle = PitchAngle(args.angle) if args.angle else PitchAngle.TECHNICAL_EXPERT
    tone = ProposalTone(args.tone) if args.tone else ProposalTone.CONFIDENT

    proposal = generator.generate_for_project(
        project=project,
        profile=profile,
        pitch_angle=angle,
        tone=tone,
        include_pricing=not args.no_pricing,
    )

    print(f"\nSubject Line : {proposal.subject_line}")
    print(f"Pitch Angle  : {proposal.pitch_angle.value}")
    print(f"Quality Score: {proposal.quality_score}/100\n")
    print("--- PROPOSAL CONTENT ---")
    print(proposal.full_proposal_text)
    print("-" * 70)

    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    """Display opportunity distribution metrics and KPIs."""
    print("=" * 70)
    print("[*] CLIENT FINDER SVC — Opportunity Metrics & Analytics")
    print("=" * 70)

    init_db()
    with SessionLocal() as session:
        from sqlalchemy import func, select

        total = session.scalar(select(func.count(ProjectModel.id))) or 0
        high = (
            session.scalar(select(func.count(ProjectModel.id)).where(ProjectModel.score >= 75.0))
            or 0
        )
        med = (
            session.scalar(
                select(func.count(ProjectModel.id)).where(
                    ProjectModel.score >= 50.0, ProjectModel.score < 75.0
                )
            )
            or 0
        )
        low = (
            session.scalar(select(func.count(ProjectModel.id)).where(ProjectModel.score < 50.0))
            or 0
        )
        avg_score = session.scalar(select(func.avg(ProjectModel.score))) or 0.0

    print(f"[+] Total Opportunities Discovered : {total}")
    print(
        f"    - High Priority Leads (≥75)    : {high} ({high/total*100:.1f}%)"
        if total
        else "    - High Priority Leads: 0"
    )
    print(
        f"    - Medium Priority Leads (50-74): {med} ({med/total*100:.1f}%)"
        if total
        else "    - Medium Priority Leads: 0"
    )
    print(
        f"    - Low Priority Leads (<50)     : {low} ({low/total*100:.1f}%)"
        if total
        else "    - Low Priority Leads: 0"
    )
    print(f"    - Average Match Score          : {float(avg_score):.1f}/100\n")

    return 0


def cmd_digest(args: argparse.Namespace) -> int:
    """Synthesize and send immediate daily digest email/Slack alert."""
    print("=" * 70)
    print("[*] CLIENT FINDER SVC — Dispatching Daily Digest")
    print("=" * 70)

    init_db()
    scheduler = PipelineScheduler()
    results = scheduler.send_daily_digest(lookback_hours=args.lookback)

    print(f"[+] Digest dispatched to {len(results)} notification channel(s):")
    for r in results:
        status_tag = "OK" if r.success else "FAIL"
        print(f"    [{status_tag}] Channel: {r.channel.value} ({r.error_message or 'Delivered'})")

    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build root CLI argument parser and subcommands."""
    parser = argparse.ArgumentParser(
        prog="client-finder",
        description="CLIENT FINDER SVC — Automated Lead Discovery, Scoring, and Proposal Generator CLI",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # 1. Harvest Command
    p_harvest = subparsers.add_parser("harvest", help="Run immediate lead harvesting cycle")
    p_harvest.add_argument(
        "--limit", type=int, default=10, help="Max leads to fetch per collector (default: 10)"
    )
    p_harvest.add_argument(
        "--min-score", type=float, default=75.0, help="Min score for alert dispatch (default: 75.0)"
    )
    p_harvest.add_argument(
        "--dry-run", action="store_true", help="Harvest and extract without saving or notifying"
    )
    p_harvest.set_defaults(func=cmd_harvest)

    # 2. Daemon Command
    p_daemon = subparsers.add_parser("daemon", help="Run continuous background scheduler service")
    p_daemon.add_argument(
        "--interval", type=float, default=15.0, help="Harvest interval in minutes (default: 15.0)"
    )
    p_daemon.add_argument(
        "--digest-hours", type=float, default=24.0, help="Digest interval in hours (default: 24.0)"
    )
    p_daemon.add_argument(
        "--min-score", type=float, default=75.0, help="Min score for alert dispatch (default: 75.0)"
    )
    p_daemon.set_defaults(func=cmd_daemon)

    # 3. Score Command
    p_score = subparsers.add_parser("score", help="Re-score all projects in database")
    p_score.set_defaults(func=cmd_score)

    # 4. Pitch Command
    p_pitch = subparsers.add_parser("pitch", help="Generate AI proposal for a stored project")
    p_pitch.add_argument(
        "--project-id", type=int, required=True, help="Database ID of target project"
    )
    p_pitch.add_argument(
        "--angle",
        choices=[a.value for a in PitchAngle],
        default=PitchAngle.TECHNICAL_EXPERT.value,
        help="Strategic pitch angle",
    )
    p_pitch.add_argument(
        "--tone",
        choices=[t.value for t in ProposalTone],
        default=ProposalTone.CONFIDENT.value,
        help="Proposal tone",
    )
    p_pitch.add_argument(
        "--no-pricing", action="store_true", help="Omit commercial pricing section"
    )
    p_pitch.set_defaults(func=cmd_pitch)

    # 5. Stats Command
    p_stats = subparsers.add_parser("stats", help="Display opportunity analytics and KPIs")
    p_stats.set_defaults(func=cmd_stats)

    # 6. Digest Command
    p_digest = subparsers.add_parser("digest", help="Dispatch daily summary digest")
    p_digest.add_argument(
        "--lookback", type=int, default=24, help="Hours to look back for top leads (default: 24)"
    )
    p_digest.set_defaults(func=cmd_digest)

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not hasattr(args, "func"):
        parser.print_help()
        return 0

    res = args.func(args)
    return int(res) if isinstance(res, int) else 0


if __name__ == "__main__":
    sys.exit(main())
