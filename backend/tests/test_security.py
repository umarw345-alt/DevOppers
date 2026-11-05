from pathlib import Path
from uuid import uuid4

from backend.auth_service.config import Settings
from backend.auth_service.security import (
    build_password_hasher,
    hash_refresh_token,
    new_refresh_token,
)


def settings() -> Settings:
    return Settings(
        database_url="postgresql+psycopg://unused",
        jwt_private_key_path=Path("unused-private.pem"),
        jwt_public_key_path=Path("unused-public.pem"),
        jwt_issuer="issuer",
        jwt_audience="audience",
        access_token_ttl_minutes=15,
        refresh_token_ttl_days=1,
        afk_timeout_minutes=30,
        login_rate_limit=5,
        login_rate_window_seconds=300,
        argon2_memory_cost=8192,
        argon2_time_cost=1,
        argon2_parallelism=1,
        argon2_hash_length=16,
        argon2_salt_length=16,
    )


def test_argon2id_hash_verifies_without_exposing_password():
    password = "correct horse battery staple"
    hashed = build_password_hasher(settings()).hash(password)

    assert hashed.startswith("$argon2id$")
    assert build_password_hasher(settings()).verify(hashed, password)
    assert password not in hashed


def test_refresh_tokens_are_random_and_only_hashes_are_persisted():
    first = new_refresh_token()
    second = new_refresh_token()

    assert first != second
    assert hash_refresh_token(first) != first
    assert hash_refresh_token(first) != hash_refresh_token(second)


def test_refresh_token_hash_is_deterministic():
    token = str(uuid4())

    assert hash_refresh_token(token) == hash_refresh_token(token)
