"""Security utilities — JWT handling, API key validation, password hashing."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt
from ...domain.exceptions import AuthenticationError



# ── Password hashing ─────────────────────────────────────────

def hash_password(password: str) -> str:
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    plain_bytes = plain.encode("utf-8")
    hashed_bytes = hashed.encode("utf-8")
    try:
        return bcrypt.checkpw(plain_bytes, hashed_bytes)
    except ValueError:
        return False


# ── JWT ──────────────────────────────────────────────────────
def create_access_token(
    data: dict[str, Any],
    secret_key: str,
    algorithm: str = "HS256",
    expires_minutes: int = 30,
) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, secret_key, algorithm=algorithm)


def create_refresh_token(
    data: dict[str, Any],
    secret_key: str,
    algorithm: str = "HS256",
    expires_days: int = 7,
) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=expires_days)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, secret_key, algorithm=algorithm)


def decode_token(
    token: str,
    secret_key: str,
    algorithm: str = "HS256",
) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        return payload  # type: ignore[no-any-return]
    except JWTError as exc:
        raise AuthenticationError(f"Invalid token: {exc}") from exc


def validate_api_key(provided: str, expected: str) -> bool:
    """Constant-time comparison for API keys."""
    import hmac

    return hmac.compare_digest(provided.encode(), expected.encode())
