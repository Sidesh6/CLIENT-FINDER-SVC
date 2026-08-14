"""
Live demonstration and verification script for Phase 8: REST API & Web Dashboard Service.
Exercises all REST endpoints, triggers live collection, fetches statistics,
generates dynamic proposals, and verifies dashboard assets.
"""

import logging
import sys

from fastapi.testclient import TestClient

from src.api.main import app

if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger("APILiveTest")


def main():
    print("=================================================================")
    print("[*] CLIENT FINDER SVC - Phase 8: REST API & Dashboard Live Test")
    print("=================================================================\n")

    client = TestClient(app)

    # 1. Test Health Endpoint
    logger.info("Checking API Health (/health)...")
    res = client.get("/health")
    print(f"[+] Health Status: {res.status_code} -> {res.json()}\n")
    assert res.status_code == 200

    # 2. Test Developer Profile Endpoint
    logger.info("Fetching Active Profile (/api/profile)...")
    res = client.get("/api/profile")
    profile = res.json()
    print(f"[+] Active Profile: {profile['name']} ({profile['title']})")
    print(
        f"    Target Rate: ${profile['target_hourly_rate']}/hr | Min Rate: ${profile['minimum_hourly_rate']}/hr\n"
    )

    # 3. Trigger Collector Harvest Pipeline
    logger.info("Triggering Live Collector Pipeline via API (/api/collectors/trigger)...")
    res = client.post("/api/collectors/trigger?limit=3")
    harvest_data = res.json()
    print(f"[+] Harvest Result: {harvest_data['message']}")
    print(
        f"    Collected: {harvest_data['collected_count']} | Enriched: {harvest_data['enriched_count']} | Scored: {harvest_data['scored_count']}\n"
    )

    # 4. Fetch Opportunity KPI Statistics
    logger.info("Fetching Opportunity Statistics (/api/opportunities/stats)...")
    res = client.get("/api/opportunities/stats")
    stats = res.json()
    print(f"[+] Total Projects in Database : {stats['total_projects']}")
    print(f"    High Priority Leads (≥75) : {stats['high_priority_count']}")
    print(f"    Medium Priority Leads (50-74): {stats['medium_priority_count']}")
    print(f"    Average Match Score        : {stats['average_score']}/100")
    print(f"    Top Discovered Skills      : {[s['skill'] for s in stats['top_skills'][:5]]}\n")

    # 5. Fetch Top Opportunities
    logger.info("Fetching Top Ranked Opportunities (/api/opportunities/top)...")
    res = client.get("/api/opportunities/top?limit=3")
    top_opps = res.json()

    if top_opps:
        target = top_opps[0]
        print(f"[+] Top Opportunity: '{target['title']}' (Score: {target['score']}/100)")
        print(f"    Skills: {', '.join(target['skills'])}")
        print(f"    Source URL: {target['source_url']}\n")

        # 6. Generate AI Proposal via API
        logger.info("Generating Multi-Angle Proposal via API (/api/proposals/generate)...")
        proposal_payload = {
            "project_id": target["id"],
            "pitch_angle": "TECHNICAL_EXPERT",
            "tone": "CONFIDENT",
            "include_pricing": True,
        }
        res = client.post("/api/proposals/generate", json=proposal_payload)
        proposal = res.json()

        print("=" * 70)
        print(f"GENERATED PROPOSAL VIA API (Quality Score: {proposal['quality_score']}/100)")
        print(f"Subject: {proposal['subject_line']}")
        print("=" * 70)
        print(proposal["full_proposal_text"])
        print("=" * 70 + "\n")

    # 7. Verify Dashboard Static Asset Serving
    logger.info("Verifying Web Dashboard Single-Page Interface (/)...")
    res = client.get("/")
    assert res.status_code == 200
    print(
        f"[+] Root Dashboard Served: HTTP {res.status_code} ({len(res.text)} bytes HTML/CSS/JS payload)"
    )

    print("\n=================================================================")
    print("[SUCCESS] Phase 8 REST API & Web Dashboard verified successfully!")
    print("=================================================================")


if __name__ == "__main__":
    main()
