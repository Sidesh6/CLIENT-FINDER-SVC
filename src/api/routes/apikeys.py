"""
FastAPI Programmatic API Key Management REST Router.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from src.auth.dependencies import (
    get_current_tenant,
    get_current_user,
    require_role,
)
from src.auth.schemas import (
    ApiKeyCreate,
    ApiKeyCreatedResponse,
    ApiKeyResponse,
    TenantResponse,
    UserProfileResponse,
    UserRole,
)
from src.auth.store import GLOBAL_TENANT_STORE

router = APIRouter(prefix="/api/apikeys", tags=["Programmatic API Keys"])


@router.post("", response_model=ApiKeyCreatedResponse, status_code=status.HTTP_201_CREATED)
def create_programmatic_api_key(
    req: ApiKeyCreate,
    user: UserProfileResponse = Depends(require_role(UserRole.ADMIN)),
    tenant: TenantResponse = Depends(get_current_tenant),
) -> ApiKeyCreatedResponse:
    """
    Issue a new programmatic API key for the workspace (Admin only).
    """
    try:
        return GLOBAL_TENANT_STORE.create_api_key(
            tenant_id=tenant.tenant_id,
            user_id=user.user_id,
            name=req.name,
            scopes=req.scopes,
            rate_limit=req.rate_limit_per_minute,
        )
    except KeyError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)) from err


@router.get("", response_model=list[ApiKeyResponse])
def list_workspace_api_keys(
    user: UserProfileResponse = Depends(get_current_user),
    tenant: TenantResponse = Depends(get_current_tenant),
) -> list[ApiKeyResponse]:
    """
    List all active and revoked programmatic API keys for the current workspace.
    """
    return GLOBAL_TENANT_STORE.list_api_keys(tenant_id=tenant.tenant_id)


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_programmatic_api_key(
    key_id: str,
    user: UserProfileResponse = Depends(require_role(UserRole.ADMIN)),
    tenant: TenantResponse = Depends(get_current_tenant),
) -> None:
    """
    Revoke a programmatic API key (Admin only).
    """
    revoked = GLOBAL_TENANT_STORE.revoke_api_key(tenant_id=tenant.tenant_id, key_id=key_id)
    if not revoked:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API key '{key_id}' not found in workspace.",
        )
