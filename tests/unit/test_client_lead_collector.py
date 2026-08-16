from unittest.mock import MagicMock

from src.collectors.client_lead_collector import ClientLeadCollector
from src.collectors.registry import get_default_registry


def test_client_lead_collector_keeps_client_requests_and_extracts_niches():
    http = MagicMock()
    http.get_json.return_value = {
        "hits": [
            {
                "objectID": "123",
                "author": "startup-founder",
                "created_at": "2026-08-16T08:30:00Z",
                "comment_text": (
                    "We are looking for a freelance Python/FastAPI developer to build an "
                    "AI automation workflow for our SaaS product."
                ),
            },
            {
                "objectID": "456",
                "author": "freelancer",
                "comment_text": "I am a freelance Python developer seeking work. Portfolio available.",
            },
            {
                "objectID": "789",
                "author": "employer",
                "comment_text": "Hiring an accountant for our office.",
            },
        ]
    }

    collector = ClientLeadCollector(http_client=http, queries=("python",), max_projects=5)
    leads = collector.collect()

    assert len(leads) == 1
    lead = leads[0]
    assert lead["source"] == "Client Leads"
    assert lead["project_type"] == "Freelance Client Lead"
    assert lead["client_name"] == "startup-founder"
    assert lead["source_url"] == "https://news.ycombinator.com/item?id=123"
    assert "Python / FastAPI" in lead["skills"]
    assert "AI / Automation" in lead["skills"]


def test_client_lead_collector_deduplicates_results_across_queries():
    http = MagicMock()
    hit = {
        "objectID": "123",
        "author": "client",
        "comment_text": "We need a web developer for a freelance website redesign.",
    }
    http.get_json.return_value = {"hits": [hit]}

    leads = ClientLeadCollector(http_client=http, queries=("web", "freelance")).collect()

    assert len(leads) == 1
    assert http.get_json.call_count == 2


def test_default_harvest_only_enables_client_leads():
    registry = get_default_registry()

    active_names = [collector.source_name for collector in registry.get_active_collectors()]
    assert "Client Leads" in active_names
    assert "Upwork" in active_names
    assert "Hacker News" in active_names

