"""
FastAPI Router for AI Executive Agent & Autonomous Lead Acquisition Orchestrator.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from src.auth.dependencies import get_current_tenant, get_current_user, require_role
from src.auth.schemas import TenantResponse, UserProfileResponse, UserRole
from src.executive.coordinator import GLOBAL_EXECUTIVE_COORDINATOR
from src.executive.schemas import (
    AutonomousPolicyConfig,
    ExecutiveActionLog,
    ExecutiveCycleResult,
    ExecutiveTelemetryKPIs,
)
from src.executive.telemetry import GLOBAL_EXECUTIVE_TELEMETRY

router = APIRouter(prefix="/api/executive", tags=["AI Executive Agent & Autonomous Orchestrator"])


@router.get("/status", response_model=ExecutiveTelemetryKPIs)
def get_executive_status(
    user: UserProfileResponse = Depends(get_current_user),
    tenant: TenantResponse = Depends(get_current_tenant),
) -> ExecutiveTelemetryKPIs:
    """
    Get executive AI status, active policy rules, autonomy level, and velocity KPIs.
    """
    return GLOBAL_EXECUTIVE_TELEMETRY.get_kpis(tenant_id=tenant.tenant_id)


@router.post("/config", response_model=AutonomousPolicyConfig)
def update_autonomy_config(
    policy: AutonomousPolicyConfig,
    user: UserProfileResponse = Depends(require_role(UserRole.ADMIN)),
    tenant: TenantResponse = Depends(get_current_tenant),
) -> AutonomousPolicyConfig:
    """
    Update autonomy execution mode, minimum score thresholds, risk floors, and daily quotas (Admin only).
    """
    return GLOBAL_EXECUTIVE_TELEMETRY.update_policy(tenant_id=tenant.tenant_id, new_policy=policy)


@router.post("/cycle", response_model=ExecutiveCycleResult)
def trigger_executive_cycle(
    user: UserProfileResponse = Depends(get_current_user),
    tenant: TenantResponse = Depends(get_current_tenant),
) -> ExecutiveCycleResult:
    """
    Trigger an immediate 7-step autonomous lead acquisition cycle.
    """
    return GLOBAL_EXECUTIVE_COORDINATOR.run_autonomous_cycle(tenant_id=tenant.tenant_id)


@router.get("/activity-log", response_model=list[ExecutiveActionLog])
def get_executive_activity_log(
    limit: int = 50,
    user: UserProfileResponse = Depends(get_current_user),
    tenant: TenantResponse = Depends(get_current_tenant),
) -> list[ExecutiveActionLog]:
    """
    Retrieve real-time audit stream of executive decision logs and time-saved estimates.
    """
    return GLOBAL_EXECUTIVE_TELEMETRY.get_logs(tenant_id=tenant.tenant_id, limit=limit)
