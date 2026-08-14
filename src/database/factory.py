"""
Multi-Backend Database Repository Factory.
Dynamically yields SQL (SQLAlchemy) or NoSQL (MongoDB) repository instances
based on runtime configuration and environment settings.
"""

from typing import Any

from pymongo.database import Database
from sqlalchemy.orm import Session

from src.database.mongo import get_mongo_db, is_mongo_configured
from src.database.mongo_repository import (
    MongoApplicationRepository,
    MongoCollectionRunRepository,
    MongoOpportunityRepository,
    MongoProjectRepository,
    MongoSourceRepository,
)
from src.database.repository import (
    ApplicationRepository,
    CollectionRunRepository,
    OpportunityRepository,
    ProjectRepository,
    SourceRepository,
)


def get_project_repo(
    session: Session | None = None,
    db: Database[Any] | None = None,
) -> ProjectRepository | MongoProjectRepository:
    """
    Instantiate appropriate Project repository based on configuration.
    """
    if db is not None or is_mongo_configured():
        return MongoProjectRepository(db=db or get_mongo_db())
    return ProjectRepository(session=session)


def get_opportunity_repo(
    session: Session | None = None,
    db: Database[Any] | None = None,
) -> OpportunityRepository | MongoOpportunityRepository:
    """
    Instantiate appropriate Opportunity repository based on configuration.
    """
    if db is not None or is_mongo_configured():
        return MongoOpportunityRepository(db=db or get_mongo_db())
    return OpportunityRepository(session=session)


def get_source_repo(
    session: Session | None = None,
    db: Database[Any] | None = None,
) -> SourceRepository | MongoSourceRepository:
    """
    Instantiate appropriate Source repository based on configuration.
    """
    if db is not None or is_mongo_configured():
        return MongoSourceRepository(db=db or get_mongo_db())
    return SourceRepository(session=session)


def get_collection_run_repo(
    session: Session | None = None,
    db: Database[Any] | None = None,
) -> CollectionRunRepository | MongoCollectionRunRepository:
    """
    Instantiate appropriate CollectionRun repository based on configuration.
    """
    if db is not None or is_mongo_configured():
        return MongoCollectionRunRepository(db=db or get_mongo_db())
    return CollectionRunRepository(session=session)


def get_application_repo(
    session: Session | None = None,
    db: Database[Any] | None = None,
) -> ApplicationRepository | MongoApplicationRepository:
    """
    Instantiate appropriate Application repository based on configuration.
    """
    if db is not None or is_mongo_configured():
        return MongoApplicationRepository(db=db or get_mongo_db())
    return ApplicationRepository(session=session)
