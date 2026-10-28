from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from uuid import UUID, uuid4

import jwt
from argon2 import PasswordHasher
from argon2.low_level import Type

from .config import Settings


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def build_password_hasher(settings: Settings) -> PasswordHasher:
    return PasswordHasher(
        time_cost=settings.argon2_time_cost,
        memory_cost=settings.argon2_memory_cost,
        parallelism=settings.argon2_parallelism,
        hash_len=settings.argon2_hash_length,
        salt_len=settings.argon2_salt_length,
        type=Type.ID,
    )


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_refresh_token() -> str:
    return secrets.token_urlsafe(64)


def create_access_token(settings: Settings, user_id: UUID, session_id: UUID) -> str:
    now = utc_now()
    claims = {
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "sub": str(user_id),
        "sid": str(session_id),
        "jti": str(uuid4()),
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_ttl_minutes),
        "typ": "access",
    }
    private_key = settings.jwt_private_key_path.read_text(encoding="utf-8")
    return jwt.encode(claims, private_key, algorithm="RS256")


def decode_access_token(settings: Settings, token: str) -> dict:
    public_key = settings.jwt_public_key_path.read_text(encoding="utf-8")
    return jwt.decode(
        token,
        public_key,
        algorithms=["RS256"],
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
        options={"require": ["iss", "aud", "sub", "sid", "jti", "iat", "exp", "typ"]},
    )
