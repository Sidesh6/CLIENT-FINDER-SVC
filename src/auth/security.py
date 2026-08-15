"""
Cryptographic Security Engine: PBKDF2 Password Hashing, JWT Bearer Tokens, and API Key Generation.
"""

import hashlib
import hmac
import json
import os
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from src.auth.schemas import UserRole

# Secret signing key (in production, read from SECRET_KEY environment variable)
JWT_SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY", "client_finder_svc_super_secret_jwt_key_98234710923840912"
)
JWT_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    """
    Hash a plaintext password using PBKDF2-HMAC-SHA256 with 100,000 iterations and a 16-byte salt.
    """
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
    return f"pbkdf2:sha256:100000${salt}${key.hex()}"


def verify_password(password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against a stored PBKDF2 hash using constant-time comparison.
    """
    if not hashed_password or "$" not in hashed_password:
        return False

    try:
        algorithm, salt, stored_hash = hashed_password.split("$")
        key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
        return hmac.compare_digest(key.hex(), stored_hash)
    except Exception:
        return False


def _base64url_encode(data: bytes) -> str:
    """Base64url encode without padding."""
    import base64

    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _base64url_decode(data_str: str) -> bytes:
    """Base64url decode with padding restoration."""
    import base64

    padding = 4 - (len(data_str) % 4)
    if padding and padding != 4:
        data_str += "=" * padding
    return base64.urlsafe_b64decode(data_str)


def create_access_token(
    user_id: str,
    tenant_id: str,
    role: UserRole,
    expires_in_seconds: int = 86400,
) -> str:
    """
    Generate a signed HMAC-SHA256 JWT access token.
    """
    header = {"alg": JWT_ALGORITHM, "typ": "JWT"}
    now = datetime.now(UTC)
    exp = now + timedelta(seconds=expires_in_seconds)

    payload = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "role": role.value,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }

    header_b64 = _base64url_encode(json.dumps(header).encode("utf-8"))
    payload_b64 = _base64url_encode(json.dumps(payload).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")

    signature = hmac.new(JWT_SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    sig_b64 = _base64url_encode(signature)

    return f"{header_b64}.{payload_b64}.{sig_b64}"


def decode_access_token(token: str) -> dict[str, Any] | None:
    """
    Decode and verify a signed JWT token. Returns payload claims or None if invalid/expired.
    """
    if not token or token.count(".") != 2:
        return None

    try:
        header_b64, payload_b64, sig_b64 = token.split(".")
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")

        # Verify signature
        expected_sig = hmac.new(
            JWT_SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256
        ).digest()
        actual_sig = _base64url_decode(sig_b64)

        if not hmac.compare_digest(expected_sig, actual_sig):
            return None

        payload_bytes = _base64url_decode(payload_b64)
        payload: dict[str, Any] = json.loads(payload_bytes.decode("utf-8"))

        # Verify expiration
        exp = payload.get("exp")
        if exp and exp < datetime.now(UTC).timestamp():
            return None

        return dict(payload)
    except Exception:
        return None


def generate_api_key() -> tuple[str, str, str]:
    """
    Issue a new programmatic API key.
    Returns: (raw_secret_key, key_prefix, hashed_key)
    Format: cf_live_<8-char-prefix>_<32-char-random-secret>
    """
    prefix = secrets.token_hex(4)  # 8 hex chars
    secret = secrets.token_urlsafe(24)
    raw_key = f"cf_live_{prefix}_{secret}"
    hashed_key = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
    return raw_key, f"cf_live_{prefix}", hashed_key


def hash_api_key(raw_key: str) -> str:
    """Compute SHA-256 hash of an API key for storage or lookup."""
    return hashlib.sha256(raw_key.strip().encode("utf-8")).hexdigest()
