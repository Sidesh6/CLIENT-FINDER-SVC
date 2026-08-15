"""
FastAPI Multi-Tenant SaaS Workspace & Team RBAC REST Router.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from src.auth.dependencies import (
    get_current_tenant,
    require_role,
)
from src.auth.metering import GLOBAL_QUOTA_METER
from src.auth.schemas import (
    QuotaUsageResponse,
    TenantMemberInvite,
    TenantMemberItem,
    TenantMemberUpdate,
    TenantResponse,
    UserProfileResponse,
    UserRole,
)
from src.auth.store import GLOBAL_TENANT_STORE

router = APIRouter(prefix="/api/tenants", tags=["Tenant Workspaces & Team RBAC"])


@router.get("/current", response_model=TenantResponse)
def get_current_workspace_details(
    tenant: TenantResponse = Depends(get_current_tenant),
) -> TenantResponse:
    """
    Retrieve current tenant workspace metadata, plan limits, and member roster.
    """
    return tenant


@router.get("/quota", response_model=QuotaUsageResponse)
def get_workspace_quota_consumption(
    tenant: TenantResponse = Depends(get_current_tenant),
) -> QuotaUsageResponse:
    """
    Retrieve real-time monthly request quota consumption and minute throughput limits.
    """
    return GLOBAL_QUOTA_METER.get_quota_status(
        tenant_id=tenant.tenant_id,
        plan_tier=tenant.plan_tier,
    )


@router.post("/invite", response_model=TenantMemberItem, status_code=status.HTTP_201_CREATED)
def invite_team_member(
    req: TenantMemberInvite,
    user: UserProfileResponse = Depends(require_role(UserRole.ADMIN)),
    tenant: TenantResponse = Depends(get_current_tenant),
) -> TenantMemberItem:
    """
    Invite a new team member into the workspace with assigned RBAC role (Admin only).
    """
    try:
        return GLOBAL_TENANT_STORE.invite_member(
            tenant_id=tenant.tenant_id,
            email=req.email,
            full_name=req.full_name,
            role=req.role,
        )
    except (ValueError, KeyError) as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)) from err


@router.patch("/members/{member_user_id}", response_model=TenantMemberItem)
def update_member_role_or_status(
    member_user_id: str,
    req: TenantMemberUpdate,
    user: UserProfileResponse = Depends(require_role(UserRole.ADMIN)),
    tenant: TenantResponse = Depends(get_current_tenant),
) -> TenantMemberItem:
    """
    Update a workspace team member's role or active status (Admin only).
    """
    updated = GLOBAL_TENANT_STORE.update_member(
        tenant_id=tenant.tenant_id,
        user_id=member_user_id,
        role=req.role,
        is_active=req.is_active,
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Member '{member_user_id}' not found in workspace.",
        )
    return updated
