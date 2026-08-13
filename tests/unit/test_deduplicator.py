from src.models.project import Project
from src.processors.deduplicator import (
    ProjectDeduplicator,
    compute_content_hash,
    compute_url_hash,
    normalize_content,
    normalize_url,
)


def test_normalize_url_strips_tracking_and_normalizes():
    url1 = "HTTPS://NEWS.YCOMBINATOR.COM/item?id=12345&utm_source=twitter&utm_medium=social/"
    url2 = "https://news.ycombinator.com/item?id=12345"

    assert normalize_url(url1) == normalize_url(url2)
    assert compute_url_hash(url1) == compute_url_hash(url2)


def test_normalize_content_normalizes_whitespace_and_case():
    title1 = "  Senior Python Developer  "
    desc1 = "Looking for an experienced   FastAPI engineer!  "

    title2 = "senior python developer"
    desc2 = "looking for an experienced fastapi engineer"

    assert normalize_content(title1, desc1) == normalize_content(title2, desc2)
    assert compute_content_hash(title1, desc1) == compute_content_hash(title2, desc2)


def test_deduplicator_identifies_duplicate_dict():
    dedup = ProjectDeduplicator()

    proj1 = {
        "title": "AI Project",
        "description": "Build an AI tool",
        "source": "Hacker News",
        "source_url": "https://news.ycombinator.com/item?id=1",
    }
    proj2 = {
        "title": "AI Project",
        "description": "Build an AI tool",
        "source": "Hacker News",
        "source_url": "https://news.ycombinator.com/item?id=1",
    }

    assert not dedup.is_duplicate(proj1)
    dedup.mark_seen(proj1)
    assert dedup.is_duplicate(proj2)


def test_deduplicator_identifies_duplicate_project_model():
    dedup = ProjectDeduplicator()

    proj1 = Project(
        title="AI Project",
        description="Build an AI tool",
        source="Hacker News",
        source_url="https://news.ycombinator.com/item?id=1",
    )
    proj2 = Project(
        title="AI Project",
        description="Build an AI tool",
        source="Hacker News",
        source_url="https://news.ycombinator.com/item?id=1",
    )

    assert not dedup.is_duplicate(proj1)
    dedup.mark_seen(proj1)
    assert dedup.is_duplicate(proj2)


def test_deduplicate_batch():
    dedup = ProjectDeduplicator()

    batch = [
        {
            "title": "Project 1",
            "description": "Desc 1",
            "source_url": "https://example.com/1",
        },
        {
            "title": "Project 1",
            "description": "Desc 1",
            "source_url": "https://example.com/1?utm_source=email",
        },
        {
            "title": "Project 2",
            "description": "Desc 2",
            "source_url": "https://example.com/2",
        },
    ]

    unique, duplicate_count = dedup.deduplicate_batch(batch)
    assert len(unique) == 2
    assert duplicate_count == 1
    assert unique[0]["title"] == "Project 1"
    assert unique[1]["title"] == "Project 2"


def test_deduplicate_against_existing_hashes():
    dedup = ProjectDeduplicator()
    existing_url = "https://example.com/existing"
    existing_url_hash = compute_url_hash(existing_url)

    batch = [
        {
            "title": "New Project",
            "description": "Desc",
            "source_url": "https://example.com/new",
        },
        {
            "title": "Old Project",
            "description": "Desc",
            "source_url": existing_url,
        },
    ]

    unique, dup_count = dedup.deduplicate_batch(batch, existing_url_hashes={existing_url_hash})
    assert len(unique) == 1
    assert dup_count == 1
    assert unique[0]["title"] == "New Project"
