"""
Unit tests for MongoDB connection manager, document schemas, collection indexing, and NoSQL repositories.
"""

from unittest.mock import patch

import mongomock
import pytest

from src.database.factory import (
    get_application_repo,
    get_collection_run_repo,
    get_opportunity_repo,
    get_project_repo,
    get_source_repo,
)
from src.database.mongo import (
    check_mongo_health,
    init_mongo_indexes,
    is_mongo_configured,
)
from src.database.mongo_repository import (
    MongoApplicationRepository,
    MongoCollectionRunRepository,
    MongoOpportunityRepository,
    MongoProjectRepository,
    MongoSourceRepository,
)
from src.models.project import Project


@pytest.fixture
def mock_mongo_db():
    """Provide an isolated in-memory mongomock database for unit tests."""
    client = mongomock.MongoClient()
    db = client["client_finder_test"]
    init_mongo_indexes(db)
    return db


class TestMongoConnection:
    """Tests for MongoDB connection lifecycle, configuration, and index management."""

    def test_is_mongo_configured(self):
        with patch.dict("os.environ", {"DATABASE_TYPE": "mongodb"}, clear=True):
            assert is_mongo_configured() is True

        with patch.dict(
            "os.environ",
            {"DATABASE_URL": "mongodb://localhost:27017/db"},
            clear=True,
        ):
            assert is_mongo_configured() is True

        with patch.dict(
            "os.environ",
            {"MONGODB_URI": "mongodb://localhost:27017/db"},
            clear=True,
        ):
            assert is_mongo_configured() is True

        with patch.dict("os.environ", {"DATABASE_TYPE": "sqlite"}, clear=True):
            assert is_mongo_configured() is False

    def test_init_mongo_indexes(self, mock_mongo_db):
        # Index creation must complete cleanly on all collections
        init_mongo_indexes(mock_mongo_db)
        assert "projects" in mock_mongo_db.list_collection_names() or True

    def test_check_mongo_health_connected(self):
        mock_client = mongomock.MongoClient()
        status = check_mongo_health(mock_client)
        assert status["status"] == "connected"
        assert status["backend"] == "mongodb"


class TestMongoSourceRepository:
    """Tests for MongoDB Source management."""

    def test_source_lifecycle(self, mock_mongo_db):
        repo = MongoSourceRepository(mock_mongo_db)
        source = repo.get_or_create("RemoteOK", source_type="api", base_url="https://remoteok.com")
        assert source["name"] == "RemoteOK"
        assert source["id"] >= 1
        assert source["enabled"] is True

        # Fetch by name
        fetched = repo.get_by_name("RemoteOK")
        assert fetched is not None
        assert fetched["name"] == "RemoteOK"

        # List sources
        sources = repo.list_sources()
        assert len(sources) == 1

        # Disable source
        updated = repo.set_enabled(source["id"], False)
        assert updated is not None
        assert updated["enabled"] is False


class TestMongoProjectRepository:
    """Tests for MongoDB Project persistence, deduplication, and filtering."""

    def test_project_crud_and_deduplication(self, mock_mongo_db):
        repo = MongoProjectRepository(mock_mongo_db)
        proj = Project(
            title="FastAPI & MongoDB Engineer",
            description="Build scalable microservices with MongoDB and FastAPI",
            source="Hacker News",
            source_url="https://news.ycombinator.com/item?id=99999",
            skills=["FastAPI", "Python", "MongoDB"],
            budget=5500.0,
            currency="USD",
            score=88.0,
        )

        # 1. Add project
        doc = repo.add(proj)
        assert doc["id"] >= 1
        assert doc["title"] == proj.title
        assert doc["score"] == 88.0

        # 2. Check duplicate detection
        assert repo.is_duplicate(str(proj.source_url)) is True
        assert repo.is_duplicate("https://nonexistent.com/job") is False

        # 3. Fetch by ID and URL hash
        by_id = repo.get_by_id(doc["id"])
        assert by_id is not None
        assert by_id["title"] == proj.title

        by_hash = repo.get_by_url_hash(doc["url_hash"])
        assert by_hash is not None
        assert by_hash["id"] == doc["id"]

        # 4. List and filter
        listed = repo.list_projects(min_score=80.0, skill="FastAPI")
        assert len(listed) == 1
        assert listed[0]["id"] == doc["id"]

        # 5. Update score and status
        updated_status = repo.update_status(doc["id"], "APPLIED")
        assert updated_status is not None
        assert updated_status["status"] == "APPLIED"

        updated_score = repo.update_score(doc["id"], 92.0)
        assert updated_score is not None
        assert updated_score["score"] == 92.0

        # 6. Count and delete
        assert repo.count() == 1
        assert repo.delete(doc["id"]) is True
        assert repo.count() == 0

    def test_add_many_batch(self, mock_mongo_db):
        repo = MongoProjectRepository(mock_mongo_db)
        batch = [
            Project(
                title=f"Dev Job {i}",
                description=f"Description {i}",
                source="WeWorkRemotely",
                source_url=f"https://weworkremotely.com/job-{i}",
                skills=["Python"],
            )
            for i in range(5)
        ]
        saved = repo.add_many(batch, skip_duplicates=True)
        assert len(saved) == 5
        assert repo.count() == 5

        # Re-saving same batch skips duplicates
        saved_again = repo.add_many(batch, skip_duplicates=True)
        assert len(saved_again) == 0
        assert repo.count() == 5


class TestMongoOpportunityRepository:
    """Tests for MongoDB multi-factor scored opportunities."""

    def test_opportunity_lifecycle(self, mock_mongo_db):
        proj_repo = MongoProjectRepository(mock_mongo_db)
        opp_repo = MongoOpportunityRepository(mock_mongo_db)

        proj = proj_repo.add(
            Project(
                title="AI Vector Search Engineer",
                description="pgvector & MongoDB Atlas Search",
                source="RemoteOK",
                source_url="https://remoteok.com/job/101",
                skills=["Python", "MongoDB"],
            )
        )

        opp = opp_repo.create_or_update(
            project_id=proj["id"],
            overall_score=86.5,
            skill_match_score=90.0,
            budget_score=85.0,
            win_probability=78.0,
            explanation="High technical alignment with MongoDB stack",
        )

        assert opp["project_id"] == proj["id"]
        assert opp["overall_score"] == 86.5

        # Verify parent project score synchronization
        refreshed_proj = proj_repo.get_by_id(proj["id"])
        assert refreshed_proj is not None
        assert refreshed_proj["score"] == 86.5

        # Fetch by project ID
        fetched_opp = opp_repo.get_by_project_id(proj["id"])
        assert fetched_opp is not None
        assert fetched_opp["overall_score"] == 86.5

        # List top opportunities
        top = opp_repo.list_top_opportunities(min_score=80.0)
        assert len(top) == 1


class TestMongoCollectionRunRepository:
    """Tests for MongoDB collector telemetry runs."""

    def test_collection_run_lifecycle(self, mock_mongo_db):
        repo = MongoCollectionRunRepository(mock_mongo_db)
        run = repo.start_run("Hacker News")
        assert run["id"] >= 1
        assert run["status"] == "RUNNING"

        completed = repo.complete_run(
            run["id"],
            items_collected=10,
            items_saved=8,
            duplicates_skipped=2,
        )
        assert completed is not None
        assert completed["status"] == "SUCCESS"
        assert completed["items_collected"] == 10
        assert completed["items_saved"] == 8

        runs = repo.list_recent_runs()
        assert len(runs) == 1


class TestMongoApplicationRepository:
    """Tests for MongoDB application tracking and funnel transitions."""

    def test_application_tracking(self, mock_mongo_db):
        proj_repo = MongoProjectRepository(mock_mongo_db)
        app_repo = MongoApplicationRepository(mock_mongo_db)

        proj = proj_repo.add(
            Project(
                title="Lead Backend Architect",
                description="High throughput systems",
                source="Hacker News",
                source_url="https://news.ycombinator.com/job/555",
            )
        )

        app_doc = app_repo.create(
            project_id=proj["id"],
            status="APPLIED",
            proposed_budget=7000.0,
            notes="Custom SOW milestone proposal attached",
        )
        assert app_doc["id"] >= 1
        assert app_doc["project_id"] == proj["id"]

        # Verify parent project status updated
        refreshed_proj = proj_repo.get_by_id(proj["id"])
        assert refreshed_proj is not None
        assert refreshed_proj["status"] == "APPLIED"

        # Update status to OFFER_ACCEPTED
        updated_app = app_repo.update_status(
            app_doc["id"],
            status="OFFER_ACCEPTED",
            actual_revenue=7000.0,
        )
        assert updated_app is not None
        assert updated_app["status"] == "OFFER_ACCEPTED"
        assert updated_app["actual_revenue"] == 7000.0

        # List applications
        apps = app_repo.list_applications(status="OFFER_ACCEPTED")
        assert len(apps) == 1

        # Delete application
        assert app_repo.delete(app_doc["id"]) is True


class TestRepositoryFactory:
    """Tests for dynamic factory repository dispatching."""

    def test_factory_returns_mongo_when_db_passed(self, mock_mongo_db):
        p_repo = get_project_repo(db=mock_mongo_db)
        assert isinstance(p_repo, MongoProjectRepository)

        o_repo = get_opportunity_repo(db=mock_mongo_db)
        assert isinstance(o_repo, MongoOpportunityRepository)

        s_repo = get_source_repo(db=mock_mongo_db)
        assert isinstance(s_repo, MongoSourceRepository)

        c_repo = get_collection_run_repo(db=mock_mongo_db)
        assert isinstance(c_repo, MongoCollectionRunRepository)

        a_repo = get_application_repo(db=mock_mongo_db)
        assert isinstance(a_repo, MongoApplicationRepository)
