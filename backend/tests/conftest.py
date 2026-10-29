import json
from pathlib import Path

import pytest

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
