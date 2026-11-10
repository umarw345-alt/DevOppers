# Portable Resume Backend

FastAPI backend for Portable Resume: one app (`main.py`) serving authentication and portfolio routes on port 8000. Uses [uv](https://docs.astral.sh/uv/) for packages; run every command from this `backend/` folder.

- `auth_service/` - register, login, refresh, logout and idle tracking under `/v1/auth/*` (Argon2id, RS256 JWTs, PostgreSQL)
- `portfolio/` - static portfolio site generator (see below)
- `migrations/` + `alembic.ini` - database schema migrations

## Setup

PostgreSQL runs in Docker (see the root README for `.env` and JWT keys):

```bash
docker compose up -d postgres migrations   # from the project root
uv sync
uv run fastapi dev main.py
```

The app loads `.env` from the project root. API docs: http://127.0.0.1:8000/docs

To create a new migration after changing `auth_service/models.py` (Postgres must be running):

```bash
uv run --env-file ../.env alembic revision --autogenerate -m "describe change"
uv run --env-file ../.env alembic upgrade head
```

## Tests

```bash
uv run pytest --cov=portfolio --cov=auth_service --cov=main
```

- `tests/unit/` - single functions and models on their own
- `tests/component/` - the generator with the real templates
- `tests/system/` - full requests through the API
- `tests/test_security.py`, `tests/test_rate_limit.py` - auth helpers
- `tests/test_integration.py` - opt-in auth tests against the running Docker stack (see `tests/run_tests.md`)

PRs should keep coverage above 80%.

## Portfolio generator

`portfolio/` turns a verified resume JSON into a static site.

- `schema.py` - the resume JSON format (`Resume`) and the user's customization (`Theme`)
- `themes.py` - fonts, each template's defaults, and the accent color contrast check
- `generator.py` - `render(resume, template_id, theme)` returns `{"index.html": ..., "style.css": ...}`
- `templates/` - `classic`, `modern`, `minimal`, `dark`, plus the shared `base.html` and `_sections.html`

Endpoints:

- `POST /portfolio/preview` - body `{"resume": {...}, "template_id": "classic", "theme": {...}}`, returns one HTML page
- `GET /portfolio/templates` - templates with their defaults, plus font choices

A theme is optional. Example: `{"accent": "#0f5132", "font": "display", "section_order": ["projects"]}`.
An accent that is hard to read on the chosen template returns a 422.

### Previewing templates locally

```bash
uv run python preview.py [resume.json] [theme.json]
```

Renders every template into `preview/` (git-ignored) and serves it at http://localhost:8765.
Restart it to see template changes.
