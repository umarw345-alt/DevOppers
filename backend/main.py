"""Portable Resume backend API."""

from fastapi import FastAPI, UploadFile

app = FastAPI(title="Portable Resume API", version="0.1.0")


# Health

@app.get("/health", tags=["health"])
def health():
    """Simple liveness check."""
    return {"status": "ok"}


# Auth (FR1) - register, login, logout. Login returns a signed JWT.


@app.post("/auth/register", tags=["auth"])
def register():
    """Create an account (username, email, password). Hash password with bcrypt."""


@app.post("/auth/login", tags=["auth"])
def login():
    """Verify credentials and return a signed JWT session token."""


@app.post("/auth/logout", tags=["auth"])
def logout():
    """Invalidate the current session token."""


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
