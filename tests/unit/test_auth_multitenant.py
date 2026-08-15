"""
Unit & Integration Tests for Multi-Tenant SaaS Workspace, Team RBAC, API Key Quotas, and JWT Authentication.
"""

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.auth.metering import TenantQuotaMeter
from src.auth.schemas import PlanTier, UserRole
from src.auth.security import (
    create_access_token,
    decode_access_token,
    generate_api_key,
    hash_api_key,
    hash_password,
    verify_password,
)
from src.auth.store import MultiTenantStore


@pytest.fixture
def client():
    return TestClient(app)


class TestPasswordAndJwtSecurity:
    """Tests for PBKDF2 password hashing, salt randomness, and JWT tokens."""

    def test_password_hashing_and_verification(self):
        pwd = "SuperSecretSecurePass123!"
        hashed = hash_password(pwd)

        assert hashed.startswith("pbkdf2:sha256:100000$")
        assert verify_password(pwd, hashed) is True
        assert verify_password("WrongPassword!", hashed) is False

    def test_jwt_creation_and_decoding(self):
        token = create_access_token(
            user_id="usr_test123",
            tenant_id="ten_test456",
            role=UserRole.ADMIN,
            expires_in_seconds=3600,
        )
        assert isinstance(token, str)
        assert token.count(".") == 2

        claims = decode_access_token(token)
        assert claims is not None
        assert claims["sub"] == "usr_test123"
        assert claims["tenant_id"] == "ten_test456"
        assert claims["role"] == "ADMIN"

    def test_expired_or_tampered_jwt_rejected(self):
        # Expired token
        expired_token = create_access_token(
            user_id="usr_expired",
            tenant_id="ten_test",
            role=UserRole.MEMBER,
            expires_in_seconds=-10,
        )
        assert decode_access_token(expired_token) is None

        # Tampered token
        tampered_token = expired_token[:-4] + "abcd"
        assert decode_access_token(tampered_token) is None

    def test_api_key_generation_and_hashing(self):
        raw_key, prefix, key_hash = generate_api_key()

        assert raw_key.startswith("cf_live_")
        assert prefix.startswith("cf_live_")
        assert len(key_hash) == 64
        assert hash_api_key(raw_key) == key_hash


class TestMultiTenantStore:
    """Tests for MultiTenantStore workspace isolation, user registration, and team memberships."""

    def test_bootstrap_default_tenant(self):
        store = MultiTenantStore()
        tenant = store.get_tenant_by_id("default_tenant")
        assert tenant is not None
        assert tenant.plan_tier == PlanTier.PRO
        assert tenant.seats_used >= 1

        admin = store.get_user_by_id("default_admin")
        assert admin is not None
        assert admin.role == UserRole.ADMIN

    def test_register_user_creates_isolated_workspace(self):
        store = MultiTenantStore()
        user, tenant = store.register_user(
            email="founder@agency.io",
            password="SecurePassword456!",
            full_name="Founder Name",
            workspace_name="Elite AI Agency",
        )

        assert user.email == "founder@agency.io"
        assert user.role == UserRole.ADMIN
        assert tenant.name == "Elite AI Agency"
        assert tenant.plan_tier == PlanTier.FREE

        # Verify authentication
        auth_user = store.authenticate("founder@agency.io", "SecurePassword456!")
        assert auth_user is not None
        assert auth_user.user_id == user.user_id

    def test_invite_member_and_seat_limits(self):
        store = MultiTenantStore()
        tenant = store.create_tenant(name="Small Team", plan_tier=PlanTier.FREE)
        assert tenant.max_seats == 1

        # First member succeeds
        m1 = store.invite_member(tenant.tenant_id, "dev1@small.com", "Dev One", UserRole.MEMBER)
        assert m1.role == UserRole.MEMBER

        # Second member exceeds seat limit for FREE plan
        with pytest.raises(ValueError, match="seat limit reached"):
            store.invite_member(tenant.tenant_id, "dev2@small.com", "Dev Two", UserRole.READONLY)

    def test_api_key_lifecycle(self):
        store = MultiTenantStore()
        created = store.create_api_key(
            tenant_id="default_tenant",
            user_id="default_admin",
            name="CI/CD Deploy Key",
            scopes=["read", "write"],
        )

        assert created.api_key.name == "CI/CD Deploy Key"
        assert created.raw_secret_key.startswith("cf_live_")

        # Lookup by secret key
        lookup = store.lookup_api_key(created.raw_secret_key)
        assert lookup is not None
        t, k = lookup
        assert t.tenant_id == "default_tenant"
        assert k.usage_count == 1

        # Revoke key
        revoked = store.revoke_api_key("default_tenant", created.api_key.id)
        assert revoked is True

        lookup_revoked = store.lookup_api_key(created.raw_secret_key)
        assert lookup_revoked is None


class TestTenantQuotaMeter:
    """Tests for sliding-window rate limiting and monthly quota tracking."""

    def test_minute_rate_limiting(self):
        meter = TenantQuotaMeter()
        tenant_id = "ten_rate_test"

        # Plan FREE allows 30 req/min
        allowed, telem, headers = meter.check_and_consume(
            tenant_id=tenant_id,
            plan_tier=PlanTier.FREE,
            tokens=30,
        )
        assert allowed is True
        assert telem.current_minute_requests == 30

        # 31st request is throttled
        throttled, telem_throt, _ = meter.check_and_consume(
            tenant_id=tenant_id,
            plan_tier=PlanTier.FREE,
            tokens=1,
        )
        assert throttled is False
        assert telem_throt.is_throttled is True

    def test_monthly_quota_consumption(self):
        meter = TenantQuotaMeter()
        tenant_id = "ten_quota_test"

        # Simulate 250 requests consumed this month
        meter._monthly_counts[tenant_id] = 250
        status = meter.get_quota_status(tenant_id, plan_tier=PlanTier.FREE)
        assert status.requests_this_month == 250
        assert status.quota_percent_consumed == 100.0

        # Exceeding monthly cap
        exhausted, telem_exhaust, _ = meter.check_and_consume(
            tenant_id=tenant_id,
            plan_tier=PlanTier.FREE,
            tokens=1,
        )
        assert exhausted is False
        assert telem_exhaust.is_throttled is True


class TestAuthAndTenantApiEndpoints:
    """Integration tests for /api/auth/..., /api/tenants/..., and /api/apikeys/... REST endpoints."""

    def test_register_login_and_me_lifecycle(self, client: TestClient):
        email = "test_user_unique@example.com"
        reg_payload = {
            "email": email,
            "password": "Password12345!",
            "full_name": "Test User",
            "workspace_name": "Test Cloud Workspace",
        }
        res_reg = client.post("/api/auth/register", json=reg_payload)
        assert res_reg.status_code == 201
        data_reg = res_reg.json()
        assert "access_token" in data_reg
        token = data_reg["access_token"]

        # 1. Login with credentials
        login_payload = {"email": email, "password": "Password12345!"}
        res_login = client.post("/api/auth/login", json=login_payload)
        assert res_login.status_code == 200
        assert "access_token" in res_login.json()

        # 2. Get profile with JWT
        headers = {"Authorization": f"Bearer {token}"}
        res_me = client.get("/api/auth/me", headers=headers)
        assert res_me.status_code == 200
        data_me = res_me.json()
        assert data_me["email"] == email
        assert data_me["role"] == "ADMIN"
        assert data_me["workspace_name"] == "Test Cloud Workspace"

    def test_tenant_workspace_and_quota_routes(self, client: TestClient):
        # Uses default admin in dev mode
        res_curr = client.get("/api/tenants/current")
        assert res_curr.status_code == 200
        data_curr = res_curr.json()
        assert data_curr["tenant_id"] == "default_tenant"
        assert len(data_curr["members"]) >= 1

        res_quota = client.get("/api/tenants/quota")
        assert res_quota.status_code == 200
        data_quota = res_quota.json()
        assert data_quota["monthly_quota_limit"] == 25000  # PRO tier

    def test_api_keys_crud_routes(self, client: TestClient):
        # 1. Create API key
        key_payload = {"name": "Test Integration Key", "scopes": ["read", "write"]}
        res_create = client.post("/api/apikeys", json=key_payload)
        assert res_create.status_code == 201
        data_key = res_create.json()
        raw_key = data_key["raw_secret_key"]
        key_id = data_key["api_key"]["id"]
        assert raw_key.startswith("cf_live_")

        # 2. List API keys
        res_list = client.get("/api/apikeys")
        assert res_list.status_code == 200
        assert any(k["id"] == key_id for k in res_list.json())

        # 3. Authenticate with X-API-Key header
        res_me_apikey = client.get("/api/auth/me", headers={"X-API-Key": raw_key})
        assert res_me_apikey.status_code == 200

        # 4. Revoke API key
        res_del = client.delete(f"/api/apikeys/{key_id}")
        assert res_del.status_code == 204
