from unittest.mock import MagicMock

from src.collectors.hackernews_collector import HackerNewsCollector
from src.utils.http_client import HttpClientError


def test_hackernews_collector_source_name():
    collector = HackerNewsCollector()
    assert collector.get_source_name() == "Hacker News"


def test_hackernews_strip_html():
    collector = HackerNewsCollector()
    raw = "<p>Looking for a <b>Python</b> &amp; AI dev.<br>Budget is $3,000.</p>"
    clean = collector._strip_html(raw)
    assert "<b>" not in clean
    assert "<p>" not in clean
    assert "&amp;" not in clean
    assert "Python & AI dev." in clean
    assert "Budget is $3,000." in clean


def test_hackernews_collector_custom_search(mocker):
    mock_http = MagicMock()
    mock_http.get_json.return_value = {
        "hits": [
            {
                "objectID": "12345",
                "author": "techlead_guy",
                "comment_text": "<p>SEEKING FREELANCER: Need an experienced Python / FastAPI engineer for 3 month contract.</p>",
            },
            {
                "objectID": "12346",
                "author": "startup_cto",
                "comment_text": "<p>HIRING: Looking for AI specialist to build RAG pipeline.</p>",
            },
        ]
    }

    collector = HackerNewsCollector(http_client=mock_http, search_query="SEEKING FREELANCER")
    projects = collector.collect()

    assert len(projects) == 2
    assert projects[0]["client_name"] == "techlead_guy"
    assert "Python / FastAPI" in projects[0]["description"]
    assert str(projects[0]["source_url"]) == "https://news.ycombinator.com/item?id=12345"
    assert projects[0]["source"] == "Hacker News"

    assert projects[1]["client_name"] == "startup_cto"
    assert "RAG pipeline" in projects[1]["description"]


def test_hackernews_collector_thread_discovery(mocker):
    mock_http = MagicMock()
    # First call: thread discovery search
    # Second call: story comments
    mock_http.get_json.side_effect = [
        {
            "hits": [
                {
                    "objectID": "99999",
                    "title": "Ask HN: Freelancer? Seeking Freelancer? (August 2026)",
                }
            ]
        },
        {
            "hits": [
                {
                    "objectID": "100001",
                    "author": "founder_bob",
                    "comment_text": "SEEKING FREELANCER | Remote | Looking for backend developer to build microservices.",
                },
                {
                    "objectID": "100002",
                    "author": "freelancer_alice",
                    "comment_text": "SEEKING WORK | Remote | I am a senior developer available for hire.",
                },
            ]
        },
    ]

    collector = HackerNewsCollector(http_client=mock_http)
    projects = collector.collect()

    # Only the "SEEKING FREELANCER" / hiring comment should be retained
    assert len(projects) >= 1
    assert any(p["client_name"] == "founder_bob" for p in projects)
    # The seeking work freelancer should not be included as a project opportunity
    assert not any(p["client_name"] == "freelancer_alice" for p in projects)


def test_hackernews_collector_handles_http_failure_gracefully(mocker):
    mock_http = MagicMock()
    mock_http.get_json.side_effect = HttpClientError("Network unreachable")

    collector = HackerNewsCollector(http_client=mock_http)
    projects = collector.collect()

    # Must return empty list rather than crashing
    assert isinstance(projects, list)
    assert len(projects) == 0
