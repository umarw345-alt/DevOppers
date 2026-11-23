"""What other routes use from auth: who is calling, and the CSRF check for web requests."""

from hmac import compare_digest
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, Header, HTTPException, Request

from database import open_db

from .models import Session
from .security import decode_access_token, utc_now

ACCESS_COOKIE = "auth_access_token"
REFRESH_COOKIE = "auth_refresh_token"
CSRF_COOKIE = "auth_csrf_token"


def is_web_request(request: Request) -> bool:
    """The web app logs in with cookies and says so in this header; native apps send a bearer token."""
    return request.headers.get("x-client-platform", "").lower() == "web"


def require_csrf(request: Request) -> None:
    """Call at the start of every web request that changes something."""
    if is_web_request(request):
        cookie_token = request.cookies.get(CSRF_COOKIE, "")
        header_token = request.headers.get("x-csrf-token", "")
        if not cookie_token or not header_token or not compare_digest(cookie_token, header_token):
            raise HTTPException(status_code=403, detail="Invalid CSRF token")


def _identity(request: Request, authorization: str | None) -> tuple[UUID, UUID]:
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        claims = decode_access_token(request.app.state.settings, token)
        if claims.get("typ") != "access":
            raise ValueError("Unexpected token type")
        return UUID(claims["sub"]), UUID(claims["sid"])
    except (ValueError, jwt.InvalidTokenError) as error:
        raise HTTPException(status_code=401, detail="Unauthorized") from error


def access_identity(request: Request, authorization: Annotated[str | None, Header()] = None) -> tuple[UUID, UUID]:
    """Dependency: (user_id, session_id) of a logged-in caller, or 401."""
    if not authorization and is_web_request(request):
        cookie_token = request.cookies.get(ACCESS_COOKIE)
        if cookie_token:
            authorization = f"Bearer {cookie_token}"
    user_id, session_id = _identity(request, authorization)
    with open_db(request) as db:
        session = db.get(Session, session_id)
        if session is None or session.user_id != user_id or session.revoked_at is not None or session.expires_at <= utc_now():
            raise HTTPException(status_code=401, detail="Unauthorized")
        return user_id, session_id


def current_user_id(identity: Annotated[tuple[UUID, UUID], Depends(access_identity)]) -> UUID:
    """Dependency: the logged-in caller's user ID, or 401."""
    return identity[0]
