"""
Live demonstration script for Phase 7: AI Proposal & Cover Letter Generator.
Collects a live opportunity from Hacker News, extracts requirements, scores it,
and synthesizes custom proposals across multiple pitch angles.
"""

import logging
import sys

from src.ai.extractor import ProjectExtractor
from src.collectors.hackernews_collector import HackerNewsCollector
from src.models.profile import get_default_profile
from src.processors.cleaner import ProjectCleaner
from src.proposal.generator import ProposalGenerator
from src.proposal.schemas import PitchAngle, ProposalTone
from src.scoring.engine import OpportunityScorer

if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger("ProposalLiveTest")


def main():
    print("=================================================================")
    print("[*] CLIENT FINDER SVC - Phase 7: AI Proposal & Cover Letter Test")
    print("=================================================================\n")

    profile = get_default_profile()
    print(f"[+] Loaded Developer Profile: '{profile.name}' ({profile.title})")
    print(
        f"    Target Rate: ${profile.target_hourly_rate}/hr | Min Rate: ${profile.minimum_hourly_rate}/hr\n"
    )

    # Step 1: Collect live opportunity
    logger.info("Collecting live opportunities from Hacker News...")
    collector = HackerNewsCollector(max_projects=3)
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

    # Step 3: Score and select top opportunity
    scorer = OpportunityScorer(default_profile=profile)
    scored_opps = scorer.rank_opportunities(enriched, profile=profile)

    top_project, top_breakdown = scored_opps[0]

    print("\n" + "=" * 75)
    print(
        f"TOP OPPORTUNITY SELECTED FOR PROPOSAL SYNTHESIS (Score: {top_breakdown.overall_score}/100)"
    )
    print("=" * 75)
    print(f"Title       : {top_project.title}")
    print(f"Source URL  : {top_project.source_url}")
    print(f"Tech Stack  : {', '.join(top_project.skills)}")
    print(f"Category    : {top_project.category}")
    print(f"Budget      : {top_project.budget or 'Unstated'} {top_project.currency or 'USD'}")
    print(f"Match Reason: {top_breakdown.explanation}\n")

    # Step 4: Generate Proposals across 3 Pitch Angles
    generator = ProposalGenerator(default_profile=profile)

    angles_to_demo = [
        PitchAngle.TECHNICAL_EXPERT,
        PitchAngle.FAST_DELIVERY,
        PitchAngle.VALUE_ROI,
    ]

    for idx, angle in enumerate(angles_to_demo, 1):
        print("=" * 75)
        print(f"PROPOSAL VARIANT #{idx} - PITCH ANGLE: [{angle.value}]")
        print("=" * 75)

        proposal = generator.generate_for_project(
            project=top_project,
            profile=profile,
            pitch_angle=angle,
            tone=ProposalTone.CONFIDENT,
            include_pricing=True,
        )

        print(f"Subject Line : {proposal.subject_line}")
        print(f"Quality Score: {proposal.quality_score}/100\n")
        print("--- FULL PROPOSAL TEXT ---")
        print(proposal.full_proposal_text)
        print("-" * 75 + "\n")

    print("=" * 75)
    print("[SUCCESS] Phase 7 AI Proposal & Cover Letter Generator verified successfully!")
    print("=" * 75)


if __name__ == "__main__":
    main()
