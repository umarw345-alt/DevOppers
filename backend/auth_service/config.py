from dataclasses import dataclass
import os
from pathlib import Path


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value is not None else default


@dataclass(frozen=True)
class Settings:
    database_url: str
    jwt_private_key_path: Path
    jwt_public_key_path: Path
    jwt_issuer: str
    jwt_audience: str
    access_token_ttl_minutes: int
    refresh_token_ttl_days: int
    afk_timeout_minutes: int
    login_rate_limit: int
    login_rate_window_seconds: int
    argon2_memory_cost: int
    argon2_time_cost: int
    argon2_parallelism: int
    argon2_hash_length: int
    argon2_salt_length: int


def load_settings() -> Settings:
    return Settings(
        database_url=os.environ["DATABASE_URL"],
        jwt_private_key_path=Path(os.environ["JWT_PRIVATE_KEY_PATH"]),
        jwt_public_key_path=Path(os.environ["JWT_PUBLIC_KEY_PATH"]),
        jwt_issuer=os.getenv("JWT_ISSUER", "login-authenticator"),
        jwt_audience=os.getenv("JWT_AUDIENCE", "login-authenticator-client"),
        access_token_ttl_minutes=_int_env("ACCESS_TOKEN_TTL_MINUTES", 15),
        refresh_token_ttl_days=_int_env("REFRESH_TOKEN_TTL_DAYS", 1),
        afk_timeout_minutes=_int_env("AFK_TIMEOUT_MINUTES", 30),
        login_rate_limit=_int_env("LOGIN_RATE_LIMIT", 5),
        login_rate_window_seconds=_int_env("LOGIN_RATE_WINDOW_SECONDS", 300),
        argon2_memory_cost=_int_env("ARGON2_MEMORY_COST", 65536),
        argon2_time_cost=_int_env("ARGON2_TIME_COST", 3),
        argon2_parallelism=_int_env("ARGON2_PARALLELISM", 4),
        argon2_hash_length=_int_env("ARGON2_HASH_LENGTH", 32),
        argon2_salt_length=_int_env("ARGON2_SALT_LENGTH", 16),
    )
