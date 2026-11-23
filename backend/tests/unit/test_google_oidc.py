from urllib.parse import parse_qs, urlparse
from pathlib import Path
from types import SimpleNamespace
import time

import jwt
import pytest
from starlette.requests import Request
from fastapi import HTTPException
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption

from auth_service.config import Settings
from auth_service import google_oidc, google_routes
from auth_service.google_oidc import (
    GoogleOIDCError,
    OIDCTransaction,
    authorization_url,
    decode_transaction,
    exchange_code,
    encode_transaction,
    pkce_challenge,
    verify_id_token,
)


def settings() -> Settings:
    return Settings(
        database_url="postgresql+psycopg://test:test@localhost/test",
        jwt_private_key_path=Path("private.pem"),
        jwt_public_key_path=Path("public.pem"),
        jwt_issuer="issuer",
        jwt_audience="audience",
        access_token_ttl_minutes=15,
        refresh_token_ttl_days=1,
        afk_timeout_minutes=30,
        login_rate_limit=5,
        login_rate_window_seconds=300,
        argon2_memory_cost=65536,
        argon2_time_cost=3,
        argon2_parallelism=4,
        argon2_hash_length=32,
        argon2_salt_length=16,
        google_client_id="client-id",
        google_client_secret="client-secret",
        google_oidc_state_secret="s" * 32,
    )


def test_pkce_challenge_is_base64url_without_padding():
    assert "=" not in pkce_challenge("verifier")
    assert pkce_challenge("verifier") == "iMnq5o6zALKXGivsnlom_0F5_WYda32GHkxlV7mq7hQ"


def test_signed_transaction_round_trips_and_tampering_fails():
    transaction = OIDCTransaction("state", "nonce", "verifier")
    signed = encode_transaction(settings(), transaction)

    assert decode_transaction(settings(), signed) == transaction
    with pytest.raises(GoogleOIDCError):
        decode_transaction(settings(), signed + "tampered")


def test_authorization_url_contains_required_security_parameters(monkeypatch):
    monkeypatch.setattr(
        "auth_service.google_oidc.discovery",
        lambda _: {"authorization_endpoint": "https://accounts.google.com/o/oauth2/v2/auth"},
    )
    transaction = OIDCTransaction("state", "nonce", "verifier")

    query = parse_qs(urlparse(authorization_url(settings(), transaction)).query)

    assert query["client_id"] == ["client-id"]
    assert query["response_type"] == ["code"]
    assert query["scope"] == ["openid profile email"]
    assert query["state"] == ["state"]
    assert query["nonce"] == ["nonce"]
    assert query["code_challenge_method"] == ["S256"]
    assert query["code_challenge"] == [pkce_challenge("verifier")]


def test_transaction_cookie_requires_state_secret():
    configuration = settings()
    configuration = configuration.__class__(**{**configuration.__dict__, "google_oidc_state_secret": None})

    with pytest.raises(GoogleOIDCError):
        encode_transaction(configuration, OIDCTransaction("state", "nonce", "verifier"))


def test_exchange_code_sends_pkce_and_returns_id_token(monkeypatch):
    calls = []

    def fake_json_request(method, url, **kwargs):
        calls.append((method, url, kwargs))
        if method == "GET":
            return {
                "authorization_endpoint": "https://accounts.google.com/auth",
                "token_endpoint": "https://oauth2.googleapis.com/token",
                "jwks_uri": "https://www.googleapis.com/oauth2/v3/certs",
            }
        return {"id_token": "google-id-token", "access_token": "unused-google-api-token"}

    monkeypatch.setattr(google_oidc, "_json_request", fake_json_request)
    transaction = OIDCTransaction("state", "nonce", "verifier")

    assert exchange_code(settings(), transaction, "authorization-code") == "google-id-token"
    assert calls[1][0:2] == ("POST", "https://oauth2.googleapis.com/token")
    assert calls[1][2]["data"] == {
        "client_id": "client-id",
        "client_secret": "client-secret",
        "code": "authorization-code",
        "code_verifier": "verifier",
        "grant_type": "authorization_code",
        "redirect_uri": "http://localhost:8000/v1/auth/google/callback",
    }


def test_exchange_code_rejects_response_without_id_token(monkeypatch):
    def fake_json_request(method, url, **kwargs):
        if method == "GET":
            return {
                "authorization_endpoint": "https://accounts.google.com/auth",
                "token_endpoint": "https://oauth2.googleapis.com/token",
                "jwks_uri": "https://www.googleapis.com/oauth2/v3/certs",
            }
        return {"access_token": "unused-google-api-token"}

    monkeypatch.setattr(google_oidc, "_json_request", fake_json_request)

    with pytest.raises(GoogleOIDCError):
        exchange_code(settings(), OIDCTransaction("state", "nonce", "verifier"), "authorization-code")


def _signed_id_token(private_key, transaction, **overrides):
    claims = {
        "iss": "https://accounts.google.com",
        "aud": "client-id",
        "sub": "google-subject-123",
        "email": "person@example.com",
        "email_verified": True,
        "nonce": transaction.nonce,
        "iat": int(time.time()),
        "exp": int(time.time()) + 300,
    }
    claims.update(overrides)
    private_bytes = private_key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
    return jwt.encode(claims, private_bytes, algorithm="RS256")


def _patch_jwks(monkeypatch, private_key):
    class FakeSigningKey:
        key = private_key.public_key()

    class FakeJWKClient:
        def __init__(self, url):
            self.url = url

        def get_signing_key_from_jwt(self, token):
            return FakeSigningKey()

    monkeypatch.setattr(google_oidc.jwt, "PyJWKClient", FakeJWKClient)
    monkeypatch.setattr(
        google_oidc,
        "discovery",
        lambda _: {
            "authorization_endpoint": "https://accounts.google.com/auth",
            "token_endpoint": "https://oauth2.googleapis.com/token",
            "jwks_uri": "https://www.googleapis.com/oauth2/v3/certs",
        },
    )


def test_verify_id_token_accepts_valid_google_claims(monkeypatch):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    transaction = OIDCTransaction("state", "nonce", "verifier")
    _patch_jwks(monkeypatch, private_key)

    claims = verify_id_token(settings(), _signed_id_token(private_key, transaction), transaction)

    assert claims["sub"] == "google-subject-123"
    assert claims["email"] == "person@example.com"


@pytest.mark.parametrize(
    "overrides",
    [
        {"iss": "https://malicious.example"},
        {"aud": "different-client"},
        {"email_verified": False},
        {"nonce": "different-nonce"},
        {"exp": int(time.time()) - 1},
    ],
)
def test_verify_id_token_rejects_invalid_claims(monkeypatch, overrides):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    transaction = OIDCTransaction("state", "nonce", "verifier")
    _patch_jwks(monkeypatch, private_key)

    with pytest.raises(GoogleOIDCError):
        verify_id_token(settings(), _signed_id_token(private_key, transaction, **overrides), transaction)


def _request_with_cookie(app, cookie_value):
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/v1/auth/google/callback",
            "query_string": b"",
            "headers": [(b"cookie", f"google_oidc_transaction={cookie_value}".encode())],
            "app": app,
        }
    )


class FakeDatabase:
    def __init__(self):
        self.added = []
        self.committed = False

    def scalar(self, statement):
        return None

    def get(self, model, identifier):
        return None

    def add(self, value):
        self.added.append(value)

    def flush(self):
        return None

    def commit(self):
        self.committed = True

    def rollback(self):
        return None

    def close(self):
        return None


def test_callback_creates_local_identity_and_issues_application_session(monkeypatch):
    configuration = settings()
    app = SimpleNamespace(state=SimpleNamespace(settings=configuration))
    transaction = OIDCTransaction("state", "nonce", "verifier")
    request = _request_with_cookie(app, encode_transaction(configuration, transaction))
    db = FakeDatabase()
    issued = {}

    monkeypatch.setattr(google_routes, "open_db", lambda _: db)
    monkeypatch.setattr(google_routes, "exchange_code", lambda *_: "google-id-token")
    monkeypatch.setattr(
        google_routes,
        "verify_id_token",
        lambda *_: {"sub": "google-subject-123", "email": "person@example.com", "email_verified": True},
    )
    monkeypatch.setattr(google_routes, "_create_session", lambda *_: (SimpleNamespace(id="session-id"), "refresh"))

    def fake_auth_response(request, response, user, session, refresh_token, web=None):
        issued.update(user=user, session=session, refresh_token=refresh_token, web=web)
        response.set_cookie("app-auth", "issued")

    monkeypatch.setattr(google_routes, "_auth_response", fake_auth_response)

    response = google_routes.google_callback(request, code="authorization-code", state="state")

    assert response.status_code == 303
    assert response.headers["location"] == "http://localhost:8081"
    assert issued["user"].email == "person@example.com"
    assert issued["user"].password_hash is None
    assert issued["web"] is True
    assert db.committed is True
    assert any(getattr(item, "provider", None) == "google" for item in db.added)


def test_callback_state_mismatch_does_not_exchange_code(monkeypatch):
    configuration = settings()
    app = SimpleNamespace(state=SimpleNamespace(settings=configuration))
    transaction = OIDCTransaction("state", "nonce", "verifier")
    request = _request_with_cookie(app, encode_transaction(configuration, transaction))

    def exchange_must_not_run(*args):
        raise AssertionError("token exchange must not run after state mismatch")

    monkeypatch.setattr(google_routes, "exchange_code", exchange_must_not_run)

    with pytest.raises(HTTPException) as error:
        google_routes.google_callback(request, code="authorization-code", state="wrong-state")

    assert error.value.status_code == 401
