"""
Unit tests for Freelance Marketplace Collectors.
Tests FreelancerCollector, GuruCollector, PeoplePerHourCollector, and FiverrCollector.
"""

from unittest.mock import MagicMock

from src.collectors.fiverr_collector import FiverrCollector
from src.collectors.freelancer_collector import FreelancerCollector
from src.collectors.guru_collector import GuruCollector
from src.collectors.peopleperhour_collector import PeoplePerHourCollector
from src.collectors.registry import get_default_registry
from src.utils.http_client import HttpClient


class TestFreelancerCollector:
    """Tests for Freelancer.com XML RSS feed parsing."""

    def test_freelancer_rss_parsing(self):
        mock_http = MagicMock(spec=HttpClient)
        sample_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
          <channel>
            <title>Freelancer Projects</title>
            <item>
              <title>Build Python FastAPI Microservice for AI SaaS</title>
              <link>https://www.freelancer.com/projects/python/fastapi-saas-microservice</link>
              <description>&lt;p&gt;Looking for a freelance backend developer to build FastAPI endpoints and vector search integration.&lt;/p&gt;&lt;p&gt;Budget: $750 - $1,500 USD&lt;/p&gt;&lt;p&gt;Skills: Python, FastAPI, PostgreSQL, AI&lt;/p&gt;</description>
              <guid>https://www.freelancer.com/projects/python/fastapi-saas-microservice</guid>
              <pubDate>Mon, 17 Aug 2026 12:00:00 +0000</pubDate>
            </item>
          </channel>
        </rss>"""
        mock_http.get.return_value = sample_xml

        collector = FreelancerCollector(http_client=mock_http)
        projects = collector.collect()

        assert len(projects) == 1
        p = projects[0]
        assert p["title"] == "Build Python FastAPI Microservice for AI SaaS"
        assert p["source"] == "Freelancer"
        assert p["budget"] == 1500.0
        assert p["currency"] == "USD"
        assert "FastAPI" in p["skills"]
        assert p["is_direct_client"] is True


class TestGuruCollector:
    """Tests for Guru.com XML RSS feed parsing."""

    def test_guru_rss_parsing(self):
        mock_http = MagicMock(spec=HttpClient)
        sample_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
          <channel>
            <title>Guru Programming Jobs</title>
            <item>
              <title>Full-Stack React and Python Developer Needed</title>
              <link>https://www.guru.com/jobs/full-stack-react-python/12345</link>
              <description>&lt;p&gt;Need an experienced contractor for MVP development.&lt;/p&gt;&lt;p&gt;Budget: Fixed Price ($2,000 - $4,000)&lt;/p&gt;&lt;p&gt;Skills: Python, React, PostgreSQL&lt;/p&gt;&lt;p&gt;Location: United States&lt;/p&gt;</description>
              <guid>https://www.guru.com/jobs/full-stack-react-python/12345</guid>
              <pubDate>Mon, 17 Aug 2026 13:00:00 +0000</pubDate>
            </item>
          </channel>
        </rss>"""
        mock_http.get.return_value = sample_xml

        collector = GuruCollector(http_client=mock_http)
        projects = collector.collect()

        assert len(projects) == 1
        p = projects[0]
        assert p["title"] == "Full-Stack React and Python Developer Needed"
        assert p["source"] == "Guru"
        assert p["budget"] == 4000.0
        assert p["location"] == "United States"
        assert "React" in p["skills"]
        assert p["is_direct_client"] is True


class TestPeoplePerHourCollector:
    """Tests for PeoplePerHour XML RSS feed parsing."""

    def test_pph_rss_parsing(self):
        mock_http = MagicMock(spec=HttpClient)
        sample_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
          <channel>
            <title>PeoplePerHour Jobs</title>
            <item>
              <title>AI Automation Agent for Customer Support</title>
              <link>https://www.peopleperhour.com/freelance-jobs/technology-programming/ai-agent-support/9988</link>
              <description>&lt;p&gt;We need a freelancer to integrate OpenAI and LangChain with our CRM.&lt;/p&gt;&lt;p&gt;Budget: $850&lt;/p&gt;&lt;p&gt;Skills: Python, AI, LangChain, API Integration&lt;/p&gt;</description>
              <guid>https://www.peopleperhour.com/freelance-jobs/technology-programming/ai-agent-support/9988</guid>
              <pubDate>Mon, 17 Aug 2026 14:00:00 +0000</pubDate>
            </item>
          </channel>
        </rss>"""
        mock_http.get.return_value = sample_xml

        collector = PeoplePerHourCollector(http_client=mock_http)
        projects = collector.collect()

        assert len(projects) == 1
        p = projects[0]
        assert p["title"] == "AI Automation Agent for Customer Support"
        assert p["source"] == "PeoplePerHour"
        assert p["budget"] == 850.0
        assert p["currency"] == "USD"
        assert p["is_direct_client"] is True


class TestFiverrCollector:
    """Tests for Fiverr buyer brief parsing and ingestion."""

    def test_parse_incoming_buyer_brief(self):
        collector = FiverrCollector()
        brief_data = {
            "title": "Need custom FastAPI backend for mobile app",
            "description": "Looking for a top Python developer to build auth, database models, and payment webhook integrations. Budget: $1,200",
            "buyer_name": "techfounder_nyc",
            "budget": 1200.0,
            "currency": "USD",
            "country": "United States",
            "brief_id": "fiverr_brief_9921",
        }

        project = collector.parse_incoming_brief(brief_data)
        assert project["title"] == "Need custom FastAPI backend for mobile app"
        assert project["source"] == "Fiverr"
        assert project["budget"] == 1200.0
        assert project["client_name"] == "techfounder_nyc"
        assert "FastAPI" in project["skills"]
        assert "Python" in project["skills"]
        assert project["is_direct_client"] is True


class TestCollectorRegistryFreelanceDefaults:
    """Tests for Registry default configurations for freelance client discovery."""

    def test_default_registry_enables_freelance_marketplaces(self):
        registry = get_default_registry()
        active_names = [c.source_name for c in registry.get_active_collectors()]

        # Verify freelance client sources are enabled
        assert "Upwork" in active_names
        assert "Client Leads" in active_names
        assert "Freelancer" in active_names
        assert "Guru" in active_names
        assert "PeoplePerHour" in active_names
        assert "Fiverr" in active_names
        assert "Hacker News" in active_names

        # Verify employee job boards are disabled
        assert "RemoteOK" not in active_names
        assert "WeWorkRemotely" not in active_names
        assert "Remotive" not in active_names
        assert "Jobicy" not in active_names
        assert "Arbeitnow" not in active_names
