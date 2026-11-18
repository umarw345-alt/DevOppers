"""Google OpenID Connect discovery, authorization, exchange, and validation."""

from dataclasses import dataclass
import hashlib
import base64
import secrets
from hmac import compare_digest
from typing import Any
from urllib.parse import urlencode

import httpx
import jwt

from .config import Settings


GOOGLE_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}
GOOGLE_SCOPES = "openid profile email"


class GoogleOIDCError(Exception):
    """A safe, user-facing Google OIDC failure without token contents."""


@dataclass(frozen=True)
class OIDCTransaction:
    state: str
    nonce: str
    code_verifier: str


def is_configured(settings: Settings) -> bool:
    return bool(
        settings.google_client_id
        and settings.google_client_secret
        and settings.google_oidc_state_secret
    )


def new_transaction() -> OIDCTransaction:
    code_verifier = secrets.token_urlsafe(64)
    return OIDCTransaction(
        state=secrets.token_urlsafe(32),
        nonce=secrets.token_urlsafe(32),
        code_verifier=code_verifier,
    )


def pkce_challenge(code_verifier: str) -> str:
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def encode_transaction(settings: Settings, transaction: OIDCTransaction) -> str:
    if not settings.google_oidc_state_secret:
        raise GoogleOIDCError("Google OIDC state protection is not configured")
    return jwt.encode(
        {
            "state": transaction.state,
            "nonce": transaction.nonce,
            "code_verifier": transaction.code_verifier,
            "exp": __import__("time").time() + 300,
        },
        settings.google_oidc_state_secret,
        algorithm="HS256",
    )


def decode_transaction(settings: Settings, value: str) -> OIDCTransaction:
    if not settings.google_oidc_state_secret:
        raise GoogleOIDCError("Google OIDC state protection is not configured")
    try:
        claims = jwt.decode(value, settings.google_oidc_state_secret, algorithms=["HS256"])
        state = claims["state"]
        nonce = claims["nonce"]
        code_verifier = claims["code_verifier"]
        if not all(isinstance(item, str) and item for item in (state, nonce, code_verifier)):
            raise ValueError("Invalid transaction values")
        return OIDCTransaction(state=state, nonce=nonce, code_verifier=code_verifier)
    except (KeyError, TypeError, ValueError, jwt.InvalidTokenError) as error:
        raise GoogleOIDCError("Invalid or expired Google OIDC transaction") from error


def _json_request(method: str, url: str, **kwargs: Any) -> dict[str, Any]:
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.request(method, url, **kwargs)
            response.raise_for_status()
            body = response.json()
    except (httpx.HTTPError, ValueError) as error:
        raise GoogleOIDCError("Google OIDC request failed") from error
    if not isinstance(body, dict):
        raise GoogleOIDCError("Google returned an invalid OIDC response")
    return body


def discovery(settings: Settings) -> dict[str, Any]:
    metadata = _json_request("GET", settings.google_discovery_url)
    required = ("authorization_endpoint", "token_endpoint", "jwks_uri")
    if any(not isinstance(metadata.get(key), str) for key in required):
        raise GoogleOIDCError("Google OIDC discovery metadata is incomplete")
    if any(not metadata[key].startswith("https://") for key in required):
        raise GoogleOIDCError("Google OIDC endpoints must use HTTPS")
    return metadata


def authorization_url(settings: Settings, transaction: OIDCTransaction) -> str:
    if not settings.google_client_id:
        raise GoogleOIDCError("Google client ID is not configured")
    metadata = discovery(settings)
    query = urlencode(
        {
            "client_id": settings.google_client_id,
            "response_type": "code",
            "scope": GOOGLE_SCOPES,
            "redirect_uri": settings.google_redirect_uri,
            "state": transaction.state,
            "nonce": transaction.nonce,
            "code_challenge": pkce_challenge(transaction.code_verifier),
            "code_challenge_method": "S256",
        }
    )
    return f"{metadata['authorization_endpoint']}?{query}"


def exchange_code(settings: Settings, transaction: OIDCTransaction, code: str) -> str:
    if not settings.google_client_id or not settings.google_client_secret:
        raise GoogleOIDCError("Google client credentials are not configured")
    metadata = discovery(settings)
    body = _json_request(
        "POST",
        metadata["token_endpoint"],
        data={
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "code": code,
            "code_verifier": transaction.code_verifier,
            "grant_type": "authorization_code",
            "redirect_uri": settings.google_redirect_uri,
        },
        headers={"Accept": "application/json"},
    )
    id_token = body.get("id_token")
    if not isinstance(id_token, str) or not id_token:
        raise GoogleOIDCError("Google did not return an ID token")
    return id_token


def verify_id_token(settings: Settings, id_token: str, transaction: OIDCTransaction) -> dict[str, Any]:
    if not settings.google_client_id:
        raise GoogleOIDCError("Google client ID is not configured")
    try:
        metadata = discovery(settings)
        signing_key = jwt.PyJWKClient(metadata["jwks_uri"]).get_signing_key_from_jwt(id_token)
        claims = jwt.decode(
            id_token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.google_client_id,
        )
    except (jwt.InvalidTokenError, jwt.PyJWKClientError, GoogleOIDCError) as error:
        raise GoogleOIDCError("Google ID token validation failed") from error

    if claims.get("iss") not in GOOGLE_ISSUERS:
        raise GoogleOIDCError("Google ID token issuer is invalid")
    if not isinstance(claims.get("nonce"), str) or not compare_digest(claims["nonce"], transaction.nonce):
        raise GoogleOIDCError("Google ID token nonce is invalid")
    if claims.get("email_verified") is not True:
        raise GoogleOIDCError("Google email is not verified")
    if not isinstance(claims.get("sub"), str) or not claims["sub"]:
        raise GoogleOIDCError("Google ID token subject is missing")
    if not isinstance(claims.get("email"), str) or not claims["email"]:
        raise GoogleOIDCError("Google ID token email is missing")
    return claims
