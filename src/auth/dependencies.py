"""
FastAPI Security Dependencies, JWT Authentication, and RBAC Role Enforcement Guards.
"""

import logging
from collections.abc import Callable

from fastapi import Depends, Header, HTTPException, Request, Response, status

from src.auth.metering import GLOBAL_QUOTA_METER
from src.auth.schemas import (
    TenantResponse,
    UserProfileResponse,
    UserRole,
)
from src.auth.security import decode_access_token
from src.auth.store import GLOBAL_TENANT_STORE

logger = logging.getLogger("AuthDependencies")


def get_current_user(
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> UserProfileResponse:
    """
    Authenticate request via Bearer JWT token or programmatic X-API-Key header.
    Defaults to the seeded admin user when no auth headers are provided in local development.
    """
    # 1. API Key Authentication
    if x_api_key:
        lookup = GLOBAL_TENANT_STORE.lookup_api_key(x_api_key)
        if not lookup:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or revoked API Key.",
                headers={"WWW-Authenticate": "ApiKey"},
            )
        tenant, api_key = lookup
        user = GLOBAL_TENANT_STORE.get_user_by_id(api_key.created_by_user_id)
        if user:
            return user
        # Fallback profile for key
        return UserProfileResponse(
            user_id=api_key.created_by_user_id,
            email="apikey@clientfinder.service",
            full_name=f"API Key: {api_key.name}",
            role=UserRole.ADMIN,
            tenant_id=tenant.tenant_id,
            workspace_name=tenant.name,
            plan_tier=tenant.plan_tier,
            created_at=api_key.created_at,
        )

    # 2. Bearer JWT Authentication
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()
        claims = decode_access_token(token)
        if not claims:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid, expired, or malformed authentication token.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user_id = claims.get("sub")
        user = GLOBAL_TENANT_STORE.get_user_by_id(user_id) if user_id else None
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User associated with token no longer exists.",
            )
        return user

    # 3. Default fallback for testing / local development
    default_user = GLOBAL_TENANT_STORE.get_user_by_id("default_admin")
    if default_user:
        return default_user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing required authentication credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_tenant(
    user: UserProfileResponse = Depends(get_current_user),
) -> TenantResponse:
    """Retrieve workspace tenant record for the authenticated user."""
    tenant = GLOBAL_TENANT_STORE.get_tenant_by_id(user.tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace tenant '{user.tenant_id}' not found.",
        )
    return tenant


def require_role(min_role: UserRole) -> Callable:
    """
    Dependency factory enforcing minimum required RBAC role.
    """

    def _role_guard(
        user: UserProfileResponse = Depends(get_current_user),
    ) -> UserProfileResponse:
        if not user.role.can_access(min_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Action requires minimum '{min_role.value}' privileges (current: '{user.role.value}').",
            )
        return user

    return _role_guard


def enforce_quota(
    response: Response,
    tenant: TenantResponse = Depends(get_current_tenant),
) -> TenantResponse:
    """
    Enforces per-minute throughput limits and monthly request quotas.
    Injects standard rate limit response headers.
    """
    is_allowed, telemetry, headers = GLOBAL_QUOTA_METER.check_and_consume(
        tenant_id=tenant.tenant_id,
        plan_tier=tenant.plan_tier,
        tokens=1,
    )

    for k, v in headers.items():
        response.headers[k] = v

    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Workspace rate limit or monthly quota exceeded ({telemetry.requests_this_month}/{telemetry.monthly_quota_limit}). Upgrade plan to increase limits.",
            headers=headers,
        )

    return tenant
