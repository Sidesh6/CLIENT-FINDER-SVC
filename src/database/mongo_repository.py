"""
MongoDB Document Repositories for Projects, Sources, Opportunities, CollectionRuns, and Applications.
Implements high-performance NoSQL operations with automated index utilization and counter sequencing.
"""

import logging
from datetime import UTC, datetime
from typing import Any, cast

from pymongo import ASCENDING, DESCENDING, ReturnDocument
from pymongo.database import Database

from src.database.models import (
    ApplicationStatus,
    compute_content_hash,
    compute_url_hash,
    normalize_url,
)
from src.database.mongo import get_mongo_db
from src.models.project import Project

logger = logging.getLogger("MongoRepositories")


def get_next_sequence(db: Database[Any], sequence_name: str) -> int:
    """
    Generate sequential integer IDs for Mongo collections for seamless SQL API compatibility.
    """
    counter_coll = db["counters"]
    doc = counter_coll.find_one_and_update(
        {"_id": sequence_name},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return int(doc["seq"]) if doc and "seq" in doc else 1


class MongoSourceRepository:
    """
    MongoDB repository for managing project collection sources.
    """

    def __init__(self, db: Database[Any] | None = None):
        self.db = db or get_mongo_db()
        self.coll = self.db["sources"]

    def get_by_id(self, source_id: int) -> dict[str, Any] | None:
        """Fetch a source by its integer ID."""
        doc = self.coll.find_one({"id": source_id})
        if doc and "_id" in doc:
            doc.pop("_id")
        return cast(dict[str, Any] | None, doc)

    def get_by_name(self, name: str) -> dict[str, Any] | None:
        """Fetch a source by its unique name."""
        doc = self.coll.find_one({"name": name})
        if doc and "_id" in doc:
            doc.pop("_id")
        return cast(dict[str, Any] | None, doc)

    def get_or_create(
        self,
        name: str,
        source_type: str = "api",
        base_url: str | None = None,
        collection_interval: int = 3600,
    ) -> dict[str, Any]:
        """Retrieve existing source or create a new document."""
        source = self.get_by_name(name)
        if source:
            return source

        source_id = get_next_sequence(self.db, "source_id")
        now = datetime.now(UTC)
        doc = {
            "id": source_id,
            "name": name,
            "type": source_type,
            "base_url": base_url,
            "collection_interval": collection_interval,
            "enabled": True,
            "is_active": True,
            "success_count": 0,
            "failure_count": 0,
            "created_at": now,
            "updated_at": now,
        }
        self.coll.insert_one(doc)
        if "_id" in doc:
            doc.pop("_id")
        return cast(dict[str, Any], doc)

    def list_sources(self, enabled_only: bool = False) -> list[dict[str, Any]]:
        """List all configured sources."""
        query: dict[str, Any] = {}
        if enabled_only:
            query["enabled"] = True
        cursor = self.coll.find(query).sort("name", ASCENDING)
        results: list[dict[str, Any]] = []
        for doc in cursor:
            if "_id" in doc:
                doc.pop("_id")
            results.append(cast(dict[str, Any], doc))
        return results

    def set_enabled(self, source_id: int, enabled: bool) -> dict[str, Any] | None:
        """Enable or disable a specific source."""
        doc = self.coll.find_one_and_update(
            {"id": source_id},
            {"$set": {"enabled": enabled, "updated_at": datetime.now(UTC)}},
            return_document=ReturnDocument.AFTER,
        )
        if doc and "_id" in doc:
            doc.pop("_id")
        return cast(dict[str, Any] | None, doc)


class MongoProjectRepository:
    """
    MongoDB repository for managing project documents, deduplication, and querying.
    """

    def __init__(self, db: Database[Any] | None = None):
        self.db = db or get_mongo_db()
        self.coll = self.db["projects"]

    def is_duplicate(self, url: str, content_hash: str | None = None) -> bool:
        """
        Check if a project already exists by exact URL, normalized URL, or content hash.
        """
        norm_url = normalize_url(url)
        u_hash = compute_url_hash(url)

        query = {
            "$or": [
                {"source_url": url},
                {"source_url": norm_url},
                {"source_url": f"{norm_url}/"},
                {"url_hash": u_hash},
            ]
        }
        if self.coll.find_one(query, {"_id": 1}) is not None:
            return True

        if content_hash:
            if self.coll.find_one({"content_hash": content_hash}, {"_id": 1}) is not None:
                return True

        return False

    def get_by_id(self, project_id: int) -> dict[str, Any] | None:
        """Fetch project opportunity by its integer ID."""
        doc = self.coll.find_one({"id": project_id})
        if doc and "_id" in doc:
            doc.pop("_id")
        return cast(dict[str, Any] | None, doc)

    def get_by_url(self, url: str) -> dict[str, Any] | None:
        """Fetch project opportunity by exact or normalized source URL."""
        norm_url = normalize_url(url)
        u_hash = compute_url_hash(url)
        query = {
            "$or": [
                {"source_url": url},
                {"source_url": norm_url},
                {"source_url": f"{norm_url}/"},
                {"url_hash": u_hash},
            ]
        }
        doc = self.coll.find_one(query)
        if doc and "_id" in doc:
            doc.pop("_id")
        return cast(dict[str, Any] | None, doc)

    def get_by_url_hash(self, url_hash: str) -> dict[str, Any] | None:
        """Find a project by its unique URL hash."""
        doc = self.coll.find_one({"url_hash": url_hash})
        if doc and "_id" in doc:
            doc.pop("_id")
        return cast(dict[str, Any] | None, doc)

    def get_by_content_hash(self, content_hash: str) -> dict[str, Any] | None:
        """Fetch project opportunity by content hash."""
        doc = self.coll.find_one({"content_hash": content_hash})
        if doc and "_id" in doc:
            doc.pop("_id")
        return cast(dict[str, Any] | None, doc)

    def get_by_external_id(self, source_name: str, external_id: str) -> dict[str, Any] | None:
        """Fetch project opportunity by source name and external identifier."""
        doc = self.coll.find_one({"source": source_name, "external_id": external_id})
        if doc and "_id" in doc:
            doc.pop("_id")
        return cast(dict[str, Any] | None, doc)

    def get_all_url_hashes(self) -> set[str]:
        """Fetch all unique URL hashes currently in MongoDB."""
        cursor = self.coll.find({}, {"url_hash": 1})
        return {doc["url_hash"] for doc in cursor if "url_hash" in doc}

    def get_all_content_hashes(self) -> set[str]:
        """Fetch all unique content hashes currently in MongoDB."""
        cursor = self.coll.find({}, {"content_hash": 1})
        return {doc["content_hash"] for doc in cursor if "content_hash" in doc}

    def add(
        self,
        project: Project | dict[str, Any],
        source_id: int | None = None,
        external_id: str | None = None,
        raw_data: dict[str, Any] | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        """
        Persist a single project opportunity in MongoDB.
        """
        project_id = get_next_sequence(self.db, "project_id")
        now = datetime.now(UTC)

        if isinstance(project, Project):
            url_str = str(project.source_url)
            u_hash = compute_url_hash(url_str)
            c_hash = compute_content_hash(project.title, project.description)
            doc = {
                "id": project_id,
                "source_id": source_id,
                "source": project.source,
                "external_id": external_id,
                "title": project.title,
                "description": project.description,
                "source_url": url_str,
                "url_hash": u_hash,
                "content_hash": c_hash,
                "client_name": project.client_name,
                "budget": project.budget,
                "currency": project.currency,
                "project_type": project.project_type,
                "skills": project.skills,
                "status": status or "DISCOVERED",
                "score": project.score,
                "posted_at": project.project_start_date,
                "deadline": project.project_end_date,
                "raw_data": raw_data,
                "created_at": now,
                "updated_at": now,
            }
        elif isinstance(project, dict):
            url_str = str(project.get("source_url", project.get("url", "")))
            u_hash = project.get("url_hash", compute_url_hash(url_str))
            c_hash = project.get(
                "content_hash",
                compute_content_hash(project.get("title", ""), project.get("description", "")),
            )
            doc = {
                "id": project_id,
                "source_id": source_id or project.get("source_id"),
                "source": project.get("source", project.get("source_name", "Unknown")),
                "external_id": external_id or project.get("external_id"),
                "title": project["title"],
                "description": project["description"],
                "source_url": url_str,
                "url_hash": u_hash,
                "content_hash": c_hash,
                "client_name": project.get("client_name"),
                "budget": project.get("budget"),
                "currency": project.get("currency", "USD"),
                "project_type": project.get("project_type"),
                "skills": project.get("skills", []),
                "status": status or project.get("status") or "DISCOVERED",
                "score": project.get("score"),
                "posted_at": project.get("posted_at"),
                "deadline": project.get("deadline"),
                "raw_data": raw_data or project.get("raw_data"),
                "created_at": now,
                "updated_at": now,
            }
        else:
            raise TypeError(f"Unsupported project format: {type(project)}")

        self.coll.insert_one(doc)
        if "_id" in doc:
            doc.pop("_id")
        return cast(dict[str, Any], doc)

    def save_project(self, project: Project) -> dict[str, Any] | None:
        """Save a single project if not duplicate."""
        url_str = str(project.source_url)
        c_hash = compute_content_hash(project.title, project.description)
        if self.is_duplicate(url_str, c_hash):
            return None
        return self.add(project)

    def add_many(
        self,
        projects: list[Project | dict[str, Any]],
        skip_duplicates: bool = True,
        source_id: int | None = None,
    ) -> list[dict[str, Any]]:
        """Batch save multiple project documents with duplicate filtering."""
        persisted: list[dict[str, Any]] = []
        for item in projects:
            if isinstance(item, Project):
                url = str(item.source_url)
                c_hash = compute_content_hash(item.title, item.description)
            elif isinstance(item, dict):
                url = str(item.get("source_url", item.get("url", "")))
                c_hash = item.get(
                    "content_hash",
                    compute_content_hash(item.get("title", ""), item.get("description", "")),
                )
            else:
                continue

            if skip_duplicates and self.is_duplicate(url, c_hash):
                continue

            doc = self.add(item, source_id=source_id)
            persisted.append(doc)
        return persisted

    def list_projects(
        self,
        status: str | None = None,
        source_name: str | None = None,
        source: str | None = None,
        min_score: float | None = None,
        skill: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Query projects matching status, source, score, and skill filters."""
        query: dict[str, Any] = {}
        if status:
            query["status"] = status
        filter_source = source_name or source
        if filter_source:
            query["source"] = filter_source
        if min_score is not None:
            query["score"] = {"$gte": min_score}
        if skill:
            query["skills"] = {"$regex": f"^{skill}$", "$options": "i"}

        cursor = self.coll.find(query).sort("created_at", DESCENDING).skip(offset).limit(limit)
        results: list[dict[str, Any]] = []
        for doc in cursor:
            if "_id" in doc:
                doc.pop("_id")
            results.append(cast(dict[str, Any], doc))
        return results

    def update_status(self, project_id: int, status: str) -> dict[str, Any] | None:
        """Update project workflow status."""
        doc = self.coll.find_one_and_update(
            {"id": project_id},
            {"$set": {"status": status, "updated_at": datetime.now(UTC)}},
            return_document=ReturnDocument.AFTER,
        )
        if doc and "_id" in doc:
            doc.pop("_id")
        return cast(dict[str, Any] | None, doc)

    def update_score(self, project_id: int, score: float) -> dict[str, Any] | None:
        """Update project relevance score."""
        doc = self.coll.find_one_and_update(
            {"id": project_id},
            {"$set": {"score": score, "updated_at": datetime.now(UTC)}},
            return_document=ReturnDocument.AFTER,
        )
        if doc and "_id" in doc:
            doc.pop("_id")
        return cast(dict[str, Any] | None, doc)

    def delete(self, project_id: int) -> bool:
        """Delete project document by ID."""
        res = self.coll.delete_one({"id": project_id})
        return res.deleted_count > 0

    def count(
        self,
        status: str | None = None,
        source_name: str | None = None,
        source: str | None = None,
    ) -> int:
        """Count total projects matching filters."""
        query: dict[str, Any] = {}
        if status:
            query["status"] = status
        filter_source = source_name or source
        if filter_source:
            query["source"] = filter_source
        return int(self.coll.count_documents(query))


class MongoOpportunityRepository:
    """
    MongoDB repository for storing and querying multi-factor scored opportunities.
    """

    def __init__(self, db: Database[Any] | None = None):
        self.db = db or get_mongo_db()
        self.coll = self.db["opportunities"]

    def get_by_project_id(self, project_id: int) -> dict[str, Any] | None:
        """Retrieve opportunity breakdown by parent project ID."""
        doc = self.coll.find_one({"project_id": project_id})
        if doc and "_id" in doc:
            doc.pop("_id")
        return cast(dict[str, Any] | None, doc)

    def create_or_update(
        self,
        project_id: int,
        overall_score: float,
        skill_match_score: float | None = None,
        budget_score: float | None = None,
        client_score: float | None = None,
        competition_score: float | None = None,
        complexity_score: float | None = None,
        freshness_score: float | None = None,
        win_probability: float | None = None,
        explanation: str | None = None,
    ) -> dict[str, Any]:
        """Create or update opportunity score breakdown."""
        now = datetime.now(UTC)
        update_data = {
            "project_id": project_id,
            "overall_score": overall_score,
            "skill_match_score": skill_match_score,
            "budget_score": budget_score,
            "client_score": client_score,
            "competition_score": competition_score,
            "complexity_score": complexity_score,
            "freshness_score": freshness_score,
            "win_probability": win_probability,
            "explanation": explanation,
            "updated_at": now,
        }
        doc = self.coll.find_one_and_update(
            {"project_id": project_id},
            {
                "$set": update_data,
                "$setOnInsert": {
                    "id": get_next_sequence(self.db, "opportunity_id"),
                    "created_at": now,
                },
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )

        # Synchronize score with parent project document
        proj_repo = MongoProjectRepository(self.db)
        proj_repo.update_score(project_id, overall_score)

        if doc and "_id" in doc:
            doc.pop("_id")
        return cast(dict[str, Any], doc)

    def list_top_opportunities(
        self, limit: int = 20, min_score: float = 0.0
    ) -> list[dict[str, Any]]:
        """List highest scored opportunities."""
        cursor = (
            self.coll.find({"overall_score": {"$gte": min_score}})
            .sort("overall_score", DESCENDING)
            .limit(limit)
        )
        results: list[dict[str, Any]] = []
        for doc in cursor:
            if "_id" in doc:
                doc.pop("_id")
            results.append(cast(dict[str, Any], doc))
        return results


class MongoCollectionRunRepository:
    """
    MongoDB repository for managing collector telemetry runs.
    """

    def __init__(self, db: Database[Any] | None = None):
        self.db = db or get_mongo_db()
        self.coll = self.db["collection_runs"]

    def start_run(self, source: str) -> dict[str, Any]:
        """Start a new collector run and log initial document."""
        run_id = get_next_sequence(self.db, "run_id")
        now = datetime.now(UTC)
        doc = {
            "id": run_id,
            "source": source,
            "status": "RUNNING",
            "items_collected": 0,
            "items_saved": 0,
            "duplicates_skipped": 0,
            "started_at": now,
        }
        self.coll.insert_one(doc)
        if "_id" in doc:
            doc.pop("_id")
        return cast(dict[str, Any], doc)

    def complete_run(
        self,
        run_id: int,
        items_collected: int = 0,
        items_saved: int = 0,
        duplicates_skipped: int = 0,
        status: str = "SUCCESS",
    ) -> dict[str, Any] | None:
        """Mark collector run as complete."""
        doc = self.coll.find_one_and_update(
            {"id": run_id},
            {
                "$set": {
                    "status": status,
                    "items_collected": items_collected,
                    "items_saved": items_saved,
                    "duplicates_skipped": duplicates_skipped,
                    "completed_at": datetime.now(UTC),
                }
            },
            return_document=ReturnDocument.AFTER,
        )
        if doc and "_id" in doc:
            doc.pop("_id")
        return cast(dict[str, Any] | None, doc)

    def fail_run(self, run_id: int, error_message: str) -> dict[str, Any] | None:
        """Mark collector run as failed with error details."""
        doc = self.coll.find_one_and_update(
            {"id": run_id},
            {
                "$set": {
                    "status": "FAILED",
                    "error_message": error_message,
                    "completed_at": datetime.now(UTC),
                }
            },
            return_document=ReturnDocument.AFTER,
        )
        if doc and "_id" in doc:
            doc.pop("_id")
        return cast(dict[str, Any] | None, doc)

    def get_by_id(self, run_id: int) -> dict[str, Any] | None:
        """Fetch collection run by ID."""
        doc = self.coll.find_one({"id": run_id})
        if doc and "_id" in doc:
            doc.pop("_id")
        return cast(dict[str, Any] | None, doc)

    def list_recent_runs(self, limit: int = 20) -> list[dict[str, Any]]:
        """List most recent collection runs."""
        cursor = self.coll.find().sort("started_at", DESCENDING).limit(limit)
        results: list[dict[str, Any]] = []
        for doc in cursor:
            if "_id" in doc:
                doc.pop("_id")
            results.append(cast(dict[str, Any], doc))
        return results

    def create_run(
        self,
        source_name: str,
        projects_found: int = 0,
        new_projects: int = 0,
        duration_seconds: float = 0.0,
        status: str = "SUCCESS",
    ) -> dict[str, Any]:
        """Create a completed run record directly."""
        run_id = get_next_sequence(self.db, "run_id")
        now = datetime.now(UTC)
        doc = {
            "id": run_id,
            "source": source_name,
            "status": status,
            "items_collected": projects_found,
            "items_saved": new_projects,
            "duplicates_skipped": max(0, projects_found - new_projects),
            "started_at": now,
            "completed_at": now,
            "duration_seconds": duration_seconds,
        }
        self.coll.insert_one(doc)
        if "_id" in doc:
            doc.pop("_id")
        return cast(dict[str, Any], doc)


class MongoApplicationRepository:
    """
    MongoDB repository for managing freelance applications and funnel transitions.
    """

    def __init__(self, db: Database[Any] | None = None):
        self.db = db or get_mongo_db()
        self.coll = self.db["applications"]

    def create(
        self,
        project_id: int,
        status: str = ApplicationStatus.APPLIED.value,
        proposed_budget: float | None = None,
        currency: str = "USD",
        proposal_text: str | None = None,
        pitch_angle: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """Record a new application in MongoDB."""
        now = datetime.now(UTC)
        app_id = get_next_sequence(self.db, "application_id")
        doc = {
            "id": app_id,
            "project_id": project_id,
            "status": status,
            "proposed_budget": proposed_budget,
            "currency": currency,
            "proposal_text": proposal_text,
            "pitch_angle": pitch_angle,
            "notes": notes,
            "applied_at": now,
            "created_at": now,
            "updated_at": now,
        }
        self.coll.insert_one(doc)

        # Synchronize parent project status
        proj_repo = MongoProjectRepository(self.db)
        proj_repo.update_status(project_id, status)

        if "_id" in doc:
            doc.pop("_id")
        return cast(dict[str, Any], doc)

    def get_by_id(self, application_id: int) -> dict[str, Any] | None:
        """Fetch application by ID."""
        doc = self.coll.find_one({"id": application_id})
        if doc and "_id" in doc:
            doc.pop("_id")
        return cast(dict[str, Any] | None, doc)

    def get_by_project_id(self, project_id: int) -> dict[str, Any] | None:
        """Fetch application by target project ID."""
        doc = self.coll.find_one({"project_id": project_id})
        if doc and "_id" in doc:
            doc.pop("_id")
        return cast(dict[str, Any] | None, doc)

    def update_status(
        self,
        application_id: int,
        status: str,
        actual_revenue: float | None = None,
        client_feedback: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any] | None:
        """Transition application status and sync with parent project."""
        now = datetime.now(UTC)
        update_fields: dict[str, Any] = {
            "status": status,
            "updated_at": now,
        }
        if actual_revenue is not None:
            update_fields["actual_revenue"] = actual_revenue
        if client_feedback is not None:
            update_fields["client_feedback"] = client_feedback
        if notes is not None:
            update_fields["notes"] = notes

        doc = self.coll.find_one_and_update(
            {"id": application_id},
            {"$set": update_fields},
            return_document=ReturnDocument.AFTER,
        )
        if doc:
            # Sync parent project status
            proj_repo = MongoProjectRepository(self.db)
            proj_repo.update_status(doc["project_id"], status)
            if "_id" in doc:
                doc.pop("_id")
        return cast(dict[str, Any] | None, doc)

    def list_applications(
        self,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List tracked applications."""
        query: dict[str, Any] = {}
        if status:
            query["status"] = status

        cursor = self.coll.find(query).sort("applied_at", DESCENDING).skip(offset).limit(limit)
        results: list[dict[str, Any]] = []
        for doc in cursor:
            if "_id" in doc:
                doc.pop("_id")
            results.append(cast(dict[str, Any], doc))
        return results

    def delete(self, application_id: int) -> bool:
        """Delete application document."""
        res = self.coll.delete_one({"id": application_id})
        return res.deleted_count > 0
