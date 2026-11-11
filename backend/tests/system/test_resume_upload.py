"""POST /resume/upload with a fake Claude client and a fake logged-in user (no API calls, no database)."""

from types import SimpleNamespace
from uuid import uuid4

import anthropic
import httpx2
import pytest
from fastapi.testclient import TestClient

from auth_service.fastapi_routes import access_identity
from auth_service.rate_limit import LoginRateLimiter
from main import app
from portfolio.schema import Resume
from resume.routes import get_anthropic_client

PDF = b"%PDF-1.7\n fake pdf body"
JPEG = b"\xff\xd8\xff\xe0 fake jpeg body"
PNG = b"\x89PNG\r\n\x1a\n fake png body"


class FakeMessages:
    def __init__(self):
        self.calls = []
        self.response = None
        self.error = None

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.response


def reply(resume, stop_reason="end_turn"):
    return SimpleNamespace(
        stop_reason=stop_reason,
        parsed_output=resume if stop_reason == "end_turn" else None,
        model="claude-haiku-5-5",
        usage=SimpleNamespace(input_tokens=4600, output_tokens=1000),
    )


@pytest.fixture
def fake(full_resume):
    messages = FakeMessages()
    messages.response = reply(Resume.model_validate(full_resume))
    app.dependency_overrides[access_identity] = lambda: (uuid4(), uuid4())
    app.dependency_overrides[get_anthropic_client] = lambda: SimpleNamespace(messages=messages)
    app.state.upload_rate_limiter = LoginRateLimiter(10, 600)
    yield messages
    app.dependency_overrides.clear()


client = TestClient(app)


def upload(data, name="resume.pdf", content_type="application/pdf"):
    return client.post("/resume/upload", files={"file": (name, data, content_type)})


def test_requires_login():
    response = upload(PDF)
    assert response.status_code == 401


@pytest.mark.parametrize("data, mime", [(PDF, "application/pdf"), (JPEG, "image/jpeg"), (PNG, "image/png")])
def test_returns_extracted_resume(fake, data, mime):
    response = upload(data)
    assert response.status_code == 200
    assert response.json()["contact"]["name"] == "Jordan Lee"
    # The type sent to Claude comes from the file's bytes, not the client's content type.
    block = fake.calls[0]["messages"][0]["content"][0]
    assert block["source"]["media_type"] == mime


def test_uses_haiku_with_resume_schema(fake):
    upload(PDF)
    call = fake.calls[0]
    assert call["model"] == "claude-haiku-5-5"
    assert call["output_format"] is Resume


def test_empty_file(fake):
    assert upload(b"").status_code == 400


def test_file_over_10_mb(fake):
    assert upload(b"%PDF" + b"0" * (10 * 1024 * 1024)).status_code == 413
    assert fake.calls == []


def test_not_a_resume_file(fake):
    response = upload(b"just some text", name="resume.pdf")
    assert response.status_code == 415
    assert fake.calls == []


@pytest.mark.parametrize("stop_reason", ["refusal", "max_tokens"])
def test_unusable_model_reply(fake, full_resume, stop_reason):
    fake.response = reply(Resume.model_validate(full_resume), stop_reason=stop_reason)
    response = upload(PDF)
    assert response.status_code == 422
    assert response.json()["detail"].startswith("Couldn't read that resume")


def test_unreadable_file_reported_by_api(fake):
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    fake.error = anthropic.BadRequestError("bad pdf", response=httpx2.Response(400, request=request), body=None)
    assert upload(PDF).status_code == 422


def test_api_unavailable(fake):
    fake.error = anthropic.APIConnectionError(request=httpx2.Request("POST", "https://api.anthropic.com/v1/messages"))
    assert upload(PDF).status_code == 503


def test_no_api_key_configured(fake, monkeypatch):
    del app.dependency_overrides[get_anthropic_client]
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    response = upload(PDF)
    assert response.status_code == 503
    assert "isn't set up" in response.json()["detail"]


def test_rate_limited_per_user(fake):
    user = (uuid4(), uuid4())
    app.dependency_overrides[access_identity] = lambda: user
    statuses = [upload(PDF).status_code for _ in range(11)]
    assert statuses[:10] == [200] * 10
    assert statuses[10] == 429
