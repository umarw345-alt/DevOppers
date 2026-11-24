"""Portfolio routes: preview a design, publish it at /<slug>, and serve the public page."""

import os
import re
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError

from auth_service.dependencies import current_user_id, require_csrf
from auth_service.security import utc_now
from database import open_db
from portfolio.generator import inline_css, render
from portfolio.google_wallet import GoogleWalletError, build_save_url
from portfolio.models import Portfolio, ResumeRecord
from portfolio.schema import Resume, Theme
from portfolio.themes import FONTS, TEMPLATES, TemplateId, ThemeError, resolve_theme
from portfolio.wallet import ICON, PassError, build_pass

router = APIRouter(tags=["portfolio"])

SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{1,38}[a-z0-9]$")
RESERVED = {"assets", "docs", "redoc", "health", "portfolio", "portfolios", "resume"}


class Design(BaseModel):
    resume: Resume
    template_id: TemplateId
    theme: Theme = Theme()


def public_url(request: Request, slug: str) -> str:
    """The portfolio's public link, e.g. https://devoppers.vercel.app/jerry.

    Built from the address this request came in on, so every deployment links to itself.
    Set PUBLIC_BASE_URL to override it, e.g. your computer's LAN address so a phone can scan the QR code.
    """
    base = os.getenv("PUBLIC_BASE_URL")
    if not base:
        scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
        host = request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc
        base = f"{scheme}://{host}"
    return f"{base.rstrip('/')}/{slug}"


def to_json(request: Request, p: Portfolio) -> dict:
    slug = p.public_slug
    return {
        "slug": slug,
        "url": public_url(request, slug),
        "resume": p.resume_record.resume_json if p.resume_record else {},
        "template_id": p.template_id,
        "theme": p.theme_json or {},
    }


def render_page(design: Design, wallet_url: str | None = None) -> str:
    try:
        return inline_css(render(design.resume, design.template_id, design.theme, wallet_url))
    except ThemeError as error:
        raise HTTPException(status_code=422, detail=str(error))


@router.get("/portfolio/templates")
def list_templates():
    """The site templates with their default theme, plus the font choices."""
    return {
        "templates": [
            {"id": template_id, "accent": d.accent, "font": d.font, "sections": list(d.sections)}
            for template_id, d in TEMPLATES.items()
        ],
        "fonts": list(FONTS),
    }


@router.post("/portfolio/preview", response_class=HTMLResponse)
def preview(design: Design):
    """Render the page without saving it, for the design screen's live preview."""
    return render_page(design)


@router.get("/portfolios")
def list_mine(request: Request, user_id: UUID = Depends(current_user_id)):
    with open_db(request) as db:
        rows = db.scalars(
            select(Portfolio)
            .options(selectinload(Portfolio.resume_record))
            .where(Portfolio.user_id == user_id)
            .order_by(Portfolio.updated_at.desc())
        )
        return [to_json(request, p) for p in rows]


@router.put("/portfolios/{slug}")
def publish(slug: str, design: Design, request: Request, user_id: UUID = Depends(current_user_id)):
    """Create or update the caller's portfolio at /<slug>."""
    require_csrf(request)
    if not SLUG.match(slug) or slug in RESERVED:
        raise HTTPException(status_code=422, detail="Links are 3-40 lowercase letters, numbers and dashes.")
    render_page(design)
    with open_db(request) as db:
        p = db.scalar(select(Portfolio).where(Portfolio.public_slug == slug).options(selectinload(Portfolio.resume_record)))
        if p is None:
            now = utc_now()
            resume_record = ResumeRecord(
                id=uuid4(),
                user_id=user_id,
                resume_json=design.resume.model_dump(mode="json"),
                created_at=now,
                updated_at=now,
            )
            p = Portfolio(
                id=uuid4(),
                user_id=user_id,
                resume_record=resume_record,
                template_id=design.template_id,
                theme_json=design.theme.model_dump(mode="json", exclude_none=True),
                status="published",
                public_slug=slug,
                created_at=now,
                updated_at=now,
            )
            db.add(p)
        elif p.user_id != user_id:
            raise HTTPException(status_code=409, detail="That link is taken. Try another.")
        else:
            now = utc_now()
            if p.resume_record is None:
                p.resume_record = ResumeRecord(
                    id=uuid4(),
                    user_id=user_id,
                    resume_json=design.resume.model_dump(mode="json"),
                    created_at=now,
                    updated_at=now,
                )
            else:
                p.resume_record.resume_json = design.resume.model_dump(mode="json")
                p.resume_record.updated_at = now
            p.template_id = design.template_id
            p.theme_json = design.theme.model_dump(mode="json", exclude_none=True)
            p.status = "published"
            p.updated_at = now
        try:
            db.commit()
        except IntegrityError:
            raise HTTPException(status_code=409, detail="That link is taken. Try another.")
        return to_json(request, p)


@router.delete("/portfolios/{slug}", status_code=204)
def delete(slug: str, request: Request, user_id: UUID = Depends(current_user_id)):
    require_csrf(request)
    with open_db(request) as db:
        p = db.scalar(select(Portfolio).where(Portfolio.public_slug == slug))
        if p is None or p.user_id != user_id:
            raise HTTPException(status_code=404, detail="Portfolio not found.")
        db.delete(p)
        db.commit()


def find(request: Request, slug: str) -> Portfolio:
    with open_db(request) as db:
        p = db.scalar(select(Portfolio).where(Portfolio.public_slug == slug).options(selectinload(Portfolio.resume_record)))
    if p is None:
        raise HTTPException(status_code=404, detail="No portfolio at this link.")
    return p


@router.get("/google-wallet-logo.png", include_in_schema=False)
def google_wallet_logo():
    """The card logo. Google downloads it from this public URL instead of reading it from the card."""
    return Response(ICON, media_type="image/png", headers={"Cache-Control": "public, max-age=86400"})


# ponytail: rendered on every visit instead of pre-built onto a CDN; fine for a class demo, cache or pre-render when traffic is real.
@router.get("/{slug}", response_class=HTMLResponse, include_in_schema=False)
def public_page(slug: str, request: Request):
    """What a recruiter sees after scanning the QR code. No login needed."""
    p = find(request, slug)
    return render_page(Design(resume=p.resume_record.resume_json, template_id=p.template_id, theme=p.theme_json or {}), f"/{slug}/pass.pkpass")


@router.get("/{slug}/pass.pkpass", include_in_schema=False)
def wallet_pass(slug: str, request: Request):
    """Apple Wallet card in the portfolio's accent color. Public: it only holds the name, title and public link.
    Its QR code is just the URL, so editing the portfolio never needs a new pass."""
    p = find(request, slug)
    design = Design(resume=p.resume_record.resume_json, template_id=p.template_id, theme=p.theme_json or {})
    try:
        data = build_pass(
            serial=slug,
            name=design.resume.contact.name,
            headline=design.resume.contact.headline,
            url=public_url(request, slug),
            color=resolve_theme(design.template_id, design.theme).accent,
        )
    except PassError as error:
        raise HTTPException(status_code=503, detail=str(error))
    return Response(data, media_type="application/vnd.apple.pkpass", headers={"Content-Disposition": f'attachment; filename="{slug}.pkpass"'})


@router.get("/{slug}/google-wallet", include_in_schema=False)
def google_wallet(slug: str, request: Request):
    """Send the browser to Google's "Add to Google Wallet" page for this portfolio's card.
    Public, like the Apple pass: the card only holds the name, title and public link."""
    p = find(request, slug)
    design = Design(resume=p.resume_record.resume_json, template_id=p.template_id, theme=p.theme_json or {})
    logo_url = public_url(request, "google-wallet-logo.png")
    try:
        save_url = build_save_url(
            slug=slug,
            name=design.resume.contact.name,
            headline=design.resume.contact.headline,
            url=public_url(request, slug),
            color=resolve_theme(design.template_id, design.theme).accent,
            logo_url=logo_url if logo_url.startswith("https://") else None,
        )
    except GoogleWalletError as error:
        raise HTTPException(status_code=503, detail=str(error))
    return RedirectResponse(save_url, status_code=303)
