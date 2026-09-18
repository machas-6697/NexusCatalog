"""
app/core/security.py
─────────────────────────────────────────────────────────────
JWT encode/decode and password hashing utilities.

NOTE: Using the `bcrypt` library directly (not via passlib)
because passlib's bcrypt integration is broken with bcrypt 5.x
(missing __about__ attribute). Direct bcrypt usage is simpler
and fully supported.

- hash_password()   : bcrypt hash a plaintext password
- verify_password() : compare plaintext against stored hash
- create_token()    : sign a JWT with user/tenant/role claims
- decode_token()    : validate signature + expiry, return payload
"""

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from app.config import settings

# Pre-computed bcrypt hash used for constant-time login when email is unknown
_DUMMY_PASSWORD_HASH = (
    "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYIz.AWMRi"
)


# ── Password hashing (bcrypt direct) ─────────────────────────

def hash_password(plaintext: str) -> str:
    """Returns a bcrypt hash of the given plaintext password."""
    password_bytes = plaintext.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plaintext: str, hashed: str) -> bool:
    """Returns True if plaintext matches the stored bcrypt hash."""
    password_bytes = plaintext.encode("utf-8")
    hashed_bytes = hashed.encode("utf-8")
    return bcrypt.checkpw(password_bytes, hashed_bytes)


# ── JWT ───────────────────────────────────────────────────────

def create_token(
    user_id: str,
    tenant_id: str,
    role: str,
    email: str = "",
) -> tuple[str, int]:
    """
    Creates and signs a JWT access token.

    Returns:
        (encoded_token, expires_in_seconds)
    """
    expiry_seconds = settings.jwt_expiry_hours * 3600
    expire = datetime.now(timezone.utc) + timedelta(seconds=expiry_seconds)

    payload: dict[str, Any] = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "role": role,
        "email": email,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }

    encoded = jwt.encode(
        payload,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    return encoded, expiry_seconds


def decode_token(token: str) -> dict[str, Any]:
    """
    Decodes and validates a JWT token.

    Returns the payload dict on success.
    Raises jwt.InvalidTokenError (or subclass) on failure —
    callers should catch this and return 401.
    """
    return jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
    )
