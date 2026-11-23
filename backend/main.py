"""Portable Resume backend API: authentication plus portfolio generation."""

import base64
import logging
import os
import tempfile
from pathlib import Path

from dotenv import load_dotenv

# Uvicorn only configures its own loggers; this lets app messages (e.g. per-upload token counts) show up.
logging.basicConfig(level=logging.INFO, format="%(levelname)s:     %(name)s - %(message)s")

# Lets `uv run fastapi dev main.py` pick up the repo's .env. Variables that are
# already set (e.g. by Docker) win, and a missing file is ignored.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Hosts without secret files (Vercel) pass each one base64-encoded as <NAME>_B64; write it out and point <NAME>_PATH at it.
for name in ("JWT_PRIVATE_KEY", "JWT_PUBLIC_KEY", "PASS_P12", "WWDR_CERT", "GOOGLE_WALLET_KEY"):
    if encoded := os.getenv(f"{name}_B64"):
        secret = Path(tempfile.gettempdir()) / name.lower()
        secret.write_bytes(base64.b64decode(encoded))
        os.environ[f"{name}_PATH"] = str(secret)

from urllib.parse import urlencode  # noqa: E402

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.exception_handlers import http_exception_handler  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import FileResponse, RedirectResponse, Response  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from starlette.exceptions import HTTPException  # noqa: E402

from auth_service.config import load_settings  # noqa: E402
from database import create_session_factory  # noqa: E402
from auth_service.fastapi_routes import router as auth_router  # noqa: E402
from auth_service.google_routes import router as google_router  # noqa: E402
from auth_service.rate_limit import LoginRateLimiter  # noqa: E402
from portfolio.routes import router as portfolio_router  # noqa: E402
from resume.routes import router as resume_router  # noqa: E402


def create_app() -> FastAPI:
    app = FastAPI(title="Portable Resume API", version="0.1.0")
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
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept", "X-Client-Platform", "X-CSRF-Token"],
    )
    # /health and /v1/auth/* (register, login, refresh, logout, input).
    # Other routes require a login with auth_service.dependencies.current_user_id.
    app.include_router(auth_router, tags=["auth"])
    app.include_router(google_router, tags=["auth"])

    # Google sign-in runs as full-page redirects, so a failure there would leave the user on a
    # bare JSON page. Send them back to the app's login screen with the message instead.
    @app.exception_handler(HTTPException)
    async def google_errors_back_to_app(request: Request, error: HTTPException):
        if request.url.path.startswith("/v1/auth/google/"):
            query = urlencode({"auth_error": error.detail})
            return RedirectResponse(f"{settings.google_frontend_redirect_uri}?{query}", status_code=303)
        return await http_exception_handler(request, error)

    # Each upload is a paid Claude call, so cap it per user: 10 uploads per 10 minutes.
    app.state.upload_rate_limiter = LoginRateLimiter(10, 600)
    app.include_router(resume_router)
    web_dir = Path(__file__).resolve().parent.parent / "web"
    if (web_dir / "index.html").is_file():
        # Every build's index.html has the same size and timestamp, so a file-based ETag never changes and
        # browsers keep an old copy pointing at a deleted bundle (a blank page). Send it without one, uncached.
        index_html = (web_dir / "index.html").read_bytes()
        app.get("/", include_in_schema=False)(lambda: Response(index_html, media_type="text/html", headers={"Cache-Control": "no-store"}))
        app.get("/favicon.ico", include_in_schema=False)(lambda: FileResponse(web_dir / "favicon.ico"))
    # Last, because its public GET /{slug} page would otherwise catch other one-segment paths.
    app.include_router(portfolio_router)
    if web_dir.is_dir():
        app.mount("/", StaticFiles(directory=web_dir, html=True), name="frontend")
    return app


app = create_app()
