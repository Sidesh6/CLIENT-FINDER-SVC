"""
Unit tests for Multi-Source Collectors (RemoteOK, WeWorkRemotely, RSS/Atom),
CollectorRegistry health and circuit-breaker management, and Portfolio Case-Study RAG.
"""

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from src.api.main import app
from src.collectors.registry import CollectorRegistry
from src.collectors.remoteok_collector import RemoteOKCollector
from src.collectors.rss_collector import RSSFeedCollector
from src.collectors.weworkremotely_collector import WeWorkRemotelyCollector
from src.models.profile import get_default_profile
from src.models.project import Project
from src.proposal.heuristic import HeuristicProposalGenerator
from src.proposal.schemas import PitchAngle
from src.utils.http_client import HttpClient, HttpClientError

client = TestClient(app)


class TestRemoteOKCollector:
    """Tests for RemoteOK JSON API collector."""

    def test_remoteok_collector_parses_job_entries(self):
        mock_http = MagicMock(spec=HttpClient)
        mock_http.get_json.return_value = [
            {"legal": "Disclaimer object"},
            {
                "id": "12345",
                "position": "Senior Python & FastAPI Engineer",
                "company": "Acme AI",
                "description": "<p>We are building <strong>FastAPI</strong> microservices and LangChain RAG pipelines.</p>",
                "url": "https://remoteok.com/remote-jobs/12345",
                "tags": ["python", "fastapi", "ai", "contract"],
                "salary_min": 100000,
                "salary_max": 140000,
                "location": "Worldwide",
                "date": "2026-08-14T10:00:00Z",
            },
        ]

        collector = RemoteOKCollector(http_client=mock_http, max_projects=10)
        projects = collector.collect()

        assert len(projects) == 1
        p = projects[0]
        assert "Senior Python & FastAPI Engineer" in p["title"]
        assert p["client_name"] == "Acme AI"
        assert p["source"] == "RemoteOK"
        assert "FastAPI" in p["description"]
        assert "<p>" not in p["description"]
        assert "fastapi" in [t.lower() for t in p["skills"]]
        assert p["budget"] == 140000.0
        assert p["project_type"] == "Contract"

    def test_remoteok_collector_tag_filtering(self):
        mock_http = MagicMock(spec=HttpClient)
        mock_http.get_json.return_value = [
            {"position": "React Frontend Dev", "tags": ["react", "frontend"], "id": "1"},
            {"position": "AI Engineer", "tags": ["python", "llm"], "id": "2"},
        ]

        collector = RemoteOKCollector(http_client=mock_http, tag_filters=["llm"])
        projects = collector.collect()

        assert len(projects) == 1
        assert "AI Engineer" in projects[0]["title"]

    def test_remoteok_collector_handles_http_error(self):
        mock_http = MagicMock(spec=HttpClient)
        mock_http.get_json.side_effect = HttpClientError("Network timeout")

        collector = RemoteOKCollector(http_client=mock_http)
        projects = collector.collect()

        assert projects == []


class TestWeWorkRemotelyCollector:
    """Tests for WeWorkRemotely RSS feed collector."""

    SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
      <channel>
        <title>We Work Remotely - Programming</title>
        <item>
          <title>TechCorp: Lead Python Developer</title>
          <link>https://weworkremotely.com/jobs/123-lead-python-developer</link>
          <description>&lt;p&gt;Looking for an experienced &lt;strong&gt;Python/FastAPI&lt;/strong&gt; architect.&lt;/p&gt;</description>
          <guid>https://weworkremotely.com/jobs/123</guid>
          <pubDate>Fri, 14 Aug 2026 12:00:00 +0000</pubDate>
        </item>
      </channel>
    </rss>
    """

    def test_weworkremotely_parses_rss_feed(self):
        mock_http = MagicMock(spec=HttpClient)
        mock_http.get.return_value = self.SAMPLE_RSS

        collector = WeWorkRemotelyCollector(http_client=mock_http)
        projects = collector.collect()

        assert len(projects) == 1
        p = projects[0]
        assert "Lead Python Developer" in p["title"]
        assert p["client_name"] == "TechCorp"
        assert p["source"] == "WeWorkRemotely"
        assert "Python/FastAPI" in p["description"]
        assert "<p>" not in p["description"]
        assert p["posted_at"] is not None

    def test_weworkremotely_handles_empty_or_invalid_xml(self):
        mock_http = MagicMock(spec=HttpClient)
        mock_http.get.return_value = "<invalid>xml"

        collector = WeWorkRemotelyCollector(http_client=mock_http)
        projects = collector.collect()
        assert projects == []


class TestRSSFeedCollector:
    """Tests for generic RSS 2.0 & Atom feed ingestion."""

    SAMPLE_ATOM = """<?xml version="1.0" encoding="utf-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <title>Custom Tech Jobs</title>
      <entry>
        <title>Full-Stack AI Developer</title>
        <link href="https://example.com/job/456"/>
        <id>urn:uuid:456</id>
        <updated>2026-08-14T15:30:00Z</updated>
        <summary>Build LangChain and Next.js applications.</summary>
      </entry>
    </feed>
    """

    def test_rss_feed_collector_atom_parsing(self):
        mock_http = MagicMock(spec=HttpClient)
        mock_http.get.return_value = self.SAMPLE_ATOM

        collector = RSSFeedCollector(
            source_name="CustomAtomFeed",
            feed_url="https://example.com/atom.xml",
            http_client=mock_http,
        )
        projects = collector.collect()

        assert len(projects) == 1
        p = projects[0]
        assert p["title"] == "Full-Stack AI Developer"
        assert p["source"] == "CustomAtomFeed"
        assert "LangChain" in p["description"]
        assert p["source_url"] == "https://example.com/job/456"


class TestCollectorRegistryAndCircuitBreaker:
    """Tests for dynamic collector registration and circuit-breaker telemetry."""

    def test_registry_registration_and_toggle(self):
        registry = CollectorRegistry(failure_threshold=2)
        mock_col = RemoteOKCollector()

        registry.register(mock_col, enabled=True)
        assert "RemoteOK" in registry.list_sources()
        assert len(registry.get_active_collectors()) == 1

        # Toggle disable
        new_state = registry.toggle("RemoteOK", enable=False)
        assert new_state is False
        assert len(registry.get_active_collectors()) == 0

        # Toggle enable
        new_state_on = registry.toggle("RemoteOK", enable=True)
        assert new_state_on is True
        assert len(registry.get_active_collectors()) == 1

    def test_circuit_breaker_trips_after_consecutive_failures(self):
        registry = CollectorRegistry(failure_threshold=3)
        mock_col = RemoteOKCollector()
        registry.register(mock_col, enabled=True)

        registry.record_failure("RemoteOK", "Connection refused")
        registry.record_failure("RemoteOK", "503 Service Unavailable")
        state = registry.get_state("RemoteOK")
        assert state is not None
        assert state.circuit_broken is False

        # 3rd failure trips circuit
        registry.record_failure("RemoteOK", "503 Service Unavailable")
        assert state.circuit_broken is True
        assert len(registry.get_active_collectors()) == 0

        # Manual reset
        registry.reset_circuit("RemoteOK")
        assert state.circuit_broken is False
        assert len(registry.get_active_collectors()) == 1


class TestPortfolioCaseStudyRAG:
    """Tests for Portfolio Case Study model and dynamic proposal citations."""

    def test_user_profile_find_relevant_portfolio(self):
        profile = get_default_profile()
        assert len(profile.portfolio) >= 3

        # Match RAG / LangChain opportunity
        rag_matches = profile.find_relevant_portfolio(
            ["LangChain", "RAG", "FastAPI"], max_results=1
        )
        assert len(rag_matches) == 1
        assert "RAG" in rag_matches[0].title

        # Match Scraping opportunity
        scrape_matches = profile.find_relevant_portfolio(
            ["Playwright", "Web Scraping"], max_results=1
        )
        assert len(scrape_matches) == 1
        assert "Scraping" in scrape_matches[0].title

    def test_heuristic_proposal_cites_portfolio_case_studies(self):
        generator = HeuristicProposalGenerator()
        profile = get_default_profile()

        test_proj = Project(
            title="Enterprise RAG Architecture Engineer",
            description="Need expert to build knowledge base RAG microservice with LangChain and FastAPI",
            source="RemoteOK",
            source_url="https://remoteok.com/l/123",
            skills=["Python", "FastAPI", "LangChain", "RAG"],
        )

        result = generator.generate(
            project=test_proj,
            profile=profile,
            pitch_angle=PitchAngle.PORTFOLIO_PROOF,
        )

        assert result.quality_score >= 85.0
        assert len(result.relevant_projects) >= 1
        assert "RAG" in result.relevant_projects[0] or "Enterprise" in result.relevant_projects[0]


class TestCollectorApiRoutes:
    """Tests for Collector REST endpoints."""

    def test_list_collectors_and_health_routes(self):
        res = client.get("/api/collectors")
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        assert any(c["source_name"] == "Hacker News" for c in data)

        res_health = client.get("/api/collectors/health")
        assert res_health.status_code == 200
        assert len(res_health.json()) >= 1

    def test_toggle_and_reset_circuit_routes(self):
        res_toggle = client.post("/api/collectors/RemoteOK/toggle?enable=false")
        assert res_toggle.status_code == 200
        assert res_toggle.json()["enabled"] is False

        # Toggle back
        res_toggle_on = client.post("/api/collectors/RemoteOK/toggle?enable=true")
        assert res_toggle_on.status_code == 200
        assert res_toggle_on.json()["enabled"] is True

        res_reset = client.post("/api/collectors/RemoteOK/reset-circuit")
        assert res_reset.status_code == 200
        assert res_reset.json()["circuit_broken"] is False
