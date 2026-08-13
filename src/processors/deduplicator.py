import hashlib
import logging
import re
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from src.models.project import Project

logger = logging.getLogger(__name__)

# Standard query parameters that do not alter the identity of a post/project
TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "ref",
    "fbclid",
    "gclid",
    "source",
}


def normalize_url(url: str) -> str:
    """
    Produce a canonical version of a URL by:
      - Lowercasing the scheme and network location (hostname)
      - Stripping standard analytics/tracking query parameters
      - Sorting remaining query parameters deterministically
      - Stripping trailing slashes
    """
    if not url:
        return ""
    try:
        parsed = urlparse(url.strip())
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()
        path = parsed.path.rstrip("/")

        # Filter out tracking query parameters
        filtered_queries = [
            (k, v)
            for k, v in parse_qsl(parsed.query, keep_blank_values=True)
            if k.lower() not in TRACKING_PARAMS
        ]
        filtered_queries.sort(key=lambda x: x[0])
        query = urlencode(filtered_queries)

        return urlunparse((scheme, netloc, path, parsed.params, query, ""))
    except Exception as exc:
        logger.warning("Error normalizing URL '%s': %s", url, exc)
        return url.strip().rstrip("/")


def compute_url_hash(url: str) -> str:
    """Compute a SHA-256 hash of a normalized URL."""
    canonical_url = normalize_url(url)
    return hashlib.sha256(canonical_url.encode("utf-8")).hexdigest()


def normalize_content(title: str, description: str) -> str:
    """
    Produce a normalized string representing project content by:
      - Lowercasing
      - Removing special characters / punctuation
      - Collapsing multiple whitespaces into a single space
    """
    combined = f"{title} {description}".lower()
    clean_text = re.sub(r"[^a-z0-9\s]", " ", combined)
    return re.sub(r"\s+", " ", clean_text).strip()


def compute_content_hash(title: str, description: str) -> str:
    """Compute a SHA-256 fingerprint of the normalized title and description."""
    normalized = normalize_content(title, description)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class ProjectDeduplicator:
    """
    Identifies and removes duplicate project opportunities across collection runs.
    """

    def __init__(self):
        self._seen_url_hashes: set[str] = set()
        self._seen_content_hashes: set[str] = set()

    def is_duplicate(
        self,
        project: dict[str, Any] | Project,
        existing_url_hashes: set[str] | None = None,
        existing_content_hashes: set[str] | None = None,
    ) -> bool:
        """
        Check whether a project is a duplicate based on URL or content fingerprint.
        """
        if isinstance(project, Project):
            url_str = str(project.source_url)
            title = project.title
            description = project.description
        else:
            url_str = str(project.get("source_url", ""))
            title = str(project.get("title", ""))
            description = str(project.get("description", ""))

        url_hash = compute_url_hash(url_str)
        content_hash = compute_content_hash(title, description)

        # Check against existing hashes if provided
        if existing_url_hashes and url_hash in existing_url_hashes:
            return True
        if existing_content_hashes and content_hash in existing_content_hashes:
            return True

        # Check against in-memory session hashes
        if url_hash in self._seen_url_hashes:
            return True
        if content_hash in self._seen_content_hashes:
            return True

        return False

    def mark_seen(self, project: dict[str, Any] | Project) -> None:
        """Mark a project's hashes as seen in the deduplicator cache."""
        if isinstance(project, Project):
            url_str = str(project.source_url)
            title = project.title
            description = project.description
        else:
            url_str = str(project.get("source_url", ""))
            title = str(project.get("title", ""))
            description = str(project.get("description", ""))

        self._seen_url_hashes.add(compute_url_hash(url_str))
        self._seen_content_hashes.add(compute_content_hash(title, description))

    def deduplicate_batch(
        self,
        projects: list[dict[str, Any]],
        existing_url_hashes: set[str] | None = None,
        existing_content_hashes: set[str] | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """
        Filter out duplicate projects from a batch.

        Returns:
            Tuple of (unique_projects, duplicate_count)
        """
        unique_projects: list[dict[str, Any]] = []
        duplicate_count = 0

        for project in projects:
            if self.is_duplicate(
                project,
                existing_url_hashes=existing_url_hashes,
                existing_content_hashes=existing_content_hashes,
            ):
                duplicate_count += 1
                logger.debug(
                    "Skipping duplicate project: '%s' (%s)",
                    project.get("title", "Untitled"),
                    project.get("source_url", ""),
                )
            else:
                self.mark_seen(project)
                unique_projects.append(project)

        logger.info(
            "Deduplication complete: %d received, %d unique kept, %d duplicates dropped",
            len(projects),
            len(unique_projects),
            duplicate_count,
        )
        return unique_projects, duplicate_count
