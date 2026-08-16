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
    print(f"    High Priority Leads   : {result.high_priority_count} (>={args.min_score})")

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
        status_icon = "[X]" if step.status.value == "EXECUTED" else "[ ]"
        print(
            f"  {status_icon} Step {step.step_index}: {step.step_type.value} (+{step.delay_days}d)"
        )
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
        print(
            f"Sequence ID: {s.sequence_id} | Status: {s.status.value} | Step: {s.current_step_index}/{s.total_steps}"
        )
        print(
            f"  App ID: {s.application_id} | Project: {s.project_title} | Client: {s.client_name}"
        )
        print(
            f"  Pitch: {s.pitch_angle.value} | Updated: {s.updated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )
        print("-" * 70)
    return 0


def cmd_outreach_advance(args: argparse.Namespace) -> int:
    """Advance an outreach sequence to its next step."""
    try:
        seq = GLOBAL_OUTREACH_ENGINE.advance_step(args.seq_id)
        print(
            f"[+] Advanced sequence {seq.sequence_id} to Step {seq.current_step_index}/{seq.total_steps} (Status: {seq.status.value})"
        )
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

    print(
        f"\n[+] Classified Intent    : {result.classified_intent.value} (Confidence: {result.confidence:.2f})"
    )
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
    print(
        f"{'Pitch Angle':<25} | {'Sent':<5} | {'Reply %':<8} | {'Win %':<6} | {'Score':<6} | {'95% CI':<14} | {'Sig?'}"
    )
    print("-" * 80)
    for m in summary.pitch_metrics:
        ci_str = f"[{m.confidence_interval_low:.1f}%, {m.confidence_interval_high:.1f}%]"
        sig_str = "[YES]" if m.is_statistically_significant else "No"
        print(
            f"{m.pitch_angle.value:<25} | {m.impressions_sent:<5} | {m.reply_rate_percent:<7.1f}% | {m.win_rate_percent:<5.1f}% | {m.conversion_score:<6.1f} | {ci_str:<14} | {sig_str}"
        )

    print("\n--- CATEGORY-SPECIFIC OPTIMAL ROUTING ---")
    for cat, angle in summary.category_recommendations.items():
        print(f"  [>] {cat:<28} -> {angle.value}")
    print("-" * 70)
    return 0


def cmd_dossier(args: argparse.Namespace) -> int:
    """Generate client intelligence dossier and credibility trust score."""
    from src.database.connection import SessionLocal
    from src.database.models import ProjectModel
    from src.intelligence.dossier import ClientDossierEngine
    from src.intelligence.schemas import ClientDossierRequest

    print("=" * 70)
    print("[*] CLIENT FINDER SVC — Deep Client Intelligence Dossier")
    print("=" * 70)

    title = args.title or "Target Project"
    desc = args.desc or ""
    client_name = args.client or "Client"
    budget = args.budget
    source_url = None
    source = "CLI Manual"

    if args.project_id:
        with SessionLocal() as session:
            proj = session.get(ProjectModel, args.project_id)
            if not proj:
                print(f"[!] Project #{args.project_id} not found in database.")
                return 1
            title = proj.title
            desc = proj.description or ""
            client_name = proj.client_name or client_name
            budget = proj.budget if budget is None else budget
            source_url = proj.source_url
            source = proj.source or source

    engine = ClientDossierEngine()
    req = ClientDossierRequest(
        client_name=client_name,
        project_title=title,
        project_description=desc,
        source=source,
        source_url=source_url,
        claimed_budget=budget,
    )
    res = engine.generate_dossier(req)

    print(f"\nClient Name            : {res.client_name}")
    print(f"Inferred Company Domain: {res.inferred_company_domain or 'Unverified Domain'}")
    print(f"Overall Trust Score    : {res.overall_trust_score}/100 ({res.trust_grade})")
    print(f"Detected Tech Stack    : {', '.join(res.detected_tech_stack)}")

    print("\n--- TRUST DIMENSIONS BREAKDOWN ---")
    print(f"  Domain Credibility   : {res.trust_breakdown.domain_credibility:.1f}/100")
    print(f"  Hiring History Scale : {res.trust_breakdown.hiring_history_score:.1f}/100")
    print(f"  Budget Transparency  : {res.trust_breakdown.budget_transparency:.1f}/100")
    print(f"  Requirement Clarity  : {res.trust_breakdown.requirement_clarity:.1f}/100")
    print(f"  Payment Security     : {res.trust_breakdown.payment_security_score:.1f}/100")

    if res.positive_signals:
        print("\n--- POSITIVE CREDIBILITY SIGNALS ---")
        for s in res.positive_signals:
            print(f"  [+] {s}")

    if res.caution_warnings:
        print("\n--- CAUTION & NUANCE WARNINGS ---")
        for c in res.caution_warnings:
            print(f"  [!] {c}")

    print("\n--- RECOMMENDED COMMERCIAL POSTURE ---")
    print(f"  {res.recommended_commercial_posture}")
    print("-" * 70)
    return 0


def cmd_scam_audit(args: argparse.Namespace) -> int:
    """Audit opportunity text for fraud patterns and red flags."""
    from src.intelligence.scam_sentinel import GLOBAL_SCAM_SENTINEL
    from src.intelligence.schemas import ScamAuditRequest

    print("=" * 70)
    print("[*] CLIENT FINDER SVC — Scam & Fraud Risk Sentinel Audit")
    print("=" * 70)

    req = ScamAuditRequest(
        project_title=args.title or "Opportunity Description",
        project_description=args.text,
        claimed_budget=args.budget,
    )
    res = GLOBAL_SCAM_SENTINEL.audit_opportunity(req)

    safety_icon = "[SAFE]" if res.is_safe_to_apply else "[DANGER]"
    print(f"\nScam Risk Score        : {res.scam_risk_score}/100 ({res.risk_tier.value})")
    print(
        f"Application Safety     : {safety_icon} {'Safe to apply' if res.is_safe_to_apply else 'High risk of fraud/exploitation'}"
    )
    print(f"Confidence Level       : {res.legitimacy_confidence * 100:.0f}%")

    if res.detected_red_flags:
        print("\n--- DETECTED RED FLAGS & EVIDENCE ---")
        for flag in res.detected_red_flags:
            print(f"  [{flag.severity}] {flag.pattern_type.value}")
            print(f"      Evidence: {flag.evidence_snippet}")
            print(f"      Risk    : {flag.risk_explanation}")
            print(f"      Defense : {flag.defensive_action}")
    else:
        print("\n[+] No malicious patterns or fraud indicators detected.")

    print("\n--- DEFENSIVE RECOMMENDATIONS ---")
    for r in res.defensive_recommendations:
        print(f"  -> {r}")
    print("-" * 70)
    return 0


def cmd_feasibility(args: argparse.Namespace) -> int:
    """Evaluate scope vs budget feasibility."""
    from src.intelligence.feasibility import GLOBAL_FEASIBILITY_ANALYZER
    from src.intelligence.schemas import BudgetFeasibilityRequest

    print("=" * 70)
    print("[*] CLIENT FINDER SVC — Scope vs. Budget Feasibility Analyzer")
    print("=" * 70)

    skills = [s.strip() for s in args.skills.split(",")] if args.skills else []
    req = BudgetFeasibilityRequest(
        project_title=args.title,
        project_description=args.desc or "",
        proposed_budget=args.budget,
        target_skills=skills,
    )
    res = GLOBAL_FEASIBILITY_ANALYZER.evaluate_feasibility(req)

    print(f"\nProject Title          : {args.title}")
    print(f"Offered Budget         : ${args.budget:,.2f}")
    print(
        f"Feasibility Rating     : {res.feasibility_rating.value} (Score: {res.feasibility_score}/100)"
    )
    print(
        f"Estimated Effort       : {res.estimated_engineering_hours_min} - {res.estimated_engineering_hours_max} hours"
    )
    print(
        f"Fair Market Budget     : ${res.estimated_fair_market_budget:,.2f} (@ ${res.estimated_market_rate_hourly:.0f}/hr)"
    )
    print(f"Budget Variance        : {res.budget_variance_percent:+.1f}%")
    print(f"Scope Creep Risk Level : {res.scope_creep_risk_level}")
    print(f"Recommended Counter    : ${res.recommended_counter_budget:,.2f}")

    print("\n--- SCOPE NEGOTIATION & PHASING ADVICE ---")
    for s in res.scope_reduction_suggestions:
        print(f"  -> {s}")
    print("-" * 70)
    return 0


def cmd_search_semantic(args: argparse.Namespace) -> int:
    """Execute natural language dense semantic vector search."""
    from src.vectors.engine import GLOBAL_VECTOR_STORE

    print("=" * 70)
    print(f"[*] CLIENT FINDER SVC — Semantic Vector Search ('{args.query}')")
    print("=" * 70)

    init_db()
    if GLOBAL_VECTOR_STORE.count() == 0:
        count = GLOBAL_VECTOR_STORE.index_from_database()
        print(f"[+] Populated vector store with {count} database opportunities.")

    results = GLOBAL_VECTOR_STORE.search(
        query=args.query,
        limit=args.limit,
        min_similarity=args.min_sim,
    )

    print(f"\n[+] Found {len(results)} semantically similar opportunity(s):\n")
    for idx, r in enumerate(results, start=1):
        print(f"  [{idx}] {r.title}")
        print(
            f"      Cosine Sim: {r.cosine_similarity * 100:.1f}% | Budget: ${r.budget or 0:,.2f} | Source: {r.source}"
        )
        if r.skills:
            print(f"      Skills    : {', '.join(r.skills[:4])}")
        print(f"      Summary   : {r.description[:120]}...\n")
    print("-" * 70)
    return 0


def cmd_search_hybrid(args: argparse.Namespace) -> int:
    """Execute hybrid dense vector + lexical BM25 search."""
    from src.vectors.hybrid_search import GLOBAL_HYBRID_SEARCH
    from src.vectors.schemas import HybridSearchRequest

    print("=" * 70)
    print(f"[*] CLIENT FINDER SVC — Hybrid Semantic + Lexical Search (alpha={args.alpha})")
    print("=" * 70)

    init_db()
    req = HybridSearchRequest(
        query=args.query,
        alpha=args.alpha,
        limit=args.limit,
        min_score=args.min_score,
    )
    res = GLOBAL_HYBRID_SEARCH.search(req)

    print(f"\n[+] Retrieved {res.total_matches} hybrid matches in {res.duration_ms:.1f}ms:\n")
    for idx, r in enumerate(res.results, start=1):
        print(f"  [{idx}] {r.title}")
        print(
            f"      Hybrid Score: {r.hybrid_score * 100:.1f}% (Dense: {r.semantic_similarity * 100:.0f}%, Lexical: {r.lexical_score * 100:.0f}%)"
        )
        print(f"      Budget      : ${r.budget or 0:,.2f} | Source: {r.source}")
        if r.skills:
            print(f"      Skills      : {', '.join(r.skills[:4])}")
        print(f"      Summary     : {r.description[:120]}...\n")
    print("-" * 70)
    return 0


def cmd_rag_match(args: argparse.Namespace) -> int:
    """Semantically retrieve matching developer case studies for a project."""
    from src.vectors.rag_retriever import GLOBAL_PORTFOLIO_RAG
    from src.vectors.schemas import PortfolioRAGRequest

    print("=" * 70)
    print(f"[*] CLIENT FINDER SVC — Portfolio RAG Matcher ('{args.title}')")
    print("=" * 70)

    skills = [s.strip() for s in args.skills.split(",")] if args.skills else []
    req = PortfolioRAGRequest(
        project_title=args.title,
        project_description=args.desc or "",
        target_skills=skills,
        top_k=args.top_k,
    )
    res = GLOBAL_PORTFOLIO_RAG.retrieve_context(req)

    print(f"\n[+] Semantically Aligned Case Studies ({len(res.matched_case_studies)}):\n")
    for idx, cs in enumerate(res.matched_case_studies, start=1):
        print(
            f"  [{idx}] {cs.title} ({cs.client_industry}) — Similarity: {cs.semantic_similarity * 100:.1f}%"
        )
        print(f"      Tech Stack: {', '.join(cs.technologies[:4])}")
        print(f"      Citation  : {cs.relevant_citation_snippet}\n")

    print("--- SYNTHESIZED PROPOSAL EVIDENCE PARAGRAPH ---")
    print(f"{res.suggested_proof_paragraph}\n")
    print("-" * 70)
    return 0


def cmd_vectors_reindex(args: argparse.Namespace) -> int:
    """Rebuild the in-memory dense vector index from database opportunities."""
    from src.vectors.engine import GLOBAL_VECTOR_STORE

    print("=" * 70)
    print("[*] CLIENT FINDER SVC — Dense Vector Store Reindex")
    print("=" * 70)

    init_db()
    count = GLOBAL_VECTOR_STORE.index_from_database()
    stats = GLOBAL_VECTOR_STORE.get_stats()

    print(f"\n[SUCCESS] Successfully indexed {count} documents into 384-dimensional vector store.")
    print(f"          Total Memory: {stats.index_memory_bytes / 1024:.1f} KB")
    print("-" * 70)
    return 0


def cmd_auth_register(args: argparse.Namespace) -> int:
    """Register a new SaaS user and initialize dedicated workspace."""
    from src.auth.security import create_access_token
    from src.auth.store import GLOBAL_TENANT_STORE

    print("=" * 70)
    print("[*] CLIENT FINDER SVC — SaaS User & Workspace Registration")
    print("=" * 70)

    try:
        user, tenant = GLOBAL_TENANT_STORE.register_user(
            email=args.email,
            password=args.password,
            full_name=args.name,
            workspace_name=args.workspace or "",
        )
        token = create_access_token(user.user_id, tenant.tenant_id, user.role)
        print(f"\n[SUCCESS] Registered User '{user.full_name}' ({user.email})")
        print(f"          Workspace : '{tenant.name}' (ID: {tenant.tenant_id})")
        print(f"          Plan Tier : {tenant.plan_tier.value}")
        print(f"          Role      : {user.role.value}")
        print(f"          JWT Token : {token[:32]}...\n")
        print("-" * 70)
        return 0
    except ValueError as err:
        print(f"\n[!] Registration Error: {err}")
        return 1


def cmd_auth_login(args: argparse.Namespace) -> int:
    """Authenticate with email/password and obtain signed JWT access token."""
    from src.auth.security import create_access_token
    from src.auth.store import GLOBAL_TENANT_STORE

    print("=" * 70)
    print(f"[*] CLIENT FINDER SVC — User Authentication ({args.email})")
    print("=" * 70)

    user = GLOBAL_TENANT_STORE.authenticate(args.email, args.password)
    if not user:
        print("\n[!] Error: Invalid email or password credentials.")
        return 1

    token = create_access_token(user.user_id, user.tenant_id, user.role)
    print(f"\n[SUCCESS] Authenticated as '{user.full_name}' ({user.role.value})")
    print(f"          Workspace ID: {user.tenant_id}")
    print(f"          Bearer Token: {token}\n")
    print("-" * 70)
    return 0


def cmd_apikey_create(args: argparse.Namespace) -> int:
    """Generate a new programmatic API key for the default or specified workspace."""
    from src.auth.store import GLOBAL_TENANT_STORE

    print("=" * 70)
    print(f"[*] CLIENT FINDER SVC — Issue Programmatic API Key ('{args.name}')")
    print("=" * 70)

    tenant_id = args.tenant or "default_tenant"
    user_id = "default_admin"

    try:
        created = GLOBAL_TENANT_STORE.create_api_key(
            tenant_id=tenant_id,
            user_id=user_id,
            name=args.name,
            scopes=["read", "write"],
        )
        print("\n[SUCCESS] API Key Issued Successfully!")
        print(f"          Key ID      : {created.api_key.id}")
        print(f"          Name        : {created.api_key.name}")
        print(f"          Prefix      : {created.api_key.key_prefix}...")
        print(f"          Throughput  : {created.api_key.rate_limit_per_minute} req/min")
        print(f"          Secret Token: {created.raw_secret_key}")
        print("          (Save this secret key now. It will not be shown again!)\n")
        print("-" * 70)
        return 0
    except KeyError as err:
        print(f"\n[!] Error: {err}")
        return 1


def cmd_apikey_list(args: argparse.Namespace) -> int:
    """List active and revoked API keys for the workspace."""
    from src.auth.store import GLOBAL_TENANT_STORE

    tenant_id = args.tenant or "default_tenant"
    print("=" * 70)
    print(f"[*] CLIENT FINDER SVC — Workspace API Keys (Tenant: {tenant_id})")
    print("=" * 70)

    keys = GLOBAL_TENANT_STORE.list_api_keys(tenant_id)
    print(f"\n[+] Found {len(keys)} API Key(s):\n")
    for k in keys:
        status_str = "[ACTIVE]" if k.is_active else "[REVOKED]"
        print(
            f"  {status_str:<10} {k.name:<30} | {k.key_prefix}... | Used: {k.usage_count}x | Rate: {k.rate_limit_per_minute}/min"
        )
    print("-" * 70)
    return 0


def cmd_team_list(args: argparse.Namespace) -> int:
    """List team members and RBAC roles in the workspace."""
    from src.auth.store import GLOBAL_TENANT_STORE

    tenant_id = args.tenant or "default_tenant"
    tenant = GLOBAL_TENANT_STORE.get_tenant_by_id(tenant_id)
    if not tenant:
        print(f"[!] Workspace '{tenant_id}' not found.")
        return 1

    print("=" * 70)
    print(f"[*] CLIENT FINDER SVC — Team Roster & RBAC ({tenant.name})")
    print("=" * 70)
    print(f"Plan: {tenant.plan_tier.value} | Seats: {tenant.seats_used}/{tenant.max_seats}\n")

    for m in tenant.members:
        status_str = "[ACTIVE]" if m.is_active else "[INACTIVE]"
        print(f"  {status_str:<10} {m.full_name:<25} ({m.email:<30}) | Role: {m.role.value}")
    print("-" * 70)
    return 0


def cmd_team_invite(args: argparse.Namespace) -> int:
    """Invite a new member to the workspace."""
    from src.auth.schemas import UserRole
    from src.auth.store import GLOBAL_TENANT_STORE

    tenant_id = args.tenant or "default_tenant"
    print("=" * 70)
    print(f"[*] CLIENT FINDER SVC — Invite Team Member ({args.email})")
    print("=" * 70)

    try:
        role = UserRole(args.role) if args.role else UserRole.MEMBER
        member = GLOBAL_TENANT_STORE.invite_member(
            tenant_id=tenant_id,
            email=args.email,
            full_name=args.name or "Team Member",
            role=role,
        )
        print(
            f"\n[SUCCESS] Successfully invited {member.full_name} ({member.email}) as {member.role.value} to workspace {tenant_id}."
        )
        print("-" * 70)
        return 0
    except (ValueError, KeyError) as err:
        print(f"\n[!] Invite Error: {err}")
        return 1


def cmd_health_check(args: argparse.Namespace) -> int:
    """Run comprehensive production health probe across all subsystems."""
    from sqlalchemy import func, select

    from src.collectors.registry import DEFAULT_REGISTRY
    from src.database.connection import SessionLocal
    from src.database.models import OpportunityModel, ProjectModel
    from src.database.mongo import check_mongo_health, is_mongo_configured
    from src.vectors.engine import GLOBAL_VECTOR_STORE

    print("=" * 70)
    print("[*] CLIENT FINDER SVC — Production Subsystem Health Probe")
    print("=" * 70)

    # 1. SQL Database
    try:
        with SessionLocal() as session:
            total_proj = session.scalar(select(func.count(ProjectModel.id))) or 0
            total_opps = session.scalar(select(func.count(OpportunityModel.id))) or 0
            print(
                f"  [HEALTHY]     SQL Relational Database : Connected ({total_proj} projects, {total_opps} opps)"
            )
    except Exception as err:
        print(f"  [ERROR]       SQL Relational Database : Failed ({err})")

    # 2. Vector Index Engine
    try:
        vstats = GLOBAL_VECTOR_STORE.get_stats()
        print(
            f"  [HEALTHY]     Dense Vector Engine     : {vstats.total_indexed_documents} docs ({vstats.vector_dimension}-D, {vstats.index_memory_bytes / 1024:.1f} KB)"
        )
    except Exception as err:
        print(f"  [DEGRADED]    Dense Vector Engine     : Degraded ({err})")

    # 3. Collector Registry
    active_count = len(DEFAULT_REGISTRY.get_active_collectors())
    total_count = len(DEFAULT_REGISTRY.list_sources())
    print(f"  [OPERATIONAL] Collector Ingestion Hub : {active_count}/{total_count} active sources")

    # 4. MongoDB Hybrid Store
    if is_mongo_configured():
        mstatus = check_mongo_health()
        print(f"  [HEALTHY]     MongoDB Store           : {mstatus.get('status', 'unknown')}")
    else:
        print("  [STANDALONE]  MongoDB Store           : SQLite / Relational Primary Mode")

    print("-" * 70)
    return 0


def cmd_crm_list(args: argparse.Namespace) -> int:
    """List configured CRM integrations for the workspace."""
    from src.crm.syncer import GLOBAL_CRM_SYNCER

    tenant_id = args.tenant or "default_tenant"
    print("=" * 70)
    print(f"[*] CLIENT FINDER SVC — Enterprise CRM Integrations ({tenant_id})")
    print("=" * 70)

    configs = GLOBAL_CRM_SYNCER.list_configs(tenant_id)
    for c in configs:
        status_str = "[ENABLED]" if c.is_enabled else "[DISABLED]"
        print(
            f"  {status_str:<10} {c.provider.value:<16} | Direction: {c.default_direction.value:<14} | DB/Base: {c.base_or_db_id or 'N/A'}"
        )
    print("-" * 70)
    return 0


def cmd_crm_test(args: argparse.Namespace) -> int:
    """Test authentication and connectivity for a CRM provider."""
    from src.crm.schemas import CRMProvider
    from src.crm.syncer import GLOBAL_CRM_SYNCER

    tenant_id = args.tenant or "default_tenant"
    try:
        provider = CRMProvider(args.provider.upper())
    except ValueError:
        print(
            f"[!] Invalid CRM provider '{args.provider}'. Choices: {[p.value for p in CRMProvider]}"
        )
        return 1

    print("=" * 70)
    print(f"[*] CLIENT FINDER SVC — Testing {provider.value} Integration ({tenant_id})")
    print("=" * 70)

    success, message = GLOBAL_CRM_SYNCER.test_connection(tenant_id, provider)
    status_badge = "[SUCCESS]" if success else "[ERROR]"
    print(f"\n{status_badge} {message}\n")
    print("-" * 70)
    return 0 if success else 1


def cmd_crm_sync(args: argparse.Namespace) -> int:
    """Execute on-demand CRM pipeline synchronization."""
    from src.crm.schemas import CRMProvider, CRMSyncRequest, SyncDirection
    from src.crm.syncer import GLOBAL_CRM_SYNCER

    tenant_id = args.tenant or "default_tenant"
    try:
        provider = CRMProvider(args.provider.upper())
    except ValueError:
        print(
            f"[!] Invalid CRM provider '{args.provider}'. Choices: {[p.value for p in CRMProvider]}"
        )
        return 1

    print("=" * 70)
    print(f"[*] CLIENT FINDER SVC — CRM Synchronization ({provider.value})")
    print("=" * 70)

    direction = SyncDirection.PUSH_TO_CRM
    if args.direction:
        try:
            direction = SyncDirection(args.direction.upper())
        except ValueError:
            pass

    req = CRMSyncRequest(
        provider=provider,
        direction=direction,
        dry_run=args.dry_run,
    )

    try:
        res = GLOBAL_CRM_SYNCER.sync_opportunities(tenant_id, req)
        mode_str = "[DRY-RUN] " if res.is_dry_run else ""
        print(
            f"\n[SUCCESS] {mode_str}Processed {res.records_processed} records in {res.duration_ms}ms:"
        )
        print(f"          Created : {res.records_created}")
        print(f"          Updated : {res.records_updated}")
        print(f"          Skipped : {res.records_skipped}")
        print(f"          Failed  : {res.records_failed}\n")

        for r in res.record_results[:5]:
            print(f"  -> [{r.action:<12}] {r.project_title[:40]:<42} | CRM ID: {r.crm_record_id}")
        print("-" * 70)
        return 0
    except Exception as err:
        print(f"\n[!] Sync Error: {err}")
        return 1


def cmd_finance_summary(args: argparse.Namespace) -> int:
    """Print revenue intelligence KPIs and tax reserve estimate."""
    from src.finance.ledger import GLOBAL_LEDGER

    tenant_id = args.tenant or "default_tenant"
    print("=" * 70)
    print(f"[*] CLIENT FINDER SVC — Revenue Intelligence ({tenant_id})")
    print("=" * 70)

    snap = GLOBAL_LEDGER.get_revenue_snapshot(tenant_id)
    print(f"\n  Gross Billed    (YTD) : ${snap.gross_billed:>12,.2f}")
    print(f"  Gross Collected (YTD) : ${snap.gross_collected:>12,.2f}")
    print(f"  Outstanding AR        : ${snap.outstanding_ar:>12,.2f}")
    print(f"  Total Expenses        : ${snap.total_expenses:>12,.2f}")
    print(f"  Net Profit            : ${snap.net_profit:>12,.2f}")
    print(f"  Tax Reserve (28%)     : ${snap.tax_reserve_suggested:>12,.2f}")
    print(f"\n  Invoices Issued  : {snap.invoices_issued}")
    print(f"  Invoices Paid    : {snap.invoices_paid}")
    print("-" * 70)
    return 0


def cmd_invoice_list(args: argparse.Namespace) -> int:
    """List all invoices with status and amounts."""
    from src.finance.ledger import GLOBAL_LEDGER

    tenant_id = args.tenant or "default_tenant"
    print("=" * 70)
    print(f"[*] CLIENT FINDER SVC — Invoice Register ({tenant_id})")
    print("=" * 70)

    invoices = GLOBAL_LEDGER.list_invoices(tenant_id)
    if not invoices:
        print("  No invoices found.")
    else:
        for inv in invoices:
            amt = inv.taxable_amount * (1 + inv.tax_rate_pct / 100)
            print(
                f"  [{inv.status:<14}] {inv.invoice_number:<10} | {inv.client_name[:28]:<30} | "
                f"${amt:>8,.2f} | Due: {inv.due_date}"
            )
    print("-" * 70)
    return 0


def cmd_invoice_create(args: argparse.Namespace) -> int:
    """Create a new invoice from CLI arguments."""
    from src.finance.ledger import GLOBAL_LEDGER
    from src.finance.schemas import CreateInvoiceRequest, InvoiceLineItem

    tenant_id = args.tenant or "default_tenant"
    req = CreateInvoiceRequest(
        client_name=args.client,
        line_items=[InvoiceLineItem(description=args.description, quantity=1, unit_price=args.amount)],
        tax_rate_pct=args.tax_rate,
        due_days=args.due_days,
    )
    inv = GLOBAL_LEDGER.create_invoice(tenant_id, req)
    print("=" * 70)
    print(f"[*] CLIENT FINDER SVC — Invoice Created")
    print("=" * 70)
    print(f"\n  Invoice Number : {inv.invoice_number}")
    print(f"  Client         : {inv.client_name}")
    print(f"  Total Amount   : ${inv.total_amount:,.2f}")
    print(f"  Status         : {inv.status.value}")
    print(f"  Due Date       : {inv.due_date}")
    print("-" * 70)
    return 0


def cmd_contract_list(args: argparse.Namespace) -> int:
    """List all legal contracts in the registry."""
    from src.contracts.registry import GLOBAL_CONTRACT_REGISTRY

    tenant_id = args.tenant or "default_tenant"
    print("=" * 70)
    print(f"[*] CLIENT FINDER SVC — Legal Contract Register ({tenant_id})")
    print("=" * 70)

    contracts = GLOBAL_CONTRACT_REGISTRY.list_contracts(tenant_id)
    if not contracts:
        print("  No contracts found.")
    else:
        for c in contracts:
            print(
                f"  [{c.status.value:<17}] {c.contract_number:<9} | {c.title[:32]:<34} | "
                f"Sigs: {len(c.signatures)}/2 | Eff: {c.effective_date}"
            )
    print("-" * 70)
    return 0


def cmd_contract_generate(args: argparse.Namespace) -> int:
    """Generate a protective legal contract."""
    from src.contracts.registry import GLOBAL_CONTRACT_REGISTRY
    from src.contracts.schemas import ContractType, GenerateContractRequest

    tenant_id = args.tenant or "default_tenant"
    req = GenerateContractRequest(
        contract_type=ContractType(args.type),
        client_name=args.client,
        project_title=args.title,
        payment_terms_days=args.terms,
    )
    contract = GLOBAL_CONTRACT_REGISTRY.create_contract(tenant_id, req)
    print("=" * 70)
    print(f"[*] CLIENT FINDER SVC — Contract Generated ({contract.contract_number})")
    print("=" * 70)
    print(f"\n  Type           : {contract.contract_type.value}")
    print(f"  Title          : {contract.title}")
    print(f"  Client         : {contract.client_name}")
    print(f"  Effective Date : {contract.effective_date}")
    print("\n" + contract.content_markdown[:300] + "\n...")
    print("-" * 70)
    return 0


def cmd_contract_audit(args: argparse.Namespace) -> int:
    """Audit raw legal text for clause risks and traps."""
    from src.contracts.analyzer import GLOBAL_LEGAL_ANALYZER
    from src.contracts.schemas import AuditContractRequest

    text = args.text
    if not text:
        print("[!] Error: --text argument is required for contract audit.")
        return 1

    res = GLOBAL_LEGAL_ANALYZER.audit_contract(AuditContractRequest(contract_title="CLI Audit", contract_text=text))
    print("=" * 70)
    print(f"[*] CLIENT FINDER SVC — Legal Risk Audit")
    print("=" * 70)
    print(f"\n  Overall Risk Score : {res.overall_risk_score} / 100")
    print(f"  Recommendation     : {res.recommendation}")
    print(f"  Critical Risks     : {res.critical_count} | High Risks: {res.high_count} | Medium Risks: {res.medium_count}")
    print("\n  Risk Findings:")
    for f in res.findings:
        print(f"   -> [{f.severity:<8}] {f.clause_title}")
        print(f"      Explanation: {f.explanation}")
        print(f"      Revision   : {f.suggested_revision}")
    print("-" * 70)
    return 0


def cmd_executive_status(args: argparse.Namespace) -> int:
    """Print executive agent status, active policy rules, and velocity KPIs."""
    from src.executive.telemetry import GLOBAL_EXECUTIVE_TELEMETRY

    tenant_id = args.tenant or "default_tenant"
    kpis = GLOBAL_EXECUTIVE_TELEMETRY.get_kpis(tenant_id)
    pol = kpis.active_policies

    print("=" * 70)
    print(f"[*] CLIENT FINDER SVC — AI Executive Agent Status ({tenant_id})")
    print("=" * 70)
    print(f"\n  Autonomy Mode        : {kpis.current_mode.value}")
    print(f"  Min Score Floor      : {pol.min_score_threshold}")
    print(f"  Max Scam Risk Floor  : {pol.scam_risk_floor}")
    print(f"  Auto SOW Generation  : {pol.auto_generate_sow}")
    print(f"  Auto Deposit Invoice : {pol.auto_issue_deposit_invoice}")
    print(f"\n  Cycles Executed      : {kpis.total_cycles_run}")
    print(f"  Proposals Drafted    : {kpis.total_proposals_auto_drafted}")
    print(f"  Contracts Generated  : {kpis.total_contracts_auto_generated}")
    print(f"  Developer Time Saved : {kpis.total_time_saved_hours:.1f} hours")
    print(f"  Velocity Multiplier  : {kpis.pipeline_velocity_multiplier:.1f}x")
    print("-" * 70)
    return 0


def cmd_executive_run(args: argparse.Namespace) -> int:
    """Trigger an immediate 7-step autonomous lead acquisition cycle."""
    from src.executive.coordinator import GLOBAL_EXECUTIVE_COORDINATOR

    tenant_id = args.tenant or "default_tenant"
    res = GLOBAL_EXECUTIVE_COORDINATOR.run_autonomous_cycle(tenant_id)

    print("=" * 70)
    print(f"[*] CLIENT FINDER SVC — Autonomous Executive Cycle Executed ({res.cycle_id})")
    print("=" * 70)
    print(f"\n  Duration               : {res.duration_ms:.1f} ms")
    print(f"  Opportunities Scanned  : {res.opportunities_scanned}")
    print(f"  Qualified Leads        : {res.qualified_leads}")
    print(f"  Proposals Auto-Drafted : {res.proposals_drafted}")
    print(f"  Outreach Enrolled      : {res.outreach_sequences_initiated}")
    print(f"  Contracts Auto-Drafted : {res.contracts_generated}")
    print("\n  Actions Executed:")
    for a in res.actions:
        print(f"   -> [{a.category.value:<18}] {a.opportunity_title[:32]:<34} | Saved {a.estimated_time_saved_mins:.0f}m")
    print("-" * 70)
    return 0


def cmd_executive_config(args: argparse.Namespace) -> int:
    """Update autonomous policy rules from CLI."""
    from src.executive.schemas import AutonomousPolicyConfig, AutonomyMode
    from src.executive.telemetry import GLOBAL_EXECUTIVE_TELEMETRY

    tenant_id = args.tenant or "default_tenant"
    current = GLOBAL_EXECUTIVE_TELEMETRY.get_policy(tenant_id)
    if args.mode:
        current.autonomy_mode = AutonomyMode(args.mode)
    if args.min_score is not None:
        current.min_score_threshold = args.min_score
    if args.scam_floor is not None:
        current.scam_risk_floor = args.scam_floor

    updated = GLOBAL_EXECUTIVE_TELEMETRY.update_policy(tenant_id, current)
    print("=" * 70)
    print(f"[*] CLIENT FINDER SVC — Executive Policies Updated ({tenant_id})")
    print("=" * 70)
    print(f"\n  Mode            : {updated.autonomy_mode.value}")
    print(f"  Min Score Floor : {updated.min_score_threshold}")
    print(f"  Scam Risk Floor : {updated.scam_risk_floor}")
    print("-" * 70)
    return 0






def cmd_sources(args: argparse.Namespace) -> int:
    """List all registered collectors and their health metrics."""
    from src.collectors.registry import DEFAULT_REGISTRY

    print("=" * 70)
    print("[*] CLIENT FINDER SVC — Opportunity Collectors Health")
    print("=" * 70)
    states = DEFAULT_REGISTRY.get_all_states()
    for s in states:
        status_tag = "[ACTIVE]" if s.enabled else "[DISABLED]"
        circuit_tag = "OPEN" if s.circuit_broken else "CLOSED"
        print(
            f"{status_tag:<10} {s.source_name:<25} | Circuit: {circuit_tag:<8} | Runs: {s.success_count + s.failure_count} | Success: {s.success_rate:.1f}%"
        )
    print("-" * 70)
    return 0


def cmd_sources_toggle(args: argparse.Namespace) -> int:
    """Enable or disable a registered collector."""
    from src.collectors.registry import DEFAULT_REGISTRY

    try:
        if args.enable:
            new_state = DEFAULT_REGISTRY.toggle(args.name, enable=True)
        elif args.disable:
            new_state = DEFAULT_REGISTRY.toggle(args.name, enable=False)
        else:
            new_state = DEFAULT_REGISTRY.toggle(args.name)
        print(f"[+] Collector '{args.name}' is now {'ENABLED' if new_state else 'DISABLED'}.")
        return 0
    except KeyError:
        print(f"[!] Collector '{args.name}' not found in registry.")
        return 1


def cmd_freelance_clients(args: argparse.Namespace) -> int:
    """List and export direct freelance clients, founders, and contract gigs."""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from src.intelligence.client_contact import GLOBAL_CONTACT_EXTRACTOR
    from src.processors.freelance_classifier import GLOBAL_FREELANCE_CLASSIFIER

    init_db()
    print("=" * 70)
    print("[*] CLIENT FINDER SVC -- Direct Freelance Client Opportunities")
    print("=" * 70)

    with SessionLocal() as session:
        query = (
            select(ProjectModel)
            .options(selectinload(ProjectModel.opportunity))
            .order_by(ProjectModel.score.desc().nullslast(), ProjectModel.created_at.desc())
        )
        if args.min_score:
            query = query.where(ProjectModel.score >= args.min_score)

        projects = session.scalars(query).all()
        direct_clients = []
        for p in projects:
            cls_res = GLOBAL_FREELANCE_CLASSIFIER.classify({
                "title": p.title,
                "description": p.description,
                "source": p.source,
                "is_direct_client": p.source in ("Client Leads", "Upwork", "Hacker News"),
            })
            if cls_res.is_direct_client:
                contact = GLOBAL_CONTACT_EXTRACTOR.extract(p.description, default_url=p.source_url)
                direct_clients.append((p, cls_res, contact))

        if not direct_clients:
            print("[!] No direct freelance clients found matching criteria.")
            return 0

        print(f"[+] Found {len(direct_clients)} Direct Freelance Client(s):\n")
        limit = args.limit or 20
        for idx, (p, cls_res, contact) in enumerate(direct_clients[:limit], 1):
            score_display = f"{p.score:.1f}/100" if p.score else "N/A"
            budget_display = f"${p.budget:,.0f} {p.currency or 'USD'}" if p.budget else "Unstated / Milestone"
            contact_str = contact.primary_action_url or p.source_url
            channels = []
            if contact.emails:
                channels.append(f"Email: {', '.join(contact.emails)}")
            if contact.calendly_links:
                channels.append(f"Calendly: {', '.join(contact.calendly_links)}")
            if contact.telegram_handles:
                channels.append(f"Telegram: {', '.join(contact.telegram_handles)}")

            channel_info = " | ".join(channels) if channels else "Direct Source Link"

            print(f"[{idx}] {p.title}")
            print(f"    Client Type : {cls_res.client_type.value} ({cls_res.engagement_type.value})")
            print(f"    Source      : {p.source} | Score: {score_display} | Budget: {budget_display}")
            print(f"    Reach Out   : {channel_info}")
            print(f"    Action URL  : {contact_str}")
            print("-" * 70)

    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build root CLI argument parser and subcommands."""
    parser = argparse.ArgumentParser(
        prog="client-finder",
        description="CLIENT FINDER SVC — Automated Lead Discovery, Scoring, and Application Tracking CLI",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Freelance Clients Command
    p_freelance = subparsers.add_parser(
        "freelance-clients", help="List direct freelance clients and founder gigs (excluding employee jobs)"
    )
    p_freelance.add_argument("--min-score", type=float, default=None, help="Filter by minimum score")
    p_freelance.add_argument("--limit", type=int, default=20, help="Max clients to display")
    p_freelance.set_defaults(func=cmd_freelance_clients)

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
        type=str,
        default=PitchAngle.TECHNICAL_EXPERT.value,
        choices=[a.value for a in PitchAngle],
        help="Optional pitch angle override",
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
    p_pitch.add_argument("--copy-only", action="store_true", help="Only output proposal body text")
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
    p_apply = subparsers.add_parser(
        "apply", help="Track a new application or update an existing one"
    )
    p_apply.add_argument(
        "--project-id", type=int, required=True, help="Database ID of project applied to"
    )
    p_apply.add_argument(
        "--status",
        type=str,
        default=ApplicationStatus.APPLIED.value,
        choices=[s.value for s in ApplicationStatus],
        help="Application status (default: APPLIED)",
    )
    p_apply.add_argument("--budget", type=float, default=None, help="Proposed commercial budget")
    p_apply.add_argument("--currency", type=str, default="USD", help="Currency code")
    p_apply.add_argument(
        "--angle", choices=[a.value for a in PitchAngle], default=None, help="Pitch angle"
    )
    p_apply.add_argument("--notes", type=str, default=None, help="Context notes or follow-up logs")
    p_apply.set_defaults(func=cmd_apply)

    # 8. Apps Command
    p_apps = subparsers.add_parser("apps", help="List tracked applications by funnel status")
    p_apps.add_argument(
        "--status",
        type=str,
        default=None,
        choices=[s.value for s in ApplicationStatus],
        help="Filter by status",
    )
    p_apps.add_argument(
        "--limit", type=int, default=20, help="Max applications to display (default: 20)"
    )
    p_apps.set_defaults(func=cmd_apps)

    # 9. Funnel Command
    p_funnel = subparsers.add_parser(
        "funnel", help="Display conversion funnel and revenue analytics"
    )
    p_funnel.set_defaults(func=cmd_funnel)

    # 10. Sources Command
    p_sources = subparsers.add_parser(
        "sources", help="List all registered opportunity collectors and health metrics"
    )
    p_sources.set_defaults(func=cmd_sources)

    # 11. Sources Toggle Command
    p_toggle = subparsers.add_parser(
        "sources-toggle", help="Enable or disable a specific opportunity collector"
    )
    p_toggle.add_argument(
        "--name", type=str, required=True, help="Exact name of the collector to toggle"
    )
    p_toggle.add_argument(
        "--enable", action="store_true", default=None, help="Explicitly enable the collector"
    )
    p_toggle.add_argument(
        "--disable", action="store_true", default=None, help="Explicitly disable the collector"
    )
    p_toggle.set_defaults(func=cmd_sources_toggle)

    # 12. Outreach Commands
    p_outreach = subparsers.add_parser(
        "outreach", help="Manage automated multi-touch outreach cadences"
    )
    p_outreach_sub = p_outreach.add_subparsers(dest="outreach_cmd", help="Outreach actions")

    p_outreach_create = p_outreach_sub.add_parser("create", help="Create an outreach cadence")
    p_outreach_create.add_argument(
        "--app-id", type=int, required=True, help="Target application ID"
    )
    p_outreach_create.add_argument("--title", type=str, required=True, help="Target project title")
    p_outreach_create.add_argument("--client", type=str, default="Client", help="Client name")
    p_outreach_create.add_argument("--angle", type=str, default=None, help="Pitch angle override")
    p_outreach_create.set_defaults(func=cmd_outreach_create)

    p_outreach_list = p_outreach_sub.add_parser("list", help="List tracked outreach cadences")
    p_outreach_list.add_argument("--status", type=str, default=None, help="Filter by status")
    p_outreach_list.set_defaults(func=cmd_outreach_list)

    p_outreach_advance = p_outreach_sub.add_parser("advance", help="Advance sequence to next step")
    p_outreach_advance.add_argument("--seq-id", type=str, required=True, help="Sequence ID")
    p_outreach_advance.set_defaults(func=cmd_outreach_advance)

    # 13. Reply Analyzer Command
    p_reply = subparsers.add_parser(
        "reply", help="Classify inbound client message intent and synthesize response"
    )
    p_reply.add_argument("--text", type=str, required=True, help="Raw message received from client")
    p_reply.add_argument("--app-id", type=int, default=None, help="Application ID to update in DB")
    p_reply.add_argument("--title", type=str, default=None, help="Project title")
    p_reply.add_argument("--client", type=str, default=None, help="Client name")
    p_reply.add_argument("--dry-run", action="store_true", help="Do not update database status")
    p_reply.set_defaults(func=cmd_reply_analyze)

    # 14. A/B Stats Command
    p_ab = subparsers.add_parser(
        "ab-stats", help="Display A/B pitch testing metrics and category routing"
    )
    p_ab.set_defaults(func=cmd_ab_stats)

    # 15. Client Dossier Command
    p_dossier = subparsers.add_parser(
        "dossier", help="Synthesize deep client background intelligence and trust score"
    )
    p_dossier.add_argument("--project-id", type=int, default=None, help="Database ID of project")
    p_dossier.add_argument("--title", type=str, default=None, help="Project title")
    p_dossier.add_argument("--client", type=str, default="Client", help="Client name")
    p_dossier.add_argument("--desc", type=str, default="", help="Project description")
    p_dossier.add_argument("--budget", type=float, default=None, help="Advertised budget")
    p_dossier.set_defaults(func=cmd_dossier)

    # 16. Scam Sentinel Command
    p_scam = subparsers.add_parser(
        "scam-audit", help="Audit project text for scams, fraud, and unpaid test traps"
    )
    p_scam.add_argument("--text", type=str, required=True, help="Project text to audit")
    p_scam.add_argument("--title", type=str, default=None, help="Optional title")
    p_scam.add_argument("--budget", type=float, default=None, help="Advertised budget")
    p_scam.set_defaults(func=cmd_scam_audit)

    # 17. Feasibility Command
    p_feas = subparsers.add_parser(
        "feasibility", help="Evaluate scope complexity vs. proposed budget feasibility"
    )
    p_feas.add_argument("--title", type=str, required=True, help="Project title")
    p_feas.add_argument("--budget", type=float, required=True, help="Proposed budget ($)")
    p_feas.add_argument("--desc", type=str, default="", help="Project requirements / scope")
    p_feas.add_argument("--skills", type=str, default=None, help="Comma-separated skills")
    p_feas.set_defaults(func=cmd_feasibility)

    # 18. Semantic Search Command
    p_vsearch = subparsers.add_parser(
        "search-semantic", help="Natural language dense semantic vector search"
    )
    p_vsearch.add_argument("--query", type=str, required=True, help="Natural language query string")
    p_vsearch.add_argument("--limit", type=int, default=10, help="Max results to return")
    p_vsearch.add_argument("--min-sim", type=float, default=0.2, help="Min cosine similarity")
    p_vsearch.set_defaults(func=cmd_search_semantic)

    # 19. Hybrid Search Command
    p_hyb = subparsers.add_parser("search-hybrid", help="Hybrid dense vector + lexical BM25 search")
    p_hyb.add_argument("--query", type=str, required=True, help="Search query string")
    p_hyb.add_argument("--alpha", type=float, default=0.5, help="Semantic weight (0.0 to 1.0)")
    p_hyb.add_argument("--limit", type=int, default=10, help="Max results to return")
    p_hyb.add_argument("--min-score", type=float, default=0.1, help="Min fused hybrid score")
    p_hyb.set_defaults(func=cmd_search_hybrid)

    # 20. Portfolio RAG Matcher Command
    p_rag = subparsers.add_parser(
        "rag-match", help="Semantically retrieve matching developer case studies for proposal RAG"
    )
    p_rag.add_argument("--title", type=str, required=True, help="Target project title")
    p_rag.add_argument("--desc", type=str, default="", help="Target project description")
    p_rag.add_argument("--skills", type=str, default=None, help="Target skills comma-separated")
    p_rag.add_argument("--top-k", type=int, default=3, help="Max case studies to match")
    p_rag.set_defaults(func=cmd_rag_match)

    # 21. Vectors Reindex Command
    p_reidx = subparsers.add_parser(
        "vectors-reindex", help="Rebuild the in-memory dense vector store from SQL database"
    )
    p_reidx.set_defaults(func=cmd_vectors_reindex)

    # 22. Auth Registration Command
    p_auth_reg = subparsers.add_parser(
        "auth-register", help="Register a new user account and dedicated workspace"
    )
    p_auth_reg.add_argument("--email", type=str, required=True, help="User email address")
    p_auth_reg.add_argument("--password", type=str, required=True, help="User password")
    p_auth_reg.add_argument("--name", type=str, required=True, help="Full name")
    p_auth_reg.add_argument("--workspace", type=str, default="", help="Workspace organization name")
    p_auth_reg.set_defaults(func=cmd_auth_register)

    # 23. Auth Login Command
    p_auth_log = subparsers.add_parser(
        "auth-login", help="Authenticate with email/password and obtain JWT token"
    )
    p_auth_log.add_argument("--email", type=str, required=True, help="User email address")
    p_auth_log.add_argument("--password", type=str, required=True, help="User password")
    p_auth_log.set_defaults(func=cmd_auth_login)

    # 24. API Key Create Command
    p_key_create = subparsers.add_parser(
        "apikey-create", help="Generate a new programmatic API key"
    )
    p_key_create.add_argument("--name", type=str, required=True, help="API key descriptive name")
    p_key_create.add_argument("--tenant", type=str, default=None, help="Tenant workspace ID")
    p_key_create.set_defaults(func=cmd_apikey_create)

    # 25. API Key List Command
    p_key_list = subparsers.add_parser(
        "apikey-list", help="List active and revoked API keys for the workspace"
    )
    p_key_list.add_argument("--tenant", type=str, default=None, help="Tenant workspace ID")
    p_key_list.set_defaults(func=cmd_apikey_list)

    # 26. Team List Command
    p_team_list = subparsers.add_parser(
        "team-list", help="List team members and RBAC roles in workspace"
    )
    p_team_list.add_argument("--tenant", type=str, default=None, help="Tenant workspace ID")
    p_team_list.set_defaults(func=cmd_team_list)

    # 27. Team Invite Command
    p_team_inv = subparsers.add_parser(
        "team-invite", help="Invite a new team member with specific RBAC role"
    )
    p_team_inv.add_argument("--email", type=str, required=True, help="Member email address")
    p_team_inv.add_argument("--name", type=str, default="Team Member", help="Member full name")
    p_team_inv.add_argument(
        "--role",
        type=str,
        default="MEMBER",
        choices=["ADMIN", "MEMBER", "READONLY"],
        help="Assigned RBAC role",
    )
    p_team_inv.add_argument("--tenant", type=str, default=None, help="Tenant workspace ID")
    p_team_inv.set_defaults(func=cmd_team_invite)

    # 28. Health Check Probe Command
    p_hcheck = subparsers.add_parser(
        "health-check", help="Run comprehensive production subsystem health probe"
    )
    p_hcheck.set_defaults(func=cmd_health_check)

    # 29. CRM List Command
    p_crm_list = subparsers.add_parser("crm-list", help="List all configured CRM integrations")
    p_crm_list.add_argument("--tenant", type=str, default=None, help="Tenant workspace ID")
    p_crm_list.set_defaults(func=cmd_crm_list)

    # 30. CRM Test Command
    p_crm_test = subparsers.add_parser(
        "crm-test", help="Test connectivity for a CRM provider (HUBSPOT, NOTION, AIRTABLE, LINEAR)"
    )
    p_crm_test.add_argument(
        "--provider",
        type=str,
        required=True,
        choices=["HUBSPOT", "NOTION", "AIRTABLE", "LINEAR"],
        help="CRM platform to test",
    )
    p_crm_test.add_argument("--tenant", type=str, default=None, help="Tenant workspace ID")
    p_crm_test.set_defaults(func=cmd_crm_test)

    # 31. CRM Sync Command
    p_crm_sync = subparsers.add_parser("crm-sync", help="Synchronize opportunities to external CRM")
    p_crm_sync.add_argument(
        "--provider",
        type=str,
        default="HUBSPOT",
        choices=["HUBSPOT", "NOTION", "AIRTABLE", "LINEAR"],
        help="Target CRM platform",
    )
    p_crm_sync.add_argument(
        "--direction",
        type=str,
        default="PUSH_TO_CRM",
        choices=["PUSH_TO_CRM", "PULL_FROM_CRM", "BI_DIRECTIONAL"],
        help="Sync direction",
    )
    p_crm_sync.add_argument("--dry-run", action="store_true", help="Simulate sync without writes")
    p_crm_sync.add_argument("--tenant", type=str, default=None, help="Tenant workspace ID")
    p_crm_sync.set_defaults(func=cmd_crm_sync)

    # 32. Finance Summary Command
    p_fin_summary = subparsers.add_parser(
        "finance-summary", help="Print YTD revenue KPIs, net profit, and tax reserve estimate"
    )
    p_fin_summary.add_argument("--tenant", type=str, default=None, help="Tenant workspace ID")
    p_fin_summary.set_defaults(func=cmd_finance_summary)

    # 33. Invoice List Command
    p_inv_list = subparsers.add_parser("invoice-list", help="List all invoices with status and amounts")
    p_inv_list.add_argument("--tenant", type=str, default=None, help="Tenant workspace ID")
    p_inv_list.set_defaults(func=cmd_invoice_list)

    # 34. Invoice Create Command
    p_inv_create = subparsers.add_parser("invoice-create", help="Issue a new freelance invoice")
    p_inv_create.add_argument("--client", type=str, required=True, help="Client company or individual name")
    p_inv_create.add_argument("--description", type=str, required=True, help="Service or project description")
    p_inv_create.add_argument("--amount", type=float, required=True, help="Total invoice amount in USD")
    p_inv_create.add_argument("--tax-rate", type=float, default=10.0, help="Tax rate percentage (default: 10)")
    p_inv_create.add_argument("--due-days", type=int, default=30, help="Payment term in days (default: 30)")
    p_inv_create.add_argument("--tenant", type=str, default=None, help="Tenant workspace ID")
    p_inv_create.set_defaults(func=cmd_invoice_create)

    # 35. Contract List Command
    p_ctr_list = subparsers.add_parser("contract-list", help="List all stored legal agreements")
    p_ctr_list.add_argument("--tenant", type=str, default=None, help="Tenant workspace ID")
    p_ctr_list.set_defaults(func=cmd_contract_list)

    # 36. Contract Generate Command
    p_ctr_gen = subparsers.add_parser("contract-generate", help="Generate a protective legal contract (MSA, SOW, NDA)")
    p_ctr_gen.add_argument("--type", type=str, default="MSA", choices=["MSA", "SOW", "NDA", "CONTRACTOR_AGREEMENT"], help="Agreement type")
    p_ctr_gen.add_argument("--client", type=str, required=True, help="Client company or individual name")
    p_ctr_gen.add_argument("--title", type=str, required=True, help="Project title")
    p_ctr_gen.add_argument("--terms", type=int, default=14, help="Payment terms in days")
    p_ctr_gen.add_argument("--tenant", type=str, default=None, help="Tenant workspace ID")
    p_ctr_gen.set_defaults(func=cmd_contract_generate)

    # 37. Contract Audit Command
    p_ctr_audit = subparsers.add_parser("contract-audit", help="Audit raw contract text for legal traps and risks")
    p_ctr_audit.add_argument("--text", type=str, required=True, help="Raw contract text to audit")
    p_ctr_audit.set_defaults(func=cmd_contract_audit)

    # 38. Executive Status Command
    p_exec_stat = subparsers.add_parser("executive-status", help="Print AI Executive Agent status, policy rules, and velocity KPIs")
    p_exec_stat.add_argument("--tenant", type=str, default=None, help="Tenant workspace ID")
    p_exec_stat.set_defaults(func=cmd_executive_status)

    # 39. Executive Run Command
    p_exec_run = subparsers.add_parser("executive-run", help="Trigger an immediate 7-step autonomous lead acquisition cycle")
    p_exec_run.add_argument("--tenant", type=str, default=None, help="Tenant workspace ID")
    p_exec_run.set_defaults(func=cmd_executive_run)

    # 40. Executive Config Command
    p_exec_cfg = subparsers.add_parser("executive-config", help="Update autonomous executive policy rules")
    p_exec_cfg.add_argument("--mode", type=str, choices=["DISABLED", "SEMI_AUTONOMOUS", "FULLY_AUTONOMOUS"], help="Autonomy execution mode")
    p_exec_cfg.add_argument("--min-score", type=float, help="Minimum lead score floor")
    p_exec_cfg.add_argument("--scam-floor", type=float, help="Maximum acceptable scam risk floor")
    p_exec_cfg.add_argument("--tenant", type=str, default=None, help="Tenant workspace ID")
    p_exec_cfg.set_defaults(func=cmd_executive_config)

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
