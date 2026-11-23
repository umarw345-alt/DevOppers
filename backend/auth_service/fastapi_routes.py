from datetime import timedelta
import secrets
from uuid import UUID, uuid4

from argon2.exceptions import InvalidHashError, VerifyMismatchError
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from database import open_db

from .dependencies import ACCESS_COOKIE, CSRF_COOKIE, REFRESH_COOKIE, access_identity, is_web_request, require_csrf
from .models import Session, User
from .security import build_password_hasher, create_access_token, hash_refresh_token, new_refresh_token, utc_now

router = APIRouter()


class Credentials(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=1024)


class RefreshRequest(BaseModel):
    refresh_token: str | None = Field(default=None, min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str


class UserResponse(BaseModel):
    id: UUID
    email: str


class AuthResponse(TokenResponse):
    user: UserResponse


class WebAuthResponse(BaseModel):
    user: UserResponse


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _create_session(request: Request, db, user_id: UUID, token_family_id: UUID | None = None):
    settings = request.app.state.settings
    session_id = uuid4()
    refresh_token = new_refresh_token()
    now = utc_now()
    session = Session(
        id=session_id,
        user_id=user_id,
        refresh_token_hash=hash_refresh_token(refresh_token),
        token_family_id=token_family_id or uuid4(),
        expires_at=now + timedelta(days=settings.refresh_token_ttl_days),
        created_at=now,
        last_activity_at=now,
    )
    db.add(session)
    return session, refresh_token


def _set_auth_cookies(request: Request, response: Response, access_token: str, refresh_token: str) -> None:
    settings = request.app.state.settings
    cookie_options = {
        "httponly": True,
        "secure": settings.web_cookie_secure,
        "samesite": settings.web_cookie_samesite,
        "path": "/",
    }
    response.set_cookie(ACCESS_COOKIE, access_token, max_age=settings.access_token_ttl_minutes * 60, **cookie_options)
    response.set_cookie(REFRESH_COOKIE, refresh_token, max_age=settings.refresh_token_ttl_days * 86400, **cookie_options)
    response.set_cookie(CSRF_COOKIE, secrets.token_urlsafe(32), max_age=settings.refresh_token_ttl_days * 86400, httponly=False, **{key: value for key, value in cookie_options.items() if key != "httponly"})


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_COOKIE, path="/")
    response.delete_cookie(REFRESH_COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")


def _auth_response(
    request: Request,
    response: Response,
    user: User,
    session: Session,
    refresh_token: str,
    web: bool | None = None,
):
    access_token = create_access_token(request.app.state.settings, user.id, session.id)
    if (is_web_request(request) if web is None else web):
        _set_auth_cookies(request, response, access_token, refresh_token)
        return WebAuthResponse(user=UserResponse(id=user.id, email=user.email))
    return AuthResponse(
        user=UserResponse(id=user.id, email=user.email),
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/v1/auth/register", response_model=AuthResponse | WebAuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: Credentials, request: Request, response: Response):
    email = _normalize_email(payload.email)
    db = open_db(request)
    try:
        if db.scalar(select(User).where(User.email == email)) is not None:
            raise HTTPException(status_code=409, detail="Unable to register account")
        user = User(id=uuid4(), email=email, password_hash=build_password_hasher(request.app.state.settings).hash(payload.password), created_at=utc_now())
        db.add(user)
        # Ensure the parent row exists before inserting the session's FK row.
        db.flush()
        session, refresh_token = _create_session(request, db, user.id)
        try:
            db.commit()
        except IntegrityError as error:
            db.rollback()
            raise HTTPException(status_code=409, detail="Unable to register account") from error
        return _auth_response(request, response, user, session, refresh_token)
    finally:
        db.close()


@router.post("/v1/auth/login", response_model=AuthResponse | WebAuthResponse)
def login(payload: Credentials, request: Request, response: Response):
    email = _normalize_email(payload.email)
    key = f"{request.client.host if request.client else 'unknown'}:{email}"
    if not request.app.state.login_rate_limiter.allow(key):
        raise HTTPException(status_code=429, detail="Too many login attempts")
    db = open_db(request)
    try:
        user = db.scalar(select(User).where(User.email == email))
        valid = False
        if user is not None and user.password_hash:
            try:
                valid = build_password_hasher(request.app.state.settings).verify(user.password_hash, payload.password)
            except (InvalidHashError, VerifyMismatchError):
                valid = False
        if not valid:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        session, refresh_token = _create_session(request, db, user.id)
        db.commit()
        return _auth_response(request, response, user, session, refresh_token)
    finally:
        db.close()


@router.post("/v1/auth/refresh", response_model=TokenResponse | WebAuthResponse)
def refresh(request: Request, response: Response, payload: RefreshRequest | None = None):
    refresh_token_value = payload.refresh_token if payload is not None else None
    if is_web_request(request):
        refresh_token_value = request.cookies.get(REFRESH_COOKIE)
    if not refresh_token_value:
        raise HTTPException(status_code=401, detail="Unauthorized")
    require_csrf(request)
    db = open_db(request)
    try:
        session = db.scalar(select(Session).where(Session.refresh_token_hash == hash_refresh_token(refresh_token_value)).with_for_update())
        now = utc_now()
        if session is None or session.expires_at <= now:
            raise HTTPException(status_code=401, detail="Unauthorized")
        if session.used_at is not None:
            db.execute(update(Session).where(Session.token_family_id == session.token_family_id).values(revoked_at=now))
            db.commit()
            raise HTTPException(status_code=401, detail="Unauthorized")
        if session.revoked_at is not None:
            raise HTTPException(status_code=401, detail="Unauthorized")
        if session.last_activity_at is None or session.last_activity_at + timedelta(minutes=request.app.state.settings.afk_timeout_minutes) <= now:
            session.revoked_at = now
            db.commit()
            raise HTTPException(status_code=401, detail="Session expired")
        session.used_at = now
        session.revoked_at = now
        replacement, refresh_token = _create_session(request, db, session.user_id, session.token_family_id)
        db.commit()
        access_token = create_access_token(request.app.state.settings, session.user_id, replacement.id)
        if is_web_request(request):
            _set_auth_cookies(request, response, access_token, refresh_token)
            user = db.get(User, session.user_id)
            return WebAuthResponse(user=UserResponse(id=user.id, email=user.email))
        return TokenResponse(access_token=access_token, refresh_token=refresh_token)
    finally:
        db.close()


@router.post("/v1/auth/logout")
def logout(request: Request, response: Response, identity=Depends(access_identity)):
    require_csrf(request)
    user_id, session_id = identity
    db = open_db(request)
    try:
        session = db.get(Session, session_id)
        if session is not None and session.user_id == user_id:
            now = utc_now()
            db.execute(update(Session).where(Session.token_family_id == session.token_family_id).values(revoked_at=now))
            db.commit()
        if is_web_request(request):
            _clear_auth_cookies(response)
        return {"status": "ok"}
    finally:
        db.close()


@router.post("/v1/auth/input")
def record_input(request: Request, identity=Depends(access_identity)):
    require_csrf(request)
    user_id, session_id = identity
    db = open_db(request)
    try:
        session = db.get(Session, session_id)
        if session is None or session.user_id != user_id or session.revoked_at is not None:
            raise HTTPException(status_code=401, detail="Unauthorized")
        now = utc_now()
        if session.last_activity_at is None or now - session.last_activity_at >= timedelta(minutes=3):
            session.last_activity_at = now
            db.commit()
        return {"status": "ok"}
    finally:
        db.close()
