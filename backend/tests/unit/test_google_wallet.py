import json
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from main import app
from portfolio import google_wallet, routes

ISSUER = "3388000000012345678"


@pytest.fixture
def service_account(tmp_path, monkeypatch):
    """A fake service-account key file, like the JSON Google Cloud gives you."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
    path = tmp_path / "google-wallet.json"
    path.write_text(json.dumps({"type": "service_account", "client_email": "wallet@demo.iam.gserviceaccount.com", "private_key": pem}))
    monkeypatch.setenv("GOOGLE_WALLET_ISSUER_ID", ISSUER)
    monkeypatch.setenv("GOOGLE_WALLET_KEY_PATH", str(path))
    google_wallet.credentials.cache_clear()
    yield key.public_key()
    google_wallet.credentials.cache_clear()


def decode(save_url: str, public_key) -> dict:
    assert save_url.startswith("https://pay.google.com/gp/v/save/")
    token = save_url.removeprefix("https://pay.google.com/gp/v/save/")
    return jwt.decode(token, public_key, algorithms=["RS256"], audience="google")


def test_save_link_is_signed_and_its_qr_code_opens_the_portfolio(service_account):
    url = google_wallet.build_save_url(
        slug="jordan-lee", name="Jordan Lee", headline="CS Student", url="https://devoppers.vercel.app/jordan-lee",
        color="#1e3a8a", logo_url="https://devoppers.vercel.app/google-wallet-logo.png",
    )
    claims = decode(url, service_account)

    assert claims["iss"] == "wallet@demo.iam.gserviceaccount.com"
    assert claims["typ"] == "savetowallet"
    assert claims["payload"]["genericClasses"] == [{"id": f"{ISSUER}.portable_resume"}]
    [card] = claims["payload"]["genericObjects"]
    assert card["id"] == f"{ISSUER}.jordan-lee"
    assert card["classId"] == f"{ISSUER}.portable_resume"
    assert card["header"]["defaultValue"]["value"] == "Jordan Lee"
    assert card["subheader"]["defaultValue"]["value"] == "CS Student"
    assert card["hexBackgroundColor"] == "#1e3a8a"
    assert card["barcode"] == {"type": "QR_CODE", "value": "https://devoppers.vercel.app/jordan-lee", "alternateText": "Scan for my portfolio"}
    assert card["logo"]["sourceUri"]["uri"] == "https://devoppers.vercel.app/google-wallet-logo.png"


def test_optional_fields_are_left_off(service_account):
    url = google_wallet.build_save_url(slug="sam", name="Sam", headline=None, url="http://localhost:8000/sam", color="#000000", logo_url=None)
    [card] = decode(url, service_account)["payload"]["genericObjects"]
    assert "subheader" not in card
    assert "logo" not in card


def test_missing_setup_is_a_clear_error(monkeypatch):
    monkeypatch.delenv("GOOGLE_WALLET_ISSUER_ID", raising=False)
    google_wallet.credentials.cache_clear()
    with pytest.raises(google_wallet.GoogleWalletError, match="isn't set up"):
        google_wallet.build_save_url(slug="sam", name="Sam", headline=None, url="http://x/sam", color="#000000", logo_url=None)


def portfolio(resume):
    return SimpleNamespace(resume_record=SimpleNamespace(resume_json=resume), template_id="modern", theme_json={})


def test_route_redirects_to_google_with_this_sites_links(service_account, full_resume, monkeypatch):
    monkeypatch.delenv("PUBLIC_BASE_URL", raising=False)
    monkeypatch.setattr(routes, "find", lambda request, slug: portfolio(full_resume))
    client = TestClient(app, base_url="https://devoppers.vercel.app")

    response = client.get("/jordan-lee/google-wallet", follow_redirects=False)

    assert response.status_code == 303
    [card] = decode(response.headers["location"], service_account)["payload"]["genericObjects"]
    assert card["barcode"]["value"] == "https://devoppers.vercel.app/jordan-lee"
    assert card["logo"]["sourceUri"]["uri"] == "https://devoppers.vercel.app/google-wallet-logo.png"


def test_route_leaves_the_logo_off_without_https(service_account, full_resume, monkeypatch):
    monkeypatch.delenv("PUBLIC_BASE_URL", raising=False)
    monkeypatch.setattr(routes, "find", lambda request, slug: portfolio(full_resume))

    response = TestClient(app).get("/jordan-lee/google-wallet", follow_redirects=False)

    [card] = decode(response.headers["location"], service_account)["payload"]["genericObjects"]
    assert "logo" not in card


def test_route_without_setup_answers_503(full_resume, monkeypatch):
    monkeypatch.delenv("GOOGLE_WALLET_ISSUER_ID", raising=False)
    google_wallet.credentials.cache_clear()
    monkeypatch.setattr(routes, "find", lambda request, slug: portfolio(full_resume))

    response = TestClient(app).get("/jordan-lee/google-wallet", follow_redirects=False)

    assert response.status_code == 503
    assert "isn't set up" in response.json()["detail"]


def test_logo_is_served_publicly():
    response = TestClient(app).get("/google-wallet-logo.png")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
