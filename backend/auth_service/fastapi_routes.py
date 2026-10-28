from datetime import timedelta
from typing import Annotated
from uuid import UUID, uuid4

import jwt
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from .models import Session, User
from .security import build_password_hasher, create_access_token, decode_access_token, hash_refresh_token, new_refresh_token, utc_now

router = APIRouter()


class Credentials(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=1024)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str


class UserResponse(BaseModel):
    id: UUID
    email: str


class AuthResponse(TokenResponse):
    user: UserResponse


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _db(request: Request):
    return request.app.state.db_session_factory()


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


def _auth_response(request: Request, user: User, session: Session, refresh_token: str):
    return AuthResponse(
        user=UserResponse(id=user.id, email=user.email),
        access_token=create_access_token(request.app.state.settings, user.id, session.id),
        refresh_token=refresh_token,
    )


def _identity(request: Request, authorization: str | None):
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


def access_identity(request: Request, authorization: Annotated[str | None, Header()] = None):
    return _identity(request, authorization)


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/v1/auth/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: Credentials, request: Request):
    email = _normalize_email(payload.email)
    db = _db(request)
    try:
        if db.scalar(select(User).where(User.email == email)) is not None:
            raise HTTPException(status_code=409, detail="Unable to register account")
        user = User(id=uuid4(), email=email, password_hash=build_password_hasher(request.app.state.settings).hash(payload.password), created_at=utc_now())
        db.add(user)
        session, refresh_token = _create_session(request, db, user.id)
        try:
            db.commit()
        except IntegrityError as error:
            db.rollback()
            raise HTTPException(status_code=409, detail="Unable to register account") from error
        return _auth_response(request, user, session, refresh_token)
    finally:
        db.close()


@router.post("/v1/auth/login", response_model=AuthResponse)
def login(payload: Credentials, request: Request):
    email = _normalize_email(payload.email)
    key = f"{request.client.host if request.client else 'unknown'}:{email}"
    if not request.app.state.login_rate_limiter.allow(key):
        raise HTTPException(status_code=429, detail="Too many login attempts")
    db = _db(request)
    try:
        user = db.scalar(select(User).where(User.email == email))
        valid = False
        if user is not None:
            try:
                valid = build_password_hasher(request.app.state.settings).verify(user.password_hash, payload.password)
            except (InvalidHashError, VerifyMismatchError):
                valid = False
        if not valid:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        session, refresh_token = _create_session(request, db, user.id)
        db.commit()
        return _auth_response(request, user, session, refresh_token)
    finally:
        db.close()


@router.post("/v1/auth/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, request: Request):
    db = _db(request)
    try:
        session = db.scalar(select(Session).where(Session.refresh_token_hash == hash_refresh_token(payload.refresh_token)).with_for_update())
        now = utc_now()
        if session is None or session.expires_at <= now or session.revoked_at is not None:
            raise HTTPException(status_code=401, detail="Unauthorized")
        if session.used_at is not None:
            db.execute(update(Session).where(Session.token_family_id == session.token_family_id).values(revoked_at=now))
            db.commit()
            raise HTTPException(status_code=401, detail="Unauthorized")
        if session.last_activity_at is None or session.last_activity_at + timedelta(minutes=request.app.state.settings.afk_timeout_minutes) <= now:
            session.revoked_at = now
            db.commit()
            raise HTTPException(status_code=401, detail="Session expired")
        session.used_at = now
        session.revoked_at = now
        replacement, refresh_token = _create_session(request, db, session.user_id, session.token_family_id)
        db.commit()
        return TokenResponse(access_token=create_access_token(request.app.state.settings, session.user_id, replacement.id), refresh_token=refresh_token)
    finally:
        db.close()


@router.post("/v1/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, identity=Depends(access_identity)):
    user_id, session_id = identity
    db = _db(request)
    try:
        session = db.get(Session, session_id)
        if session is not None and session.user_id == user_id:
            session.revoked_at = utc_now()
            db.commit()
        return None
    finally:
        db.close()


@router.post("/v1/auth/input", status_code=status.HTTP_204_NO_CONTENT)
def record_input(request: Request, identity=Depends(access_identity)):
    user_id, session_id = identity
    db = _db(request)
    try:
        session = db.get(Session, session_id)
        if session is None or session.user_id != user_id or session.revoked_at is not None:
            raise HTTPException(status_code=401, detail="Unauthorized")
        now = utc_now()
        if session.last_activity_at is None or now - session.last_activity_at >= timedelta(minutes=5):
            session.last_activity_at = now
            db.commit()
        return None
    finally:
        db.close()
