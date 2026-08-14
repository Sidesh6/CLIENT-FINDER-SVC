"""
MongoDB connection manager, client lifecycle, and collection indexing.
Supports standalone MongoDB instances and replica sets with automated index provisioning.
"""

import logging
import os
from typing import Any

from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.database import Database
from pymongo.errors import PyMongoError

logger = logging.getLogger("MongoDBManager")

DEFAULT_MONGO_URI = os.getenv(
    "MONGODB_URI",
    os.getenv(
        "DATABASE_URL",
        "mongodb://CLIENT_FINDER:YOUR_PASSWORD@127.0.0.1:27017/?authSource=admin",
    ),
)
DEFAULT_MONGO_DB_NAME = os.getenv("MONGODB_DATABASE", "client_finder")

_MONGO_CLIENT_INSTANCE: MongoClient[Any] | None = None


def is_mongo_configured() -> bool:
    """
    Check if the environment is configured to use MongoDB backend.
    """
    db_type = os.getenv("DATABASE_TYPE", "").lower()
    if db_type == "mongodb":
        return True
    db_url = os.getenv("DATABASE_URL", "")
    if db_url.startswith(("mongodb://", "mongodb+srv://")):
        return True
    return bool(os.getenv("MONGODB_URI"))


def get_mongo_client(
    uri: str | None = None,
    timeout_ms: int = 4000,
    force_new: bool = False,
) -> MongoClient[Any]:
    """
    Retrieve or initialize the PyMongo MongoClient singleton.
    """
    global _MONGO_CLIENT_INSTANCE
    if _MONGO_CLIENT_INSTANCE is not None and not force_new:
        return _MONGO_CLIENT_INSTANCE

    target_uri = uri or DEFAULT_MONGO_URI
    client: MongoClient[Any] = MongoClient(
        target_uri,
        serverSelectionTimeoutMS=timeout_ms,
        connectTimeoutMS=timeout_ms,
        socketTimeoutMS=timeout_ms,
        uuidRepresentation="standard",
    )
    if not force_new:
        _MONGO_CLIENT_INSTANCE = client
    return client


def get_mongo_db(
    db_name: str | None = None,
    client: MongoClient[Any] | None = None,
) -> Database[Any]:
    """
    Retrieve MongoDB Database handle.
    """
    target_client = client or get_mongo_client()
    name = db_name or DEFAULT_MONGO_DB_NAME
    return target_client[name]


def init_mongo_indexes(db: Database[Any] | None = None) -> None:
    """
    Initialize indexes across all MongoDB collections for fast querying and deduplication.
    """
    target_db = db or get_mongo_db()
    logger.info("Initializing MongoDB indexes on database: %s", target_db.name)

    # 1. Projects Collection
    projects_coll = target_db["projects"]
    projects_coll.create_index([("url_hash", ASCENDING)], unique=True, sparse=True)
    projects_coll.create_index([("content_hash", ASCENDING)], unique=True, sparse=True)
    projects_coll.create_index([("status", ASCENDING)])
    projects_coll.create_index([("score", DESCENDING)])
    projects_coll.create_index([("source", ASCENDING)])
    projects_coll.create_index([("created_at", DESCENDING)])

    # 2. Opportunities Collection
    opps_coll = target_db["opportunities"]
    opps_coll.create_index([("project_id", ASCENDING)], unique=True)
    opps_coll.create_index([("overall_score", DESCENDING)])
    opps_coll.create_index([("tier", ASCENDING)])

    # 3. Sources Collection
    sources_coll = target_db["sources"]
    sources_coll.create_index([("name", ASCENDING)], unique=True)
    sources_coll.create_index([("is_active", ASCENDING)])

    # 4. Applications Collection
    apps_coll = target_db["applications"]
    apps_coll.create_index([("project_id", ASCENDING)])
    apps_coll.create_index([("status", ASCENDING)])
    apps_coll.create_index([("applied_at", DESCENDING)])

    logger.info("MongoDB indexes verified successfully.")


def check_mongo_health(client: MongoClient[Any] | None = None) -> dict[str, Any]:
    """
    Ping MongoDB server and report connectivity status.
    """
    target_client = client or get_mongo_client()
    try:
        target_client.admin.command("ping")
        return {
            "status": "connected",
            "backend": "mongodb",
            "database": DEFAULT_MONGO_DB_NAME,
        }
    except PyMongoError as err:
        logger.warning("MongoDB ping failed: %s", err)
        return {
            "status": "disconnected",
            "backend": "mongodb",
            "error": str(err),
        }
