"""
Pydantic Schemas for Multi-Tenant SaaS Workspaces, User Authentication, Team RBAC, and API Key Quotas.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class UserRole(str, Enum):
    """Hierarchical Role-Based Access Control roles."""

    SUPERADMIN = "SUPERADMIN"
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"
    READONLY = "READONLY"

    @property
    def level(self) -> int:
        """Numeric rank for hierarchical privilege evaluation."""
        ranks = {
            UserRole.READONLY: 1,
            UserRole.MEMBER: 2,
            UserRole.ADMIN: 3,
            UserRole.SUPERADMIN: 4,
        }
        return ranks.get(self, 1)

    def can_access(self, required_role: "UserRole") -> bool:
        """Check if this role meets or exceeds the required privilege level."""
        return self.level >= required_role.level


class PlanTier(str, Enum):
    """SaaS Subscription Plan Tiers with varying resource and quota limits."""

    FREE = "FREE"
    STARTER = "STARTER"
    PRO = "PRO"
    ENTERPRISE = "ENTERPRISE"

    @property
    def max_seats(self) -> int:
        limits = {
            PlanTier.FREE: 1,
            PlanTier.STARTER: 3,
            PlanTier.PRO: 10,
            PlanTier.ENTERPRISE: 100,
        }
        return limits.get(self, 1)

    @property
    def monthly_request_quota(self) -> int:
        quotas = {
            PlanTier.FREE: 250,
            PlanTier.STARTER: 2500,
            PlanTier.PRO: 25000,
            PlanTier.ENTERPRISE: 500000,
        }
        return quotas.get(self, 250)

    @property
    def rate_limit_per_minute(self) -> int:
        limits = {
            PlanTier.FREE: 30,
            PlanTier.STARTER: 120,
            PlanTier.PRO: 600,
            PlanTier.ENTERPRISE: 3000,
        }
        return limits.get(self, 30)


class UserRegisterRequest(BaseModel):
    """Inbound request to register a new user and provision an initial workspace."""

    email: str = Field(pattern=r"^[^@]+@[^@]+\.[^@]+$", description="Valid email address")
    password: str = Field(min_length=6, description="Plaintext password to hash")
    full_name: str = Field(min_length=2, description="User's full name")
    workspace_name: str = Field(
        default="", description="Optional workspace name, defaults to user's name"
    )


class UserLoginRequest(BaseModel):
    """Inbound authentication credentials."""

    email: str = Field(pattern=r"^[^@]+@[^@]+\.[^@]+$")
    password: str


class TokenResponse(BaseModel):
    """Signed JWT bearer authentication token."""

    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int = 86400
    user_id: str
    tenant_id: str
    role: UserRole


class UserProfileResponse(BaseModel):
    """Authenticated user profile with workspace context."""

    user_id: str
    email: str
    full_name: str
    role: UserRole
    tenant_id: str
    workspace_name: str
    plan_tier: PlanTier
    created_at: datetime


class TenantMemberInvite(BaseModel):
    """Request to invite a new user into an existing workspace."""

    email: str = Field(pattern=r"^[^@]+@[^@]+\.[^@]+$")
    full_name: str = Field(default="Team Member")
    role: UserRole = Field(default=UserRole.MEMBER)


class TenantMemberUpdate(BaseModel):
    """Request to update an existing member's RBAC role or status."""

    role: UserRole | None = None
    is_active: bool | None = None


class TenantMemberItem(BaseModel):
    """A member in a tenant workspace."""

    user_id: str
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    joined_at: datetime


class TenantResponse(BaseModel):
    """Tenant workspace details with seat capacity and plan quotas."""

    tenant_id: str
    name: str
    slug: str
    plan_tier: PlanTier
    seats_used: int
    max_seats: int
    monthly_quota_used: int
    monthly_quota_total: int
    rate_limit_per_minute: int
    created_at: datetime
    members: list[TenantMemberItem] = Field(default_factory=list)


class ApiKeyCreate(BaseModel):
    """Request to generate a new programmatic API key."""

    name: str = Field(
        min_length=2, max_length=50, description="Label for the API key (e.g. Production Webhook)"
    )
    scopes: list[str] = Field(
        default_factory=lambda: ["read", "write"],
        description="Allowed permission scopes for this key",
    )
    rate_limit_per_minute: int | None = Field(
        default=None, description="Custom rate limit override"
    )


class ApiKeyResponse(BaseModel):
    """Public metadata for an issued API key."""

    id: str
    name: str
    key_prefix: str
    tenant_id: str
    created_by_user_id: str
    scopes: list[str]
    rate_limit_per_minute: int
    usage_count: int
    last_used_at: datetime | None
    created_at: datetime
    is_active: bool


class ApiKeyCreatedResponse(BaseModel):
    """One-time response containing the secret plaintext API key token."""

    api_key: ApiKeyResponse
    raw_secret_key: str = Field(
        description="Plaintext API key (only revealed once at generation time)"
    )


class QuotaUsageResponse(BaseModel):
    """Real-time quota consumption telemetry for a workspace."""

    tenant_id: str
    plan_tier: PlanTier
    requests_this_month: int
    monthly_quota_limit: int
    quota_percent_consumed: float
    current_minute_requests: int
    minute_rate_limit: int
    is_throttled: bool
    resets_at: datetime
