"""
FastAPI Enterprise CRM Two-Way Sync & Deal Pipeline REST Router.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from src.auth.dependencies import get_current_tenant, get_current_user, require_role
from src.auth.schemas import TenantResponse, UserProfileResponse, UserRole
from src.crm.schemas import (
    CRMConnectionConfig,
    CRMProvider,
    CRMSyncLog,
    CRMSyncRequest,
    CRMSyncResult,
)
from src.crm.syncer import GLOBAL_CRM_SYNCER

router = APIRouter(prefix="/api/crm", tags=["CRM Synchronization & Integrations"])


@router.get("/connectors", response_model=list[CRMConnectionConfig])
def list_crm_connectors(
    user: UserProfileResponse = Depends(get_current_user),
    tenant: TenantResponse = Depends(get_current_tenant),
) -> list[CRMConnectionConfig]:
    """
    List all supported CRM providers and their connection configurations for the current workspace.
    """
    return GLOBAL_CRM_SYNCER.list_configs(tenant_id=tenant.tenant_id)


@router.post("/connectors/{provider}/configure", response_model=CRMConnectionConfig)
def configure_crm_connector(
    provider: CRMProvider,
    config: CRMConnectionConfig,
    user: UserProfileResponse = Depends(require_role(UserRole.ADMIN)),
    tenant: TenantResponse = Depends(get_current_tenant),
) -> CRMConnectionConfig:
    """
    Configure credentials, database/base IDs, and mapping rules for a CRM provider (Admin only).
    """
    config.provider = provider
    return GLOBAL_CRM_SYNCER.update_config(tenant_id=tenant.tenant_id, config=config)


@router.post("/connectors/{provider}/test")
def test_crm_connection(
    provider: CRMProvider,
    user: UserProfileResponse = Depends(get_current_user),
    tenant: TenantResponse = Depends(get_current_tenant),
) -> dict:
    """
    Test authentication and connectivity for a specific CRM provider.
    """
    success, message = GLOBAL_CRM_SYNCER.test_connection(
        tenant_id=tenant.tenant_id, provider=provider
    )
    return {"provider": provider.value, "success": success, "message": message}


@router.post("/sync", response_model=CRMSyncResult)
def trigger_crm_sync(
    req: CRMSyncRequest,
    user: UserProfileResponse = Depends(get_current_user),
    tenant: TenantResponse = Depends(get_current_tenant),
) -> CRMSyncResult:
    """
    Trigger manual or automated synchronization of opportunities to the selected CRM.
    """
    try:
        return GLOBAL_CRM_SYNCER.sync_opportunities(tenant_id=tenant.tenant_id, req=req)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)) from err


@router.get("/logs", response_model=list[CRMSyncLog])
def get_crm_sync_logs(
    user: UserProfileResponse = Depends(get_current_user),
    tenant: TenantResponse = Depends(get_current_tenant),
) -> list[CRMSyncLog]:
    """
    Retrieve historical sync audit logs for the workspace.
    """
    return GLOBAL_CRM_SYNCER.get_sync_logs(tenant_id=tenant.tenant_id)
