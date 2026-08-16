"""
Unit tests for Direct Freelance Client Acquisition Engine (Phase 27).
Tests FreelanceClientClassifier, ClientContactExtractor, UpworkRSSCollector,
and direct freelance proposal pitch generation.
"""

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from src.api.main import app
from src.collectors.upwork_rss_collector import UpworkRSSCollector
from src.intelligence.client_contact import ClientContactDetails, ClientContactExtractor
from src.models.profile import get_default_profile
from src.models.project import Project
from src.processors.freelance_classifier import (
    ClientType,
    EngagementType,
    FreelanceClientClassifier,
)
from src.proposal.heuristic import HeuristicProposalGenerator
from src.proposal.schemas import PitchAngle
from src.utils.http_client import HttpClient

client = TestClient(app)


class TestFreelanceClientClassifier:
    """Tests for direct client vs employee job classification."""

    def setup_method(self):
        self.classifier = FreelanceClientClassifier()

    def test_classifies_direct_founder_project(self):
        project = {
            "title": "Need Python / FastAPI freelance developer for MVP",
            "description": "I'm the founder of an AI startup. Looking for a freelance contractor to build our FastAPI backend and vector search pipeline. Budget: $4,500 fixed-price.",
            "source": "Client Leads",
        }
        res = self.classifier.classify(project)
        assert res.is_direct_client is True
        assert res.client_type == ClientType.DIRECT_FOUNDER
        assert res.engagement_type == EngagementType.FIXED_MILESTONE
        assert len(res.rejection_reasons) == 0

    def test_classifies_hourly_contract(self):
        project = {
            "title": "Looking for contract senior React & Python engineer",
            "description": "We are seeking an hourly contractor ($80-$120/hr) for 20 hours per week over 3 months.",
            "source": "Upwork",
            "is_direct_client": True,
        }
        res = self.classifier.classify(project)
        assert res.is_direct_client is True
        assert res.engagement_type == EngagementType.HOURLY_CONTRACT

    def test_disqualifies_w2_employee_job(self):
        project = {
            "title": "Senior Software Engineer (Full-Time W2)",
            "description": "We are seeking a permanent full-time employee. Must be W2 only. Includes 401k match, health dental vision insurance, and 20 days PTO.",
            "source": "RemoteOK",
        }
        res = self.classifier.classify(project)
        assert res.is_direct_client is False
        assert res.engagement_type == EngagementType.EMPLOYEE_JOB
        assert any("401k" in r.lower() or "w-2" in r.lower() for r in res.rejection_reasons)

    def test_disqualifies_recruiter_staffing_agency(self):
        project = {
            "title": "Python Engineer needed for Client",
            "description": "Our staffing agency is recruiting on behalf of our client for a permanent role with base salary of $140,000.",
            "source": "Jobicy",
        }
        res = self.classifier.classify(project)
        assert res.is_direct_client is False
        assert any("recruiter" in r.lower() or "staffing" in r.lower() for r in res.rejection_reasons)


class TestClientContactExtractor:
    """Tests for extracting decision-maker contact details."""

    def setup_method(self):
        self.extractor = ClientContactExtractor()

    def test_extracts_emails_and_calendly(self):
        text = """
        Building a new AI tool. Contact founder directly at alex@mystartup.io or book a chat: https://calendly.com/alex-startup/15min.
        Also reachable on Telegram @alex_builds.
        """
        details = self.extractor.extract(text, default_url="https://example.com")
        assert "alex@mystartup.io" in details.emails
        assert "https://calendly.com/alex-startup/15min" in details.calendly_links
        assert "@alex_builds" in details.telegram_handles
        assert details.primary_channel == "EMAIL"
        assert details.primary_action_url == "mailto:alex@mystartup.io"

    def test_extracts_obfuscated_email(self):
        text = "Reach me at sarah [at] venturelab [dot] com to discuss milestone quote."
        details = self.extractor.extract(text)
        assert "sarah@venturelab.com" in details.emails

    def test_fallback_to_source_url_when_no_contact_found(self):
        text = "Need an urgent script fixed today."
        details = self.extractor.extract(text, default_url="https://upwork.com/jobs/~01abc")
        assert details.primary_channel == "SOURCE_LINK"
        assert details.primary_action_url == "https://upwork.com/jobs/~01abc"


class TestUpworkRSSCollector:
    """Tests for Upwork RSS XML collector."""

    def test_upwork_rss_parsing(self):
        mock_http = MagicMock(spec=HttpClient)
        sample_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
          <channel>
            <title>Upwork Jobs</title>
            <item>
              <title>FastAPI and PostgreSQL Developer for SaaS MVP - Upwork</title>
              <link>https://www.upwork.com/jobs/~0111222333</link>
              <description>&lt;b&gt;Budget&lt;/b&gt;: $2,500&lt;br /&gt;&lt;b&gt;Skills&lt;/b&gt;: Python, FastAPI, PostgreSQL&lt;br /&gt;&lt;b&gt;Country&lt;/b&gt;: United States&lt;br /&gt;Looking for a skilled freelancer to build backend.</description>
              <guid>https://www.upwork.com/jobs/~0111222333</guid>
              <pubDate>Sun, 16 Aug 2026 10:00:00 +0000</pubDate>
            </item>
            <item>
              <title>AI Engineer for RAG Pipeline - Upwork</title>
              <link>https://www.upwork.com/jobs/~0144556677</link>
              <description>&lt;b&gt;Hourly Range&lt;/b&gt;: $60.00-$100.00&lt;br /&gt;&lt;b&gt;Skills&lt;/b&gt;: Python, LangChain, OpenAI&lt;br /&gt;&lt;b&gt;Country&lt;/b&gt;: Canada&lt;br /&gt;Need contractor to optimize RAG latency.</description>
              <guid>https://www.upwork.com/jobs/~0144556677</guid>
              <pubDate>Sun, 16 Aug 2026 11:00:00 +0000</pubDate>
            </item>
          </channel>
        </rss>"""
        mock_http.get.return_value = sample_xml

        collector = UpworkRSSCollector(http_client=mock_http, max_projects=10)
        projects = collector.collect()

        assert len(projects) == 2
        p1 = projects[0]
        assert p1["title"] == "FastAPI and PostgreSQL Developer for SaaS MVP"
        assert p1["budget"] == 2500.0
        assert "FastAPI" in p1["skills"]
        assert p1["is_direct_client"] is True

        p2 = projects[1]
        assert p2["title"] == "AI Engineer for RAG Pipeline"
        assert p2["budget"] == 100.0
        assert p2["project_type"] == "Hourly Freelance Contract"


class TestFreelanceProposalGeneration:
    """Tests for direct founder and milestone freelance proposal synthesis."""

    def setup_method(self):
        self.generator = HeuristicProposalGenerator()
        self.profile = get_default_profile()

    def test_direct_founder_pitch(self):
        project = Project(
            title="FastAPI & RAG System for Startup MVP",
            description="Need freelancer to ship our AI backend in 2 weeks.",
            skills=["Python", "FastAPI", "AI"],
            budget=3000.0,
            currency="USD",
            source="Client Leads",
            source_url="https://news.ycombinator.com/item?id=123",
        )
        res = self.generator.generate(
            project=project,
            profile=self.profile,
            pitch_angle=PitchAngle.DIRECT_FOUNDER_PITCH,
        )
        assert res.pitch_angle == PitchAngle.DIRECT_FOUNDER_PITCH
        assert "Zero Ramp-Up" in res.body or "freelance engineer" in res.hook.lower()
        assert "15-minute" in res.call_to_action.lower()

    def test_fixed_milestone_quote(self):
        project = Project(
            title="Full-Stack Web App Development",
            description="Looking for fixed milestone delivery.",
            skills=["Python", "React", "PostgreSQL"],
            budget=5000.0,
            currency="USD",
            source="Upwork",
            source_url="https://upwork.com/jobs/456",
        )

        res = self.generator.generate(
            project=project,
            profile=self.profile,
            pitch_angle=PitchAngle.FIXED_MILESTONE_QUOTE,
        )
        assert res.pitch_angle == PitchAngle.FIXED_MILESTONE_QUOTE
        assert "Milestone 1" in res.body
        assert "Milestone 2" in res.body
        assert "Milestone 3" in res.body


class TestFreelanceApiFiltering:
    """Tests for direct_client_only API query filter."""

    def test_list_projects_direct_client_filtering(self):
        res = client.get("/api/projects?direct_client_only=true&limit=10")
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data["items"], list)
        for item in data["items"]:
            assert item["is_direct_client"] is True
            assert "contact_details" in item
