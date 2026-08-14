"""
Unit tests for SourceRepository, ProjectRepository, and OpportunityRepository.
"""

import pytest
from pydantic import HttpUrl
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.database.models import Base
from src.database.repository import (
    OpportunityRepository,
    ProjectRepository,
    SourceRepository,
)
from src.models.project import Project


@pytest.fixture
def session() -> Session:
    """Create isolated SQLite database session for each test."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    db_session = session_factory()
    yield db_session
    db_session.close()
    Base.metadata.drop_all(bind=engine)


class TestSourceRepository:
    """Tests for SourceRepository."""

    def test_get_or_create_new_and_existing(self, session: Session):
        repo = SourceRepository()

        # First call creates
        src1 = repo.get_or_create(
            name="Hacker News",
            source_type="api",
            session=session,
            base_url="https://hn.algolia.com",
        )
        session.commit()
        assert src1.id is not None
        assert src1.name == "Hacker News"

        # Second call returns existing
        src2 = repo.get_or_create(
            name="Hacker News",
            source_type="api",
            session=session,
        )
        assert src2.id == src1.id

    def test_list_sources_and_enable_toggle(self, session: Session):
        repo = SourceRepository()
        repo.get_or_create("Source 1", "api", session)
        src2 = repo.get_or_create("Source 2", "web", session)
        session.commit()

        sources = repo.list_sources(session)
        assert len(sources) == 2

        # Disable source 2
        repo.set_enabled(src2.id, enabled=False, session=session)
        session.commit()

        active = repo.list_sources(session, enabled_only=True)
        assert len(active) == 1
        assert active[0].name == "Source 1"


class TestProjectRepository:
    """Tests for ProjectRepository."""

    def test_add_from_pydantic_model(self, session: Session):
        repo = ProjectRepository()
        pydantic_proj = Project(
            title="Senior Python Backend Engineer",
            description="Build event-driven microservices with Kafka and FastAPI.",
            source="Hacker News",
            source_url=HttpUrl("https://news.ycombinator.com/item?id=12345"),
            client_name="Tech Co",
            budget=8000.0,
            currency="USD",
            skills=["Python", "Kafka", "FastAPI"],
        )

        model = repo.add(pydantic_proj, session=session, external_id="12345")
        session.commit()

        assert model.id is not None
        assert model.title == "Senior Python Backend Engineer"
        assert model.external_id == "12345"
        assert model.content_hash is not None

    def test_add_from_dict(self, session: Session):
        repo = ProjectRepository()
        data = {
            "title": "Full Stack Dev",
            "description": "Next.js + Python API",
            "source": "RemoteOK",
            "source_url": "https://remoteok.com/job/777",
            "skills": ["Next.js", "Python"],
            "budget": 4500.0,
        }

        model = repo.add(data, session=session)
        session.commit()

        assert model.id is not None
        assert model.source_name == "RemoteOK"
        assert model.skills == ["Next.js", "Python"]

    def test_is_duplicate_detection(self, session: Session):
        repo = ProjectRepository()
        pydantic_proj = Project(
            title="Duplicate Test",
            description="Testing duplication detection.",
            source="HN",
            source_url=HttpUrl("https://example.com/duplicate/1"),
        )
        repo.add(pydantic_proj, session=session)
        session.commit()

        # Same URL
        assert repo.is_duplicate("https://example.com/duplicate/1/", session=session) is True

        # Different URL
        assert repo.is_duplicate("https://example.com/other-url", session=session) is False

    def test_add_many_with_duplicate_skipping(self, session: Session):
        repo = ProjectRepository()
        p1 = Project(
            title="Project Alpha",
            description="Alpha description",
            source="SourceA",
            source_url=HttpUrl("https://example.com/alpha"),
        )
        p2 = Project(
            title="Project Beta",
            description="Beta description",
            source="SourceA",
            source_url=HttpUrl("https://example.com/beta"),
        )
        # Duplicate of Alpha (same URL)
        p3 = Project(
            title="Project Alpha Repost",
            description="Alpha description",
            source="SourceA",
            source_url=HttpUrl("https://example.com/alpha"),
        )

        persisted = repo.add_many([p1, p2, p3], session=session, skip_duplicates=True)
        session.commit()

        # Should only persist 2 unique projects
        assert len(persisted) == 2
        assert repo.count(session) == 2

    def test_list_projects_and_filtering(self, session: Session):
        repo = ProjectRepository()
        repo.add(
            {
                "title": "A",
                "description": "desc A",
                "source": "HN",
                "source_url": "https://a.com",
                "score": 90.0,
                "status": "QUALIFIED",
            },
            session=session,
        )
        repo.add(
            {
                "title": "B",
                "description": "desc B",
                "source": "HN",
                "source_url": "https://b.com",
                "score": 60.0,
                "status": "DISCOVERED",
            },
            session=session,
        )
        repo.add(
            {
                "title": "C",
                "description": "desc C",
                "source": "Upwork",
                "source_url": "https://c.com",
                "score": 85.0,
                "status": "DISCOVERED",
            },
            session=session,
        )
        session.commit()

        # Filter by status
        qualified = repo.list_projects(session, status="QUALIFIED")
        assert len(qualified) == 1
        assert qualified[0].title == "A"

        # Filter by source
        upwork_jobs = repo.list_projects(session, source_name="Upwork")
        assert len(upwork_jobs) == 1
        assert upwork_jobs[0].title == "C"

        # Filter by minimum score and order
        top = repo.list_projects(session, min_score=80.0, order_by_score=True)
        assert len(top) == 2
        assert top[0].score == 90.0
        assert top[1].score == 85.0

    def test_update_status_and_score(self, session: Session):
        repo = ProjectRepository()
        model = repo.add(
            {
                "title": "Status Test",
                "description": "desc",
                "source": "HN",
                "source_url": "https://test-status.com",
            },
            session=session,
        )
        session.commit()

        repo.update_status(model.id, "APPLIED", session=session)
        repo.update_score(model.id, 95.0, session=session)
        session.commit()

        updated = repo.get_by_id(model.id, session=session)
        assert updated.status == "APPLIED"
        assert updated.score == 95.0

    def test_delete_project(self, session: Session):
        repo = ProjectRepository()
        model = repo.add(
            {
                "title": "To Delete",
                "description": "desc",
                "source": "HN",
                "source_url": "https://delete-me.com",
            },
            session=session,
        )
        session.commit()

        assert repo.delete(model.id, session=session) is True
        session.commit()
        assert repo.get_by_id(model.id, session=session) is None


class TestOpportunityRepository:
    """Tests for OpportunityRepository."""

    def test_create_or_update_opportunity(self, session: Session):
        proj_repo = ProjectRepository()
        opp_repo = OpportunityRepository()

        proj = proj_repo.add(
            {
                "title": "AI Opportunity",
                "description": "Agentic system design",
                "source": "HN",
                "source_url": "https://opp-test.com",
            },
            session=session,
        )
        session.commit()

        # Create opportunity score
        opp = opp_repo.create_or_update(
            project_id=proj.id,
            overall_score=91.5,
            skill_match_score=95.0,
            budget_score=88.0,
            client_score=90.0,
            explanation="High-budget AI project matching user skillset.",
            session=session,
        )
        session.commit()

        assert opp.id is not None
        assert opp.overall_score == 91.5

        # Check that parent project score was also synchronized
        updated_proj = proj_repo.get_by_id(proj.id, session=session)
        assert updated_proj.score == 91.5

        # Update existing opportunity
        updated_opp = opp_repo.create_or_update(
            project_id=proj.id,
            overall_score=94.0,
            session=session,
        )
        session.commit()
        assert updated_opp.id == opp.id
        assert updated_opp.overall_score == 94.0
