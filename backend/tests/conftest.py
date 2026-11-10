import json
import os
from pathlib import Path

import pytest

# main.py reads these at import. The database engine connects lazily, so unit
# tests never touch Postgres; integration tests run against the real stack.
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://test:test@localhost:5432/test")
os.environ.setdefault("JWT_PRIVATE_KEY_PATH", "unused-private.pem")
os.environ.setdefault("JWT_PUBLIC_KEY_PATH", "unused-public.pem")
# Set before main.py loads .env, so tests can never use (and spend) the real key.
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-real")

FIXTURES = Path(__file__).parent / "fixtures"


def load(name):
    return json.loads((FIXTURES / f"{name}.json").read_text())


@pytest.fixture
def full_resume():
    return load("full_resume")


@pytest.fixture
def minimal_resume():
    return load("minimal_resume")


@pytest.fixture
def malicious_resume():
    return load("malicious_resume")
