"""Resume upload: the logged-in user sends a PDF/JPEG/PNG and gets the extracted Resume JSON to review."""

import logging
import os
from datetime import timedelta
from typing import Annotated

import anthropic
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from sqlalchemy import func, select

from auth_service.fastapi_routes import _db, _require_csrf, access_identity
from auth_service.models import ResumeUpload
from auth_service.security import utc_now
from portfolio.schema import Resume
from resume.extractor import ExtractionError, extract_resume

logger = logging.getLogger(__name__)
router = APIRouter(tags=["resume"])

# Vercel rejects request bodies over 4.5 MB before they reach the app, so stay under that.
MAX_UPLOAD_BYTES = 4 * 1024 * 1024
DAILY_UPLOAD_CAP = int(os.getenv("DAILY_UPLOAD_CAP", "200"))
# Identify the file by its first bytes; the client's content type can't be trusted.
SIGNATURES = {b"%PDF": "application/pdf", b"\xff\xd8\xff": "image/jpeg", b"\x89PNG": "image/png"}


def get_anthropic_client(request: Request) -> anthropic.Anthropic:
    """One shared client per app. Tests replace this with a fake."""
    if not (os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN")):
        raise HTTPException(status_code=503, detail="Resume reading isn't set up on this server.")
    client = getattr(request.app.state, "anthropic_client", None)
    if client is None:
        client = request.app.state.anthropic_client = anthropic.Anthropic()
    return client


def spend_daily_upload(request: Request, user_id) -> None:
    """Every upload is a paid Claude call, so the whole site gets DAILY_UPLOAD_CAP per 24 hours."""
    with _db(request) as db:
        used = db.scalar(select(func.count()).select_from(ResumeUpload).where(ResumeUpload.created_at > utc_now() - timedelta(days=1)))
        if used >= DAILY_UPLOAD_CAP:
            raise HTTPException(status_code=429, detail="Resume reading is at today's limit. Start blank and type it in, or try tomorrow.")
        db.add(ResumeUpload(user_id=user_id, created_at=utc_now()))
        db.commit()


def detect_type(data: bytes) -> str | None:
    return next((mime for signature, mime in SIGNATURES.items() if data.startswith(signature)), None)


@router.post("/resume/upload", response_model=Resume)
def upload_resume(
    file: UploadFile,
    request: Request,
    identity=Depends(access_identity),
    client: Annotated[anthropic.Anthropic, Depends(get_anthropic_client)] = None,
) -> Resume:
    """Read the uploaded resume with Claude and return it as Resume JSON for the user to review.

    Nothing is saved: the app shows the result in its edit form.
    """
    _require_csrf(request)
    user_id, _ = identity
    if not request.app.state.upload_rate_limiter.allow(str(user_id)):
        raise HTTPException(status_code=429, detail="Too many uploads. Try again in a few minutes.")

    data = file.file.read(MAX_UPLOAD_BYTES + 1)
    if not data:
        raise HTTPException(status_code=400, detail="The file is empty.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="The file is over 4 MB.")
    mime_type = detect_type(data)
    if mime_type is None:
        raise HTTPException(status_code=415, detail="Upload a PDF, JPEG, or PNG.")
    spend_daily_upload(request, user_id)

    try:
        result = extract_resume(data, mime_type, client=client)
    except ExtractionError as error:
        raise HTTPException(status_code=422, detail=f"Couldn't read that resume: {error}") from error
    except (anthropic.AuthenticationError, anthropic.PermissionDeniedError) as error:
        logger.error("Anthropic rejected the API key: %s", type(error).__name__)
        raise HTTPException(status_code=503, detail="Resume reading isn't set up on this server.") from error
    except anthropic.BadRequestError as error:
        # e.g. an encrypted, corrupt, or unreadable file
        raise HTTPException(status_code=422, detail="Couldn't read that file. Try a different PDF or image.") from error
    except anthropic.AnthropicError as error:
        # rate limits, overload, network errors, timeouts
        logger.warning("Resume extraction unavailable: %s", type(error).__name__)
        raise HTTPException(status_code=503, detail="Resume reading is busy right now. Try again in a minute.") from error

    logger.info(
        "Extracted resume (%s, %s): model=%s input_tokens=%d output_tokens=%d",
        mime_type, len(data), result.model, result.input_tokens, result.output_tokens,
    )
    return result.resume
