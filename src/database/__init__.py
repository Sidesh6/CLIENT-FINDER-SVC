"""
Database package for Client Finder service.
"""

from src.database.database import (
    DEFAULT_DB_URL,
    DEFAULT_SQLITE_PATH,
    drop_db,
    get_db_session,
    get_db_url,
    get_engine,
    get_session_factory,
    init_db,
)
from src.database.factory import (
    get_application_repo,
    get_collection_run_repo,
    get_opportunity_repo,
    get_project_repo,
    get_source_repo,
)
from src.database.models import (
    Base,
    CollectionRunRecord,
    OpportunityModel,
    ProjectModel,
    ProjectRecord,
    SourceModel,
    SourceRecord,
    compute_content_hash,
    compute_url_hash,
    normalize_url,
)
from src.database.mongo import (
    DEFAULT_MONGO_DB_NAME,
    DEFAULT_MONGO_URI,
    check_mongo_health,
    get_mongo_client,
    get_mongo_db,
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
from src.database.repository import (
    CollectionRunRepository,
    OpportunityRepository,
    ProjectRepository,
    SourceRepository,
)

__all__ = [
    "Base",
    "SourceModel",
    "ProjectModel",
    "OpportunityModel",
    "CollectionRunRecord",
    "ProjectRecord",
    "SourceRecord",
    "compute_content_hash",
    "compute_url_hash",
    "normalize_url",
    "SourceRepository",
    "ProjectRepository",
    "OpportunityRepository",
    "CollectionRunRepository",
    "MongoSourceRepository",
    "MongoProjectRepository",
    "MongoOpportunityRepository",
    "MongoCollectionRunRepository",
    "MongoApplicationRepository",
    "get_project_repo",
    "get_opportunity_repo",
    "get_source_repo",
    "get_collection_run_repo",
    "get_application_repo",
    "get_engine",
    "get_session_factory",
    "get_db_session",
    "init_db",
    "drop_db",
    "get_db_url",
    "DEFAULT_DB_URL",
    "DEFAULT_SQLITE_PATH",
    "get_mongo_client",
    "get_mongo_db",
    "init_mongo_indexes",
    "is_mongo_configured",
    "check_mongo_health",
    "DEFAULT_MONGO_URI",
    "DEFAULT_MONGO_DB_NAME",
]
