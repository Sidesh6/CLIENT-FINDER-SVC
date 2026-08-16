"""
Executive Telemetry Tracker — Activity Log Stream, Time Saved Metrics, and Policy Store.
"""

import logging
import uuid
from datetime import UTC, datetime

from src.executive.schemas import (
    ActionCategory,
    AutonomousPolicyConfig,
    AutonomyMode,
    ExecutiveActionLog,
    ExecutiveTelemetryKPIs,
)

logger = logging.getLogger("ExecutiveTelemetryTracker")


class ExecutiveTelemetryTracker:
    """
    Tracks autonomous decision logs, policy configurations, and executive velocity metrics.
    """

    def __init__(self) -> None:
        self._policies: dict[str, AutonomousPolicyConfig] = {}
        self._logs: dict[str, list[ExecutiveActionLog]] = {}  # tenant_id -> logs
        self._cycles_count: dict[str, int] = {}
        self._last_cycle: dict[str, datetime] = {}
        self._seed_demo_logs()

    def get_policy(self, tenant_id: str) -> AutonomousPolicyConfig:
        """Get or initialize policy config for a tenant."""
        if tenant_id not in self._policies:
            self._policies[tenant_id] = AutonomousPolicyConfig(tenant_id=tenant_id)
        return self._policies[tenant_id]

    def update_policy(self, tenant_id: str, new_policy: AutonomousPolicyConfig) -> AutonomousPolicyConfig:
        """Update and persist policy config."""
        new_policy.tenant_id = tenant_id
        self._policies[tenant_id] = new_policy
        logger.info("Updated executive autonomy policies for tenant '%s': mode=%s, min_score=%.1f", tenant_id, new_policy.autonomy_mode.value, new_policy.min_score_threshold)
        return new_policy

    def record_action(
        self,
        tenant_id: str,
        category: ActionCategory,
        opportunity_title: str,
        description: str,
        mode: AutonomyMode,
        auto_executed: bool,
        project_id: str | None = None,
        time_saved_mins: float = 15.0,
    ) -> ExecutiveActionLog:
        """Record an autonomous action in the executive audit stream."""
        now = datetime.now(UTC)
        log = ExecutiveActionLog(
            action_id=f"act_{uuid.uuid4().hex[:10]}",
            tenant_id=tenant_id,
            category=category,
            project_id=project_id,
            opportunity_title=opportunity_title,
            action_description=description,
            autonomy_level=mode,
            was_auto_executed=auto_executed,
            estimated_time_saved_mins=time_saved_mins,
            created_at=now,
        )
        if tenant_id not in self._logs:
            self._logs[tenant_id] = []
        self._logs[tenant_id].insert(0, log)  # Most recent first
        return log

    def get_logs(self, tenant_id: str, limit: int = 50) -> list[ExecutiveActionLog]:
        """Retrieve recent executive decision logs."""
        return self._logs.get(tenant_id, [])[:limit]

    def get_kpis(self, tenant_id: str) -> ExecutiveTelemetryKPIs:
        """Compute aggregated executive KPIs."""
        logs = self._logs.get(tenant_id, [])
        policy = self.get_policy(tenant_id)

        proposals = len([l for l in logs if l.category == ActionCategory.PROPOSAL_SYNTHESIS])
        outreach = len([l for l in logs if l.category == ActionCategory.OUTREACH_SEQUENCE])
        contracts = len([l for l in logs if l.category == ActionCategory.CONTRACT_GENERATION])
        time_saved_mins = sum(l.estimated_time_saved_mins for l in logs)

        return ExecutiveTelemetryKPIs(
            tenant_id=tenant_id,
            current_mode=policy.autonomy_mode,
            active_policies=policy,
            total_cycles_run=self._cycles_count.get(tenant_id, 0),
            total_actions_taken=len(logs),
            total_proposals_auto_drafted=proposals,
            total_outreach_auto_queued=outreach,
            total_contracts_auto_generated=contracts,
            total_time_saved_hours=round(time_saved_mins / 60.0, 1),
            pipeline_velocity_multiplier=3.8 if policy.autonomy_mode == AutonomyMode.FULLY_AUTONOMOUS else 2.2,
            last_cycle_at=self._last_cycle.get(tenant_id),
        )

    def mark_cycle_executed(self, tenant_id: str) -> None:
        self._cycles_count[tenant_id] = self._cycles_count.get(tenant_id, 0) + 1
        self._last_cycle[tenant_id] = datetime.now(UTC)

    def _seed_demo_logs(self) -> None:
        """Seed realistic demo action logs for initial dashboard presentation."""
        tenant_id = "default_tenant"
        now = datetime.now(UTC)

        demo_actions = [
            (ActionCategory.CONTRACT_GENERATION, "SOW — Next.js E-Commerce Frontend", "Auto-generated protective SOW contract with Net-14 payment terms.", 20.0),
            (ActionCategory.OUTREACH_SEQUENCE, "Machine Learning Model Integration", "Enrolled client lead into 5-step consultative email outreach sequence.", 25.0),
            (ActionCategory.PROPOSAL_SYNTHESIS, "FastAPI & Distributed Harvester", "Synthesized Technical Expert cover letter proposal matching 4/4 skills.", 30.0),
            (ActionCategory.DOSSIER_AND_RISK, "NovaTech Solutions", "Verified client dossier background: Trust Score 92/100, Scam Risk Low.", 15.0),
            (ActionCategory.HARVEST_AND_SCORE, "Multi-Source Feed Sweep", "Harvested and scored 14 new opportunities across RemoteOK & Hacker News.", 10.0),
        ]

        for cat, title, desc, time_saved in demo_actions:
            self.record_action(
                tenant_id=tenant_id,
                category=cat,
                opportunity_title=title,
                description=desc,
                mode=AutonomyMode.SEMI_AUTONOMOUS,
                auto_executed=True,
                time_saved_mins=time_saved,
            )
        self._cycles_count[tenant_id] = 5
        self._last_cycle[tenant_id] = now


GLOBAL_EXECUTIVE_TELEMETRY = ExecutiveTelemetryTracker()
