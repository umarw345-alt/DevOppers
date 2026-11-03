# Portable Resume Backend

FastAPI backend for Portable Resume. Uses [uv](https://docs.astral.sh/uv/) for packages.

## Setup

```bash
uv sync
uv run fastapi dev main.py
```

API docs: http://127.0.0.1:8000/docs

## Tests

```bash
uv run pytest --cov=portfolio --cov=main
```

- `tests/unit/` - single functions and models on their own
- `tests/component/` - the generator with the real templates
- `tests/system/` - full requests through the API

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
