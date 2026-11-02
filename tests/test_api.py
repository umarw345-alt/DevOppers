from uuid import UUID

from fastapi.testclient import TestClient

from upload.main import app


client = TestClient(app)
USER_ID = "00000000-0000-0000-0000-000000000001"


def test_health_check() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_get_missing_resume() -> None:
    response = client.get(
        "/resume",
        headers={"X-User-ID": USER_ID},
    )

    assert response.status_code == 404
