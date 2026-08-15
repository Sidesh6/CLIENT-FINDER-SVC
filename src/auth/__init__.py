"""
Multi-Tenant SaaS Workspace, Team RBAC, API Key Metering, and User Authentication Package.
"""

from src.auth.dependencies import (
    enforce_quota,
    get_current_tenant,
    get_current_user,
    require_role,
)
from src.auth.metering import (
    GLOBAL_QUOTA_METER,
    TenantQuotaMeter,
)
from src.auth.schemas import (
    ApiKeyCreate,
    ApiKeyCreatedResponse,
    ApiKeyResponse,
    PlanTier,
    QuotaUsageResponse,
    TenantMemberInvite,
    TenantMemberItem,
    TenantMemberUpdate,
    TenantResponse,
    TokenResponse,
    UserLoginRequest,
    UserProfileResponse,
    UserRegisterRequest,
    UserRole,
)
from src.auth.security import (
    create_access_token,
    decode_access_token,
    generate_api_key,
    hash_api_key,
    hash_password,
    verify_password,
)
from src.auth.store import (
    GLOBAL_TENANT_STORE,
    MultiTenantStore,
)

__all__ = [
    "UserRole",
    "PlanTier",
    "UserRegisterRequest",
    "UserLoginRequest",
    "TokenResponse",
    "UserProfileResponse",
    "TenantMemberInvite",
    "TenantMemberUpdate",
    "TenantMemberItem",
    "TenantResponse",
    "ApiKeyCreate",
    "ApiKeyResponse",
    "ApiKeyCreatedResponse",
    "QuotaUsageResponse",
    "hash_password",
    "verify_password",
    "create_access_token",
    "decode_access_token",
    "generate_api_key",
    "hash_api_key",
    "MultiTenantStore",
    "GLOBAL_TENANT_STORE",
    "TenantQuotaMeter",
    "GLOBAL_QUOTA_METER",
    "get_current_user",
    "get_current_tenant",
    "require_role",
    "enforce_quota",
]
