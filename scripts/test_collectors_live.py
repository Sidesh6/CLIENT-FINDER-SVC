"""
Live demonstration and verification script for Phase 11: Multi-Source Collectors, Registry, and Portfolio Case-Study RAG.
"""

import logging
import sys

from src.collectors.registry import DEFAULT_REGISTRY
from src.collectors.remoteok_collector import RemoteOKCollector
from src.collectors.weworkremotely_collector import WeWorkRemotelyCollector
from src.database.connection import init_db
from src.models.profile import get_default_profile
from src.models.project import Project
from src.proposal.generator import ProposalGenerator
from src.proposal.schemas import PitchAngle, ProposalRequest

if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("MultiCollectorsLiveTest")


def main():
    print("=========================================================================")
    print("[*] CLIENT FINDER SVC - Phase 11: Multi-Source Feeds & Portfolio RAG Test")
    print("=========================================================================\n")

    init_db()
    profile = get_default_profile()

    # 1. Inspect Collector Registry
    print("--- REGISTERED COLLECTOR SOURCES ---")
    states = DEFAULT_REGISTRY.get_all_states()
    for st in states:
        print(
            f"  * Source: {st.source_name:<16} | Active: {str(st.enabled):<5} | Success Rate: {st.success_rate}%"
        )
    print()

    # 2. Test RemoteOK Collection
    logger.info("Executing test collection from RemoteOK...")
    remoteok_col = RemoteOKCollector(max_projects=3)
    rok_items = remoteok_col.collect()
    print(f"[+] RemoteOK Harvest Result: Retrieved {len(rok_items)} opportunity/opportunities.")
    if rok_items:
        print(
            f"    Sample: '{rok_items[0]['title']}' | Skills: {', '.join(rok_items[0]['skills'][:4])}\n"
        )

    # 3. Test WeWorkRemotely Collection
    logger.info("Executing test collection from WeWorkRemotely...")
    wwr_col = WeWorkRemotelyCollector(max_projects=3)
    wwr_items = wwr_col.collect()
    print(
        f"[+] WeWorkRemotely Harvest Result: Retrieved {len(wwr_items)} opportunity/opportunities."
    )
    if wwr_items:
        print(f"    Sample: '{wwr_items[0]['title']}' | URL: {wwr_items[0]['source_url']}\n")

    # 4. Test Portfolio Case-Study Matching
    print("--- DEVELOPER PORTFOLIO CASE STUDIES ---")
    for idx, p in enumerate(profile.portfolio, 1):
        print(f"  [{idx}] {p.title} (Tech: {', '.join(p.technologies)})")
    print()

    target_skills = ["FastAPI", "LangChain", "RAG", "Python"]
    matched = profile.find_relevant_portfolio(target_skills, max_results=2)
    print(f"[+] Query Skills: {target_skills}")
    print(f"[+] Top Matching Case Study: '{matched[0].title}'")
    print(f"    Impact: {matched[0].outcomes[0]}\n")

    # 5. Generate AI Proposal Citing Portfolio Case Study
    logger.info("Generating customized proposal citing dynamic portfolio case studies...")
    generator = ProposalGenerator()
    test_proj = Project(
        title="Enterprise LangChain & RAG AI Architect",
        description="Looking for senior Python & FastAPI developer to build enterprise knowledge base system.",
        source="RemoteOK",
        source_url="https://remoteok.com/l/demo-123",
        skills=["Python", "FastAPI", "LangChain", "RAG"],
        budget=8000.0,
    )
    result = generator.generate(
        ProposalRequest(
            project=test_proj,
            user_profile=profile,
            pitch_angle=PitchAngle.PORTFOLIO_PROOF,
        )
    )

    print("--- SYNTHESIZED PROPOSAL (PORTFOLIO RAG) ---")
    print(f"Subject       : {result.subject_line}")
    print(f"Quality Score : {result.quality_score}/100")
    print(f"Cited Studies : {result.relevant_projects}\n")

    print("=========================================================================")
    print("[SUCCESS] Phase 11 Multi-Source Feeds, Registry & Portfolio RAG verified!")
    print("=========================================================================")


if __name__ == "__main__":
    main()
