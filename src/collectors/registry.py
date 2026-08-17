"""
Collector Registry & Source Health Management.
Provides dynamic collector registration, enable/disable toggling, health metrics, and circuit-breaker protection.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from src.collectors.arbeitnow_collector import ArbeitnowCollector
from src.collectors.base_collector import BaseCollector
from src.collectors.client_lead_collector import ClientLeadCollector
from src.collectors.fiverr_collector import FiverrCollector
from src.collectors.freelancer_collector import FreelancerCollector
from src.collectors.guru_collector import GuruCollector
from src.collectors.hackernews_collector import HackerNewsCollector
from src.collectors.jobicy_collector import JobicyCollector
from src.collectors.peopleperhour_collector import PeoplePerHourCollector
from src.collectors.remotive_collector import RemotiveCollector
from src.collectors.remoteok_collector import RemoteOKCollector
from src.collectors.rss_collector import RSSFeedCollector
from src.collectors.upwork_rss_collector import UpworkRSSCollector
from src.collectors.web_collector import WebProjectCollector
from src.collectors.weworkremotely_collector import WeWorkRemotelyCollector


logger = logging.getLogger(__name__)


@dataclass
class CollectorHealthState:
    """Operational state and health metrics for a registered source collector."""

    source_name: str
    enabled: bool = True
    success_count: int = 0
    failure_count: int = 0
    consecutive_failures: int = 0
    total_items_collected: int = 0
    last_scrape_at: datetime | None = None
    last_error: str | None = None
    circuit_broken: bool = False

    @property
    def success_rate(self) -> float:
        """Calculate overall successful collection percentage."""
        total = self.success_count + self.failure_count
        if total == 0:
            return 100.0
        return round((self.success_count / total) * 100.0, 1)

    def to_dict(self) -> dict[str, Any]:
        """Serialize state for API and telemetry responses."""
        return {
            "name": self.source_name,
            "source_name": self.source_name,
            "enabled": self.enabled,
            "circuit_broken": self.circuit_broken,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "consecutive_failures": self.consecutive_failures,
            "success_rate": self.success_rate,
            "total_items_collected": self.total_items_collected,
            "last_scrape_at": self.last_scrape_at.isoformat() if self.last_scrape_at else None,
            "last_error": self.last_error,
        }


class CollectorRegistry:
    """
    Central registry managing collector instances, health tracking, and circuit-breaker thresholds.
    """

    def __init__(self, failure_threshold: int = 3):
        self._collectors: dict[str, BaseCollector] = {}
        self._states: dict[str, CollectorHealthState] = {}
        self.failure_threshold = failure_threshold

    def register(self, collector: BaseCollector, enabled: bool = True) -> None:
        """Register a new collector instance."""
        name = collector.source_name
        self._collectors[name] = collector
        if name not in self._states:
            self._states[name] = CollectorHealthState(source_name=name, enabled=enabled)
        else:
            self._states[name].enabled = enabled
        logger.info("Registered collector '%s' (enabled=%s).", name, enabled)

    def unregister(self, source_name: str) -> bool:
        """Unregister a collector by source name."""
        if source_name in self._collectors:
            del self._collectors[source_name]
            del self._states[source_name]
            logger.info("Unregistered collector '%s'.", source_name)
            return True
        return False

    def get_collector(self, source_name: str) -> BaseCollector | None:
        """Retrieve collector instance by name."""
        return self._collectors.get(source_name)

    def get_state(self, source_name: str) -> CollectorHealthState | None:
        """Retrieve health state for a collector."""
        return self._states.get(source_name)

    def list_sources(self) -> list[str]:
        """Return list of all registered source names."""
        return list(self._collectors.keys())

    def get_active_collectors(self) -> list[BaseCollector]:
        """
        Return list of collector instances that are enabled and not circuit-broken.
        """
        active: list[BaseCollector] = []
        for name, col in self._collectors.items():
            st = self._states.get(name)
            if st and st.enabled and not st.circuit_broken:
                active.append(col)
        return active

    def toggle(self, source_name: str, enable: bool | None = None) -> bool:
        """
        Enable or disable a specific collector. If enable is None, state is inverted.
        """
        st = self._states.get(source_name)
        if not st:
            raise KeyError(f"Collector '{source_name}' not found in registry.")

        if enable is None:
            st.enabled = not st.enabled
        else:
            st.enabled = enable

        # Reset circuit broken state if manually re-enabled
        if st.enabled:
            st.circuit_broken = False
            st.consecutive_failures = 0

        logger.info("Collector '%s' enabled set to %s.", source_name, st.enabled)
        return st.enabled

    def record_success(self, source_name: str, items_collected: int) -> None:
        """Record successful collection run."""
        st = self._states.get(source_name)
        if st:
            st.success_count += 1
            st.consecutive_failures = 0
            st.circuit_broken = False
            st.total_items_collected += items_collected
            st.last_scrape_at = datetime.now(UTC)
            st.last_error = None

    def record_failure(self, source_name: str, error_message: str) -> None:
        """Record failed collection run and check circuit breaker threshold."""
        st = self._states.get(source_name)
        if st:
            st.failure_count += 1
            st.consecutive_failures += 1
            st.last_scrape_at = datetime.now(UTC)
            st.last_error = error_message

            if st.consecutive_failures >= self.failure_threshold:
                st.circuit_broken = True
                logger.warning(
                    "Circuit breaker tripped for '%s' after %d consecutive failures. Feed temporarily suspended.",
                    source_name,
                    st.consecutive_failures,
                )

    def reset_circuit(self, source_name: str) -> bool:
        """Manually reset a tripped circuit breaker."""
        st = self._states.get(source_name)
        if st:
            st.circuit_broken = False
            st.consecutive_failures = 0
            return True
        return False

    def register_custom_feed(
        self, source_name: str, feed_url: str, enabled: bool = True
    ) -> BaseCollector:
        """Dynamically create and register an RSSFeedCollector for a custom feed URL."""
        from src.collectors.rss_collector import RSSFeedCollector

        collector = RSSFeedCollector(source_name=source_name, feed_url=feed_url)
        self.register(collector, enabled=enabled)
        return collector

    def get_all_states(self) -> list[CollectorHealthState]:
        """Return health telemetry for all registered sources."""
        return list(self._states.values())


from src.collectors.catalog import PLATFORM_SOURCES_CATALOG


def get_default_registry() -> CollectorRegistry:
    """
    Initialize and return the default collector registry pre-loaded with standard collectors
    and all supported multi-platform catalog feeds.
    """
    registry = CollectorRegistry()
    # 1. Primary Direct Client & Freelance Marketplace collectors enabled by default
    registry.register(ClientLeadCollector(), enabled=True)
    registry.register(UpworkRSSCollector(), enabled=True)
    registry.register(FiverrCollector(), enabled=True)
    registry.register(FreelancerCollector(), enabled=True)
    registry.register(GuruCollector(), enabled=True)
    registry.register(PeoplePerHourCollector(), enabled=True)
    registry.register(HackerNewsCollector(), enabled=True)

    # 2. Standard API & Aggregator collectors
    registry.register(RemoteOKCollector(), enabled=False)
    registry.register(WeWorkRemotelyCollector(), enabled=False)
    registry.register(RemotiveCollector(), enabled=False)
    registry.register(JobicyCollector(), enabled=False)
    registry.register(ArbeitnowCollector(), enabled=False)

    # 3. Dynamically register all multi-platform catalog sources (both RSS feeds and web directories)
    for s_def in PLATFORM_SOURCES_CATALOG:
        if s_def.name not in registry.list_sources():
            if s_def.feed_url:
                col = RSSFeedCollector(
                    source_name=s_def.name,
                    feed_url=s_def.feed_url,
                )
            else:
                col = WebProjectCollector(
                    source_name=s_def.name,
                    source_url=s_def.base_url,
                )
            registry.register(col, enabled=True)

    return registry



# Shared singleton instance
DEFAULT_REGISTRY = get_default_registry()
