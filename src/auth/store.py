"""
Multi-Tenant SaaS Data Store & User Identity Registry.
Manages Tenant Workspaces, User Accounts, Role Memberships, and API Keys.
"""

import logging
import secrets
import uuid
from datetime import UTC, datetime

from src.auth.schemas import (
    ApiKeyCreatedResponse,
    ApiKeyResponse,
    PlanTier,
    TenantMemberItem,
    TenantResponse,
    UserProfileResponse,
    UserRole,
)
from src.auth.security import generate_api_key, hash_api_key, hash_password, verify_password

logger = logging.getLogger("MultiTenantStore")


class MultiTenantStore:
    """
    Central persistence and lifecycle management for tenants, users, and API keys.
    """

    def __init__(self):
        self._tenants: dict[str, dict] = {}
        self._users: dict[str, dict] = {}  # keyed by user_id
        self._users_by_email: dict[str, str] = {}  # email -> user_id
        self._api_keys: dict[str, dict] = {}  # keyed by key_id
        self._api_keys_by_hash: dict[str, str] = {}  # hash -> key_id

        # Bootstrap default development tenant and administrator
        self._bootstrap_default_tenant()

    def _bootstrap_default_tenant(self) -> None:
        """Seed the default workspace and admin account."""
        tenant_id = "default_tenant"
        admin_id = "default_admin"

        if tenant_id not in self._tenants:
            self._tenants[tenant_id] = {
                "id": tenant_id,
                "name": "Default Developer Workspace",
                "slug": "default-workspace",
                "plan_tier": PlanTier.PRO,
                "created_at": datetime.now(UTC),
                "members": {
                    admin_id: {
                        "user_id": admin_id,
                        "role": UserRole.ADMIN,
                        "is_active": True,
                        "joined_at": datetime.now(UTC),
                    }
                },
            }

            self._users[admin_id] = {
                "id": admin_id,
                "email": "admin@clientfinder.local",
                "hashed_password": hash_password("AdminPass123!"),
                "full_name": "Senior Lead Engineer",
                "tenant_id": tenant_id,
                "role": UserRole.ADMIN,
                "created_at": datetime.now(UTC),
                "is_active": True,
            }
            self._users_by_email["admin@clientfinder.local"] = admin_id

            # Create default API key
            raw_key, prefix, key_hash = generate_api_key()
            key_id = "key_default_admin"
            self._api_keys[key_id] = {
                "id": key_id,
                "tenant_id": tenant_id,
                "user_id": admin_id,
                "name": "Default Production CLI Key",
                "key_prefix": prefix,
                "hashed_key": key_hash,
                "scopes": ["read", "write", "admin"],
                "rate_limit_per_minute": 600,
                "usage_count": 0,
                "last_used_at": None,
                "created_at": datetime.now(UTC),
                "is_active": True,
            }
            self._api_keys_by_hash[key_hash] = key_id

    def create_tenant(self, name: str, plan_tier: PlanTier = PlanTier.FREE) -> TenantResponse:
        """Provision a new tenant workspace."""
        tenant_id = f"ten_{uuid.uuid4().hex[:12]}"
        slug = name.lower().replace(" ", "-").replace("_", "-")[:30]

        t_data = {
            "id": tenant_id,
            "name": name,
            "slug": slug,
            "plan_tier": plan_tier,
            "created_at": datetime.now(UTC),
            "members": {},
        }
        self._tenants[tenant_id] = t_data
        return self._to_tenant_response(t_data)

    def register_user(
        self,
        email: str,
        password: str,
        full_name: str,
        workspace_name: str = "",
    ) -> tuple[UserProfileResponse, TenantResponse]:
        """
        Register a new user, create their dedicated workspace, and make them ADMIN.
        """
        lower_email = email.lower().strip()
        if lower_email in self._users_by_email:
            raise ValueError(f"User with email '{email}' already exists.")

        ws_name = workspace_name.strip() or f"{full_name}'s Workspace"
        tenant_resp = self.create_tenant(name=ws_name, plan_tier=PlanTier.FREE)
        tenant_id = tenant_resp.tenant_id

        user_id = f"usr_{uuid.uuid4().hex[:12]}"
        hashed = hash_password(password)

        user_data = {
            "id": user_id,
            "email": lower_email,
            "hashed_password": hashed,
            "full_name": full_name,
            "tenant_id": tenant_id,
            "role": UserRole.ADMIN,
            "created_at": datetime.now(UTC),
            "is_active": True,
        }

        self._users[user_id] = user_data
        self._users_by_email[lower_email] = user_id

        # Add to tenant members
        self._tenants[tenant_id]["members"][user_id] = {
            "user_id": user_id,
            "role": UserRole.ADMIN,
            "is_active": True,
            "joined_at": datetime.now(UTC),
        }

        return self._to_user_profile(user_data), self._to_tenant_response(self._tenants[tenant_id])

    def authenticate(self, email: str, password: str) -> UserProfileResponse | None:
        """Authenticate user with email and password."""
        lower_email = email.lower().strip()
        user_id = self._users_by_email.get(lower_email)
        if not user_id:
            return None

        user = self._users.get(user_id)
        if not user or not user.get("is_active", True):
            return None

        if not verify_password(password, user["hashed_password"]):
            return None

        return self._to_user_profile(user)

    def get_user_by_id(self, user_id: str) -> UserProfileResponse | None:
        """Retrieve user profile by ID."""
        user = self._users.get(user_id)
        return self._to_user_profile(user) if user else None

    def get_tenant_by_id(self, tenant_id: str) -> TenantResponse | None:
        """Retrieve tenant details and member list."""
        t = self._tenants.get(tenant_id)
        return self._to_tenant_response(t) if t else None

    def invite_member(
        self,
        tenant_id: str,
        email: str,
        full_name: str,
        role: UserRole = UserRole.MEMBER,
    ) -> TenantMemberItem:
        """Invite a team member into a tenant workspace."""
        t = self._tenants.get(tenant_id)
        if not t:
            raise KeyError(f"Tenant '{tenant_id}' not found.")

        plan: PlanTier = t["plan_tier"]
        if len(t["members"]) >= plan.max_seats:
            raise ValueError(
                f"Workspace seat limit reached ({len(t['members'])}/{plan.max_seats}). Upgrade plan to add more seats."
            )

        lower_email = email.lower().strip()
        user_id = self._users_by_email.get(lower_email)

        if not user_id:
            user_id = f"usr_{uuid.uuid4().hex[:12]}"
            self._users[user_id] = {
                "id": user_id,
                "email": lower_email,
                "hashed_password": hash_password(secrets.token_urlsafe(12)),
                "full_name": full_name,
                "tenant_id": tenant_id,
                "role": role,
                "created_at": datetime.now(UTC),
                "is_active": True,
            }
            self._users_by_email[lower_email] = user_id

        now_dt = datetime.now(UTC)
        member_record = {
            "user_id": user_id,
            "role": role,
            "is_active": True,
            "joined_at": now_dt,
        }
        t["members"][user_id] = member_record

        return TenantMemberItem(
            user_id=user_id,
            email=lower_email,
            full_name=full_name,
            role=role,
            is_active=True,
            joined_at=now_dt,
        )

    def update_member(
        self,
        tenant_id: str,
        user_id: str,
        role: UserRole | None = None,
        is_active: bool | None = None,
    ) -> TenantMemberItem | None:
        """Update a workspace member's role or status."""
        t = self._tenants.get(tenant_id)
        if not t or user_id not in t["members"]:
            return None

        m = t["members"][user_id]
        if role is not None:
            m["role"] = role
        if is_active is not None:
            m["is_active"] = is_active

        user = self._users.get(user_id, {})
        joined_at_val = (
            m["joined_at"] if isinstance(m.get("joined_at"), datetime) else datetime.now(UTC)
        )
        return TenantMemberItem(
            user_id=user_id,
            email=user.get("email", ""),
            full_name=user.get("full_name", ""),
            role=m["role"],
            is_active=m["is_active"],
            joined_at=joined_at_val,
        )

    def create_api_key(
        self,
        tenant_id: str,
        user_id: str,
        name: str,
        scopes: list[str] | None = None,
        rate_limit: int | None = None,
    ) -> ApiKeyCreatedResponse:
        """Issue and persist a new API key."""
        t = self._tenants.get(tenant_id)
        if not t:
            raise KeyError(f"Tenant '{tenant_id}' not found.")

        plan: PlanTier = t["plan_tier"]
        default_rate = rate_limit or plan.rate_limit_per_minute

        raw_key, prefix, key_hash = generate_api_key()
        key_id = f"key_{uuid.uuid4().hex[:10]}"

        key_data = {
            "id": key_id,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "name": name,
            "key_prefix": prefix,
            "hashed_key": key_hash,
            "scopes": scopes or ["read", "write"],
            "rate_limit_per_minute": default_rate,
            "usage_count": 0,
            "last_used_at": None,
            "created_at": datetime.now(UTC),
            "is_active": True,
        }

        self._api_keys[key_id] = key_data
        self._api_keys_by_hash[key_hash] = key_id

        api_key_resp = self._to_api_key_response(key_data)
        return ApiKeyCreatedResponse(api_key=api_key_resp, raw_secret_key=raw_key)

    def list_api_keys(self, tenant_id: str) -> list[ApiKeyResponse]:
        """List all API keys for a tenant."""
        keys = [k for k in self._api_keys.values() if k["tenant_id"] == tenant_id]
        return [self._to_api_key_response(k) for k in keys]

    def revoke_api_key(self, tenant_id: str, key_id: str) -> bool:
        """Deactivate an API key."""
        k = self._api_keys.get(key_id)
        if k and k["tenant_id"] == tenant_id:
            k["is_active"] = False
            return True
        return False

    def lookup_api_key(self, raw_key: str) -> tuple[TenantResponse, ApiKeyResponse] | None:
        """Lookup active API key by plaintext token."""
        key_hash = hash_api_key(raw_key)
        key_id = self._api_keys_by_hash.get(key_hash)
        if not key_id:
            return None

        key_data = self._api_keys.get(key_id)
        if not key_data or not key_data.get("is_active", True):
            return None

        # Update telemetry
        key_data["usage_count"] += 1
        key_data["last_used_at"] = datetime.now(UTC)

        tenant = self.get_tenant_by_id(key_data["tenant_id"])
        if not tenant:
            return None

        return tenant, self._to_api_key_response(key_data)

    def _to_user_profile(self, u: dict) -> UserProfileResponse:
        t = self._tenants.get(u["tenant_id"], {})
        return UserProfileResponse(
            user_id=u["id"],
            email=u["email"],
            full_name=u["full_name"],
            role=u["role"],
            tenant_id=u["tenant_id"],
            workspace_name=t.get("name", "Workspace"),
            plan_tier=t.get("plan_tier", PlanTier.FREE),
            created_at=u["created_at"],
        )

    def _to_tenant_response(self, t: dict) -> TenantResponse:
        plan: PlanTier = t.get("plan_tier", PlanTier.FREE)
        members_list: list[TenantMemberItem] = []

        for uid, m in t.get("members", {}).items():
            user = self._users.get(uid, {})
            j_at = m["joined_at"] if isinstance(m.get("joined_at"), datetime) else t["created_at"]
            members_list.append(
                TenantMemberItem(
                    user_id=uid,
                    email=user.get("email", ""),
                    full_name=user.get("full_name", "Team Member"),
                    role=m.get("role", UserRole.MEMBER),
                    is_active=m.get("is_active", True),
                    joined_at=j_at,
                )
            )

        return TenantResponse(
            tenant_id=t["id"],
            name=t["name"],
            slug=t["slug"],
            plan_tier=plan,
            seats_used=len(members_list),
            max_seats=plan.max_seats,
            monthly_quota_used=0,
            monthly_quota_total=plan.monthly_request_quota,
            rate_limit_per_minute=plan.rate_limit_per_minute,
            created_at=t["created_at"],
            members=members_list,
        )

    def _to_api_key_response(self, k: dict) -> ApiKeyResponse:
        return ApiKeyResponse(
            id=k["id"],
            name=k["name"],
            key_prefix=k["key_prefix"],
            tenant_id=k["tenant_id"],
            created_by_user_id=k["user_id"],
            scopes=k["scopes"],
            rate_limit_per_minute=k["rate_limit_per_minute"],
            usage_count=k["usage_count"],
            last_used_at=k["last_used_at"],
            created_at=k["created_at"],
            is_active=k["is_active"],
        )


# Global Singleton Store
GLOBAL_TENANT_STORE = MultiTenantStore()
