import pytest
from sqlalchemy.orm import Session

from src.database.database import get_db_session, get_engine, get_session_factory, init_db
from src.database.repository import CollectionRunRepository, ProjectRepository
from src.models.project import Project


@pytest.fixture
def db_session():
    """Create an isolated in-memory SQLite database for testing."""
    engine = get_engine("sqlite:///:memory:")
    init_db(engine)
    session_factory = get_session_factory(engine)
    with get_db_session(session_factory) as session:
        yield session


def test_save_and_retrieve_project(db_session: Session):
    repo = ProjectRepository(db_session)
    project = Project(
        title="AI Chatbot Development",
        description="Build an AI chatbot using Python, FastAPI and RAG.",
        source="Hacker News",
        source_url="https://news.ycombinator.com/item?id=12345",
        client_name="Test Client",
        budget=2500.0,
        currency="USD",
        project_type="AI Development",
        skills=["Python", "FastAPI", "RAG"],
        score=90.0,
    )

    record = repo.save_project(project)
    assert record is not None
    assert record.id is not None
    assert record.title == "AI Chatbot Development"
    assert record.skills == ["Python", "FastAPI", "RAG"]
    assert record.score == 90.0

    retrieved = repo.get_by_id(record.id)
    assert retrieved is not None
    assert retrieved.title == "AI Chatbot Development"
    assert retrieved.url_hash == record.url_hash


def test_save_project_prevents_duplicates(db_session: Session):
    repo = ProjectRepository(db_session)
    project = Project(
        title="Duplicate Project",
        description="A project description",
        source="Hacker News",
        source_url="https://news.ycombinator.com/item?id=9999",
    )

    record1 = repo.save_project(project)
    assert record1 is not None

    # Second attempt with same URL should return None
    record2 = repo.save_project(project)
    assert record2 is None


def test_save_many_projects_with_duplicate_skipping(db_session: Session):
    repo = ProjectRepository(db_session)
    projects = [
        Project(
            title="Project 1",
            description="Desc 1",
            source="Hacker News",
            source_url="https://news.ycombinator.com/item?id=101",
        ),
        Project(
            title="Project 2",
            description="Desc 2",
            source="Hacker News",
            source_url="https://news.ycombinator.com/item?id=102",
        ),
        Project(
            title="Project 1 Duplicate",
            description="Desc 1",
            source="Hacker News",
            source_url="https://news.ycombinator.com/item?id=101",
        ),
    ]

    saved, skipped = repo.save_many(projects)
    assert len(saved) == 2
    assert skipped == 1
    assert repo.count() == 2


def test_list_projects_filtering(db_session: Session):
    repo = ProjectRepository(db_session)
    repo.save_project(
        Project(
            title="HN High Score",
            description="Desc 1",
            source="Hacker News",
            source_url="https://news.ycombinator.com/item?id=201",
            score=95.0,
        )
    )
    repo.save_project(
        Project(
            title="HN Low Score",
            description="Desc 2",
            source="Hacker News",
            source_url="https://news.ycombinator.com/item?id=202",
            score=50.0,
        )
    )
    repo.save_project(
        Project(
            title="GitHub Opportunity",
            description="Desc 3",
            source="GitHub",
            source_url="https://github.com/issues/301",
            score=80.0,
        )
    )

    all_projects = repo.list_projects()
    assert len(all_projects) == 3

    hn_projects = repo.list_projects(source="Hacker News")
    assert len(hn_projects) == 2

    high_score = repo.list_projects(min_score=85.0)
    assert len(high_score) == 1
    assert high_score[0].title == "HN High Score"


def test_collection_run_logging(db_session: Session):
    run_repo = CollectionRunRepository(db_session)

    run = run_repo.start_run("Hacker News")
    assert run.id is not None
    assert run.status == "RUNNING"

    completed = run_repo.complete_run(
        run_id=run.id,
        items_collected=10,
        items_saved=8,
        duplicates_skipped=2,
        status="SUCCESS",
    )
    assert completed is not None
    assert completed.status == "SUCCESS"
    assert completed.items_saved == 8
    assert completed.duplicates_skipped == 2
    assert completed.completed_at is not None

    recent_runs = run_repo.get_recent_runs()
    assert len(recent_runs) == 1
    assert recent_runs[0].source_name == "Hacker News"
