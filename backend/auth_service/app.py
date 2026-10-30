from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import load_settings
from .db import create_session_factory
from .rate_limit import LoginRateLimiter
from .fastapi_routes import router


def create_app() -> FastAPI:
    app = FastAPI(title="Login Authenticator API", version="0.1.0")
    settings = load_settings()
    engine, session_factory = create_session_factory(settings.database_url)
    app.state.settings = settings
    app.state.db_engine = engine
    app.state.db_session_factory = session_factory
    app.state.login_rate_limiter = LoginRateLimiter(
        settings.login_rate_limit, settings.login_rate_window_seconds
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_allowed_origins),
        allow_credentials=False,
        allow_methods=["POST", "GET", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept"],
    )
    app.include_router(router)

    return app


app = create_app()
