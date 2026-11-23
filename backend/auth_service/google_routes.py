"""FastAPI web routes for Google OIDC sign-in."""

import logging
from hmac import compare_digest
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from database import open_db

from .fastapi_routes import (
    _auth_response,
    _create_session,
    _normalize_email,
)
from .google_oidc import (
    GoogleOIDCError,
    authorization_url,
    decode_transaction,
    encode_transaction,
    exchange_code,
    is_configured,
    new_transaction,
    verify_id_token,
)
from .models import ExternalIdentity, User
from .security import utc_now


router = APIRouter()
logger = logging.getLogger(__name__)
GOOGLE_TRANSACTION_COOKIE = "google_oidc_transaction"
GOOGLE_TRANSACTION_MAX_AGE = 300


def _require_configuration(request: Request) -> None:
    if not is_configured(request.app.state.settings):
        raise HTTPException(status_code=503, detail="Google sign-in is not configured")


def _transaction_cookie_options(request: Request) -> dict:
    settings = request.app.state.settings
    return {
        "httponly": True,
        "secure": settings.web_cookie_secure,
        "samesite": "lax",
        "path": "/v1/auth/google",
        "max_age": GOOGLE_TRANSACTION_MAX_AGE,
    }


@router.get("/v1/auth/google/start", include_in_schema=False)
def google_start(request: Request):
    _require_configuration(request)
    transaction = new_transaction()
    try:
        url = authorization_url(request.app.state.settings, transaction)
        signed_transaction = encode_transaction(request.app.state.settings, transaction)
    except GoogleOIDCError as error:
        raise HTTPException(status_code=503, detail="Google sign-in is unavailable") from error

    response = RedirectResponse(url=url, status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(GOOGLE_TRANSACTION_COOKIE, signed_transaction, **_transaction_cookie_options(request))
    return response


@router.get("/v1/auth/google/callback", include_in_schema=False)
def google_callback(request: Request, code: str | None = None, state: str | None = None, error: str | None = None):
    _require_configuration(request)
    if error or not code or not state:
        raise HTTPException(status_code=400, detail="Google sign-in was not completed")

    signed_transaction = request.cookies.get(GOOGLE_TRANSACTION_COOKIE)
    if not signed_transaction:
        raise HTTPException(status_code=400, detail="Google sign-in session expired")
    try:
        transaction = decode_transaction(request.app.state.settings, signed_transaction)
        if not compare_digest(transaction.state, state):
            raise GoogleOIDCError("Google OIDC state mismatch")
        id_token = exchange_code(request.app.state.settings, transaction, code)
        claims = verify_id_token(request.app.state.settings, id_token, transaction)
    except GoogleOIDCError as oidc_error:
        raise HTTPException(status_code=401, detail="Google sign-in could not be verified") from oidc_error

    email = _normalize_email(claims["email"])
    provider_subject = claims["sub"]
    db = open_db(request)
    try:
        identity = db.scalar(
            select(ExternalIdentity).where(
                ExternalIdentity.provider == "google",
                ExternalIdentity.provider_subject == provider_subject,
            )
        )
        if identity is not None:
            user = db.get(User, identity.user_id)
            if user is None:
                raise HTTPException(status_code=500, detail="Authentication identity is incomplete")
            identity.email_at_link_time = email
            identity.updated_at = utc_now()
        else:
            if db.scalar(select(User).where(User.email == email)) is not None:
                raise HTTPException(status_code=409, detail="Google account must be linked explicitly. There may be an account already associated with this email.")
            now = utc_now()
            user = User(id=uuid4(), email=email, password_hash=None, created_at=now)
            identity = ExternalIdentity(
                id=uuid4(),
                user_id=user.id,
                provider="google",
                provider_subject=provider_subject,
                email_at_link_time=email,
                created_at=now,
                updated_at=now,
            )
            db.add(user)
            # Flush the parent first.  These models intentionally do not need
            # an ORM relationship for normal reads, but the database foreign
            # key still requires the user row to exist before the identity
            # row is inserted.
            db.flush()
            db.add(identity)
            db.flush()

        session, refresh_token = _create_session(request, db, user.id)
        db.commit()
    except IntegrityError as db_error:
        db.rollback()
        original = getattr(db_error, "orig", None)
        diagnostic = getattr(original, "diag", None)
        logger.warning(
            "Google identity link conflict: constraint=%s sqlstate=%s",
            getattr(diagnostic, "constraint_name", None),
            getattr(original, "sqlstate", None),
        )
        raise HTTPException(status_code=409, detail="Google account could not be linked") from db_error
    finally:
        db.close()

    response = RedirectResponse(
        url=request.app.state.settings.google_frontend_redirect_uri,
        status_code=status.HTTP_303_SEE_OTHER,
    )
    _auth_response(request, response, user, session, refresh_token, web=True)
    response.delete_cookie(GOOGLE_TRANSACTION_COOKIE, path="/v1/auth/google")
    return response
