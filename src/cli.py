"""
Command-Line Interface (CLI) for CLIENT FINDER SVC.
Provides terminal commands for lead discovery, scoring, proposal generation, application tracking, and analytics.
"""

import argparse
import logging
import sys
import time

from src.analytics.engine import AnalyticsEngine
from src.database.connection import SessionLocal, init_db
from src.database.models import ApplicationStatus, ProjectModel
from src.models.profile import get_default_profile
from src.outreach.experiments import GLOBAL_PROPOSAL_EXPERIMENTER
from src.outreach.inbound import InboundReplyClassifier
from src.outreach.schemas import (
    InboundReplyRequest,
    OutreachSequenceCreate,
    SequenceStatus,
)
from src.outreach.sequences import GLOBAL_OUTREACH_ENGINE
from src.proposal.generator import ProposalGenerator
from src.proposal.schemas import PitchAngle, ProposalTone
from src.scheduler.coordinator import PipelineCoordinator
from src.scheduler.service import PipelineScheduler
from src.scoring.engine import OpportunityScorer
from src.tracking.schemas import ApplicationCreate, ApplicationFilter
from src.tracking.tracker import ApplicationTracker

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


def cmd_apply(args: argparse.Namespace) -> int:
    """Track a new job/project application."""
    print("=" * 70)
    print(f"[*] CLIENT FINDER SVC — Track Application (Project #{args.project_id})")
    print("=" * 70)

    init_db()
    tracker = ApplicationTracker()
    payload = ApplicationCreate(
        project_id=args.project_id,
        status=ApplicationStatus(args.status) if args.status else ApplicationStatus.APPLIED,
        proposed_budget=args.budget,
        currency=args.currency,
        pitch_angle=PitchAngle(args.angle) if args.angle else None,
        notes=args.notes,
    )
    app = tracker.track_application(payload)
    print(
        f"[SUCCESS] Tracked Application #{app.id} for Project #{app.project_id} (Status: {app.status})"
    )
    return 0


def cmd_apps(args: argparse.Namespace) -> int:
    """List tracked applications."""
    print("=" * 70)
    print("[*] CLIENT FINDER SVC — Tracked Applications Pipeline")
    print("=" * 70)

    init_db()
    tracker = ApplicationTracker()
    filters = ApplicationFilter(
        status=ApplicationStatus(args.status) if args.status else None,
        limit=args.limit,
    )
    apps = tracker.list_applications(filters)
    print(f"[+] Found {len(apps)} application(s):\n")
    for a in apps:
        print(f"  - App #{a.id} | Project #{a.project_id}: '{a.project_title or 'N/A'}'")
        print(
            f"    Status: {a.status.value} | Budget: {a.currency} {a.proposed_budget or 0:.2f} | Applied: {a.applied_at.strftime('%Y-%m-%d %H:%M')}"
        )
        if a.final_revenue:
            print(f"    Realized Revenue: {a.currency} {a.final_revenue:.2f}")
    return 0


def cmd_funnel(args: argparse.Namespace) -> int:
    """Display application conversion funnel and ROI analytics in terminal."""
    print("=" * 70)
    print("[*] CLIENT FINDER SVC — Conversion Funnel & ROI Intelligence")
    print("=" * 70)

    init_db()
    engine = AnalyticsEngine()
    funnel = engine.compute_funnel_metrics()
    rev = engine.compute_revenue_metrics()
    insights = engine.generate_insights()

    print("\n--- CONVERSION FUNNEL ---")
    print(f"  [1] Applied      : {funnel.total_applications}")
    print(f"  [2] Replied      : {funnel.replied_count} (Response Rate: {funnel.response_rate}%)")
    print(
        f"  [3] Interviewed  : {funnel.interview_count} (Interview Rate: {funnel.interview_rate}%)"
    )
    print(f"  [4] Negotiation  : {funnel.negotiation_count}")
    print(f"  [5] Contracts Won: {funnel.won_count} (Win Rate: {funnel.win_rate}%)")
    print(f"  [6] Proposals Lost: {funnel.lost_count}")

    print("\n--- REVENUE & VELOCITY ---")
    print(f"  Active Pipeline Value : {rev.currency} {rev.total_pipeline_value:,.2f}")
    print(f"  Realized Revenue      : {rev.currency} {rev.realized_revenue:,.2f}")
    print(f"  Average Deal Size     : {rev.currency} {rev.average_deal_size:,.2f}")
    print(f"  Avg Time to Reply     : {funnel.avg_time_to_reply_hours:.1f} hour(s)")
    print(f"  Avg Time to Close     : {funnel.avg_time_to_close_days:.1f} day(s)")

    if insights.recommendations:
        print("\n--- STRATEGIC RECOMMENDATIONS ---")
        for rec in insights.recommendations:
            print(f"  💡 {rec}")
    print("-" * 70)
    return 0


def cmd_outreach_create(args: argparse.Namespace) -> int:
    """Create an automated 5-step outreach cadence for an application."""
    print("=" * 70)
    print("[*] CLIENT FINDER SVC — Create Outreach Cadence")
    print("=" * 70)

    angle = PitchAngle(args.angle) if args.angle else PitchAngle.TECHNICAL_EXPERT
    skills = [s.strip() for s in args.skills.split(",")] if args.skills else ["Python", "FastAPI"]

    req = OutreachSequenceCreate(
        application_id=args.app_id,
        project_title=args.title,
        client_name=args.client or "Client",
        pitch_angle=angle,
        target_skills=skills,
        proposed_budget=args.budget,
        auto_start=not args.no_auto_start,
    )

    seq = GLOBAL_OUTREACH_ENGINE.create_sequence(req)
    print(f"\n[+] Created Sequence ID: {seq.sequence_id}")
    print(f"    Application ID     : {seq.application_id}")
    print(f"    Project Title      : {seq.project_title}")
    print(f"    Client             : {seq.client_name}")
    print(f"    Pitch Angle        : {seq.pitch_angle.value}")
    print(f"    Status             : {seq.status.value}")
    print(f"    Next Step          : Step {seq.current_step_index} / {seq.total_steps}")
    print("\n--- CADENCE TIMELINE ---")
    for step in seq.steps:
        status_icon = "✅" if step.status.value == "EXECUTED" else "⏳"
        print(f"  [{status_icon}] Step {step.step_index}: {step.step_type.value} (+{step.delay_days}d)")
        print(f"      Subject: {step.subject}")
    print("-" * 70)
    return 0


def cmd_outreach_list(args: argparse.Namespace) -> int:
    """List tracked outreach cadences."""
    print("=" * 70)
    print("[*] CLIENT FINDER SVC — Active Outreach Sequences")
    print("=" * 70)

    status_filter = SequenceStatus(args.status) if args.status else None
    seqs = GLOBAL_OUTREACH_ENGINE.list_sequences(status=status_filter)

    if not seqs:
        print("No outreach sequences found matching criteria.")
        return 0

    for s in seqs:
        print(f"Sequence ID: {s.sequence_id} | Status: {s.status.value} | Step: {s.current_step_index}/{s.total_steps}")
        print(f"  App ID: {s.application_id} | Project: {s.project_title} | Client: {s.client_name}")
        print(f"  Pitch: {s.pitch_angle.value} | Updated: {s.updated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print("-" * 70)
    return 0


def cmd_outreach_advance(args: argparse.Namespace) -> int:
    """Advance an outreach sequence to its next step."""
    try:
        seq = GLOBAL_OUTREACH_ENGINE.advance_step(args.seq_id)
        print(f"[+] Advanced sequence {seq.sequence_id} to Step {seq.current_step_index}/{seq.total_steps} (Status: {seq.status.value})")
        return 0
    except KeyError:
        print(f"[!] Sequence with ID '{args.seq_id}' not found.")
        return 1


def cmd_reply_analyze(args: argparse.Namespace) -> int:
    """Analyze incoming client response, classify intent, and synthesize counter-script."""
    print("=" * 70)
    print("[*] CLIENT FINDER SVC — Inbound Reply Intent Classifier")
    print("=" * 70)

    classifier = InboundReplyClassifier()
    req = InboundReplyRequest(
        message_text=args.text,
        application_id=args.app_id,
        project_title=args.title or "Target Project",
        client_name=args.client or "Client",
    )
    result = classifier.analyze_reply(req=req, update_db=not args.dry_run)

    print(f"\n[+] Classified Intent    : {result.classified_intent.value} (Confidence: {result.confidence:.2f})")
    print(f"    Sentiment Score      : {result.sentiment_score:+.2f}")
    print(f"    Recommended Status   : {result.recommended_funnel_status}")
    print(f"    Database Updated     : {result.application_status_updated}")
    print(f"    Recommended Action   : {result.recommended_next_action}")

    if result.detected_objections:
        print(f"    Detected Objections  : {', '.join(result.detected_objections)}")

    print("\n--- SUGGESTED RESPONSE DRAFT ---")
    print(result.suggested_response_draft)
    print("-" * 70)
    return 0


def cmd_ab_stats(args: argparse.Namespace) -> int:
    """Display statistical A/B pitch testing performance metrics and category recommendations."""
    print("=" * 70)
    print("[*] CLIENT FINDER SVC — Dynamic A/B Pitch Angle Experimenter")
    print("=" * 70)

    summary = GLOBAL_PROPOSAL_EXPERIMENTER.get_summary()
    print(f"\nTotal Outreach Events   : {summary.total_outreach_events}")
    print(f"Total Client Responses  : {summary.total_replies}")
    print(f"Overall Response Rate   : {summary.overall_reply_rate}%")
    print(f"Best Converting Pitch   : {summary.best_performing_pitch.value}")
    print(f"Best Win-Rate Pitch     : {summary.best_performing_win_pitch.value}")

    print("\n--- PITCH ANGLE STATISTICAL CONVERSION MATRIX ---")
    print(f"{'Pitch Angle':<25} | {'Sent':<5} | {'Reply %':<8} | {'Win %':<6} | {'Score':<6} | {'95% CI':<14} | {'Sig?'}")
    print("-" * 80)
    for m in summary.pitch_metrics:
        ci_str = f"[{m.confidence_interval_low:.1f}%, {m.confidence_interval_high:.1f}%]"
        sig_str = "⭐ Yes" if m.is_statistically_significant else "No"
        print(f"{m.pitch_angle.value:<25} | {m.impressions_sent:<5} | {m.reply_rate_percent:<7.1f}% | {m.win_rate_percent:<5.1f}% | {m.conversion_score:<6.1f} | {ci_str:<14} | {sig_str}")

    print("\n--- CATEGORY-SPECIFIC OPTIMAL ROUTING ---")
    for cat, angle in summary.category_recommendations.items():
        print(f"  🎯 {cat:<28} ➔ {angle.value}")
    print("-" * 70)
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build root CLI argument parser and subcommands."""
    parser = argparse.ArgumentParser(
        prog="client-finder",
        description="CLIENT FINDER SVC — Automated Lead Discovery, Scoring, and Application Tracking CLI",
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

    # 7. Apply Command
    p_apply = subparsers.add_parser("apply", help="Track a new project application")
    p_apply.add_argument("--project-id", type=int, required=True, help="Database project ID")
    p_apply.add_argument(
        "--status",
        choices=[s.value for s in ApplicationStatus],
        default=ApplicationStatus.APPLIED.value,
    )
    p_apply.add_argument("--budget", type=float, default=None, help="Proposed budget")
    p_apply.add_argument("--currency", type=str, default="USD", help="Currency")
    p_apply.add_argument(
        "--angle", choices=[a.value for a in PitchAngle], default=None, help="Pitch angle"
    )
    p_apply.add_argument("--notes", type=str, default=None, help="Application notes")
    p_apply.set_defaults(func=cmd_apply)

    # 8. Apps Command
    p_apps = subparsers.add_parser("apps", help="List tracked applications")
    p_apps.add_argument("--status", choices=[s.value for s in ApplicationStatus], default=None)
    p_apps.add_argument("--limit", type=int, default=25)
    p_apps.set_defaults(func=cmd_apps)

    # 9. Funnel Command
    p_funnel = subparsers.add_parser(
        "funnel", help="Display conversion funnel and revenue analytics"
    )
    p_funnel.set_defaults(func=cmd_funnel)

    # 10. Outreach Sequence Subcommands
    p_outreach = subparsers.add_parser("outreach", help="Manage automated lead outreach sequences")
    outreach_subs = p_outreach.add_subparsers(dest="outreach_action", help="Outreach actions")

    p_o_create = outreach_subs.add_parser("create", help="Create new outreach sequence")
    p_o_create.add_argument("--app-id", type=int, required=True, help="Target application ID")
    p_o_create.add_argument("--title", type=str, required=True, help="Project title")
    p_o_create.add_argument("--client", type=str, default="Client", help="Client name")
    p_o_create.add_argument("--angle", choices=[a.value for a in PitchAngle], default=PitchAngle.TECHNICAL_EXPERT.value)
    p_o_create.add_argument("--skills", type=str, default="Python, FastAPI", help="Comma-separated skills")
    p_o_create.add_argument("--budget", type=float, default=None, help="Target budget")
    p_o_create.add_argument("--no-auto-start", action="store_true", help="Do not execute Step 1 immediately")
    p_o_create.set_defaults(func=cmd_outreach_create)

    p_o_list = outreach_subs.add_parser("list", help="List active outreach sequences")
    p_o_list.add_argument("--status", choices=[s.value for s in SequenceStatus], default=None)
    p_o_list.set_defaults(func=cmd_outreach_list)

    p_o_adv = outreach_subs.add_parser("advance", help="Advance sequence step")
    p_o_adv.add_argument("--seq-id", type=str, required=True, help="Sequence ID")
    p_o_adv.set_defaults(func=cmd_outreach_advance)

    # 11. Inbound Reply Classifier Command
    p_reply = subparsers.add_parser("reply", help="Classify incoming client reply intent and draft response")
    p_reply.add_argument("--text", type=str, required=True, help="Raw message received from client")
    p_reply.add_argument("--app-id", type=int, default=None, help="Application ID to update in DB")
    p_reply.add_argument("--title", type=str, default=None, help="Project title")
    p_reply.add_argument("--client", type=str, default=None, help="Client name")
    p_reply.add_argument("--dry-run", action="store_true", help="Do not update database status")
    p_reply.set_defaults(func=cmd_reply_analyze)

    # 12. A/B Stats Command
    p_ab = subparsers.add_parser("ab-stats", help="Display A/B pitch testing metrics and category routing")
    p_ab.set_defaults(func=cmd_ab_stats)

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
