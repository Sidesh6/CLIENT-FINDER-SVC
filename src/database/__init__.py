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
    "get_engine",
    "get_session_factory",
    "get_db_session",
    "init_db",
    "drop_db",
    "get_db_url",
    "DEFAULT_DB_URL",
    "DEFAULT_SQLITE_PATH",
]
