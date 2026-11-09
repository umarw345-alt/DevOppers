"""Portable Resume backend API: authentication plus portfolio generation."""

from pathlib import Path

from dotenv import load_dotenv

# Lets `uv run fastapi dev main.py` pick up the repo's .env. Variables that are
# already set (e.g. by Docker) win, and a missing file is ignored.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from fastapi import FastAPI, HTTPException, UploadFile  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import HTMLResponse  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from auth_service.config import load_settings  # noqa: E402
from auth_service.db import create_session_factory  # noqa: E402
from auth_service.fastapi_routes import router as auth_router  # noqa: E402
from auth_service.rate_limit import LoginRateLimiter  # noqa: E402
from portfolio.generator import inline_css, render  # noqa: E402
from portfolio.schema import Resume, Theme  # noqa: E402
from portfolio.themes import FONTS, TEMPLATES, TemplateId, ThemeError  # noqa: E402


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
    # Use auth_service.fastapi_routes.access_identity to require a login on other routes.
    app.include_router(auth_router, tags=["auth"])
    return app


app = create_app()


class PreviewRequest(BaseModel):
    resume: Resume
    template_id: TemplateId
    theme: Theme | None = None


# User profile


@app.get("/users/me", tags=["users"])
def get_me():
    """Return the logged-in user's profile, resume status, and active passes."""


@app.patch("/users/me", tags=["users"])
def update_me():
    """Update basic profile fields."""


@app.put("/users/me/photo", tags=["users"])
def upload_profile_photo(file: UploadFile):
    """Upload or replace the user's ID/profile photo."""


# Resume ingestion (FR2) - upload PDF/JPEG, run OCR pipeline, return JSON


@app.post("/resume/upload", tags=["resume"])
def upload_resume(file: UploadFile):
    """Validate the file (PDF/JPEG, <=10 MB, not encrypted), run the
    extraction pipeline, and return the parsed resume JSON for review."""


@app.get("/resume", tags=["resume"])
def get_resume():
    """Return the user's saved resume JSON."""


@app.put("/resume", tags=["resume"])
def save_resume():
    """Save the user-reviewed/edited resume JSON (also used for manual entry)."""


# Portfolio Generation 

@app.post("/portfolio", tags=["portfolio"])
def generate_portfolio():
    """Generate (or regenerate) the static portfolio from the saved resume
    and return its public URL."""


@app.post("/portfolio/preview", tags=["portfolio"], response_class=HTMLResponse)
def preview_portfolio(request: PreviewRequest):
    """Render the portfolio as one HTML page (CSS inlined) without saving or
    deploying it. Used by the frontend's template picker and customization screen."""
    try:
        files = render(request.resume, request.template_id, request.theme)
    except ThemeError as error:
        raise HTTPException(status_code=422, detail=str(error))
    return inline_css(files)


@app.get("/portfolio/templates", tags=["portfolio"])
def list_portfolio_templates():
    """List the site templates with their default theme, plus the font choices."""
    return {
        "templates": [
            {"id": template_id, "accent": d.accent, "font": d.font, "sections": list(d.sections)}
            for template_id, d in TEMPLATES.items()
        ],
        "fonts": list(FONTS),
    }


@app.get("/portfolio", tags=["portfolio"])
def get_portfolio():
    """Return the user's portfolio URL and generation status."""


@app.patch("/portfolio/visibility", tags=["portfolio"])
def update_portfolio_visibility():
    """Toggle which resume fields are shown publicly, then redeploy."""


# Card design

@app.get("/card/themes", tags=["card"])
def list_card_themes():
    """Return the preset card themes."""


@app.get("/card", tags=["card"])
def get_card():
    """Return the user's current card theme and visible fields."""


@app.put("/card", tags=["card"])
def update_card():
    """Save card theme (colors, logo) and visible fields. Triggers a pass update."""


# Wallet passes

@app.post("/passes/apple", tags=["passes"])
def create_apple_pass():
    """Build and sign a .pkpass for Apple Wallet and return it as a download."""


@app.post("/passes/google", tags=["passes"])
def create_google_pass():
    """Build an RS256-signed JWT GenericObject and return the Save-to-Google-Wallet URL."""


# Apple PassKit web service (FR5) - called by Apple devices


@app.post(
    "/v1/devices/{device_id}/registrations/{pass_type_id}/{serial_number}",
    tags=["apple-passkit"],
)
def register_device(device_id: str, pass_type_id: str, serial_number: str):
    """Store the device's push token so we can notify it of pass updates."""


@app.delete(
    "/v1/devices/{device_id}/registrations/{pass_type_id}/{serial_number}",
    tags=["apple-passkit"],
)
def unregister_device(device_id: str, pass_type_id: str, serial_number: str):
    """Remove a device registration (pass deleted from wallet)."""


@app.get("/v1/devices/{device_id}/registrations/{pass_type_id}", tags=["apple-passkit"])
def list_updated_passes(
    device_id: str, pass_type_id: str, passesUpdatedSince: str | None = None
):
    """Return serial numbers of passes updated since the given tag."""


@app.get("/v1/passes/{pass_type_id}/{serial_number}", tags=["apple-passkit"])
def get_latest_pass(pass_type_id: str, serial_number: str):
    """Return the latest signed .pkpass for this serial number."""


@app.post("/v1/log", tags=["apple-passkit"])
def apple_log():
    """Receive error logs from Apple devices."""
