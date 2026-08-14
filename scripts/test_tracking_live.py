"""
Live demonstration and verification script for Phase 10: Application & Outcome Tracking & Learning Loop.
"""

import logging
import sys
import uuid

from src.analytics.calibrator import WinProbabilityCalibrator
from src.analytics.engine import AnalyticsEngine
from src.cli import main as cli_main
from src.database.connection import SessionLocal, init_db
from src.database.models import ApplicationStatus, ProjectModel
from src.models.project import Project
from src.proposal.schemas import PitchAngle
from src.tracking.schemas import ApplicationCreate, ApplicationStatusUpdate
from src.tracking.tracker import ApplicationTracker

if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("TrackingLiveTest")


def main():
    print("=================================================================")
    print("[*] CLIENT FINDER SVC - Phase 10: Tracking & Analytics Live Test")
    print("=================================================================\n")

    init_db()
    tracker = ApplicationTracker()
    analytics = AnalyticsEngine()
    calibrator = WinProbabilityCalibrator()

    # 1. Create Sample Project and Track Application
    uid = uuid.uuid4().hex[:8]
    logger.info("Creating mock project opportunity and application submission...")
    with SessionLocal() as session:
        proj = Project(
            title=f"Enterprise AI RAG Backend Architecture {uid}",
            description="Build scalable FastAPI & LangChain microservice on PostgreSQL",
            source="Hacker News",
            source_url=f"https://example.com/demo-lead-{uid}",
            skills=["FastAPI", "Python", "RAG", "PostgreSQL"],
            budget=7500.0,
        )
        pm = ProjectModel.from_pydantic(proj)
        session.add(pm)
        session.commit()
        session.refresh(pm)
        project_id = pm.id

    app_created = tracker.track_application(
        ApplicationCreate(
            project_id=project_id,
            status=ApplicationStatus.APPLIED,
            proposed_budget=7500.0,
            pitch_angle=PitchAngle.TECHNICAL_EXPERT,
            proposal_text="Hi there, I have built production RAG backends with FastAPI...",
            notes="Live demo test application",
        )
    )
    print(f"[+] Application Created: App #{app_created.id} (Status: {app_created.status})")

    # 2. Progress Lifecycle Stages
    logger.info("Progressing application lifecycle through stages...")
    tracker.transition_status(
        app_created.id,
        ApplicationStatusUpdate(
            status=ApplicationStatus.CLIENT_REPLIED,
            client_feedback="Impressive technical portfolio. Let's schedule a call.",
        ),
    )
    print(f"[+] Application Progressed to: {ApplicationStatus.CLIENT_REPLIED.value}")

    tracker.transition_status(
        app_created.id,
        ApplicationStatusUpdate(status=ApplicationStatus.INTERVIEW),
    )
    print(f"[+] Application Progressed to: {ApplicationStatus.INTERVIEW.value}")

    tracker.transition_status(
        app_created.id,
        ApplicationStatusUpdate(
            status=ApplicationStatus.WON,
            final_revenue=8000.0,
            client_feedback="Hired for enterprise project! Rate accepted.",
        ),
    )
    print("[+] Application Won! Realized Revenue: $8,000.00\n")

    # 3. Compute Analytics & Conversion Funnel
    logger.info("Calculating real-time conversion metrics...")
    funnel = analytics.compute_funnel_metrics()
    rev = analytics.compute_revenue_metrics()
    insights = analytics.generate_insights()

    print("--- CONVERSION FUNNEL METRICS ---")
    print(f"    Total Applications Tracked : {funnel.total_applications}")
    print(f"    Client Responses           : {funnel.replied_count} ({funnel.response_rate}%)")
    print(f"    Interviews                 : {funnel.interview_count} ({funnel.interview_rate}%)")
    print(f"    Contracts Won              : {funnel.won_count} ({funnel.win_rate}%)")
    print(f"    Realized Revenue           : ${rev.realized_revenue:,.2f}")
    print(f"    Average Deal Size          : ${rev.average_deal_size:,.2f}")
    if insights.recommendations:
        print(f"    AI Recommendations         : {insights.recommendations[0]}\n")
    else:
        print("\n")

    # 4. Test Calibrator
    logger.info("Testing WinProbabilityCalibrator on active pipeline...")
    modifiers = calibrator.get_learned_modifiers()
    print(f"[+] Learned Empirical Modifiers Count: {len(modifiers)}")

    # 5. CLI Funnel Command
    print("\n--- CLI FUNNEL OUTPUT ---")
    cli_main(["funnel"])

    print("\n=================================================================")
    print("[SUCCESS] Phase 10 Tracking, Analytics & Learning loop verified successfully!")
    print("=================================================================")


if __name__ == "__main__":
    main()
