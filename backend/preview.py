"""Render every template into preview/ and serve it at http://localhost:8765.

Usage: uv run python preview.py [resume.json] [theme.json]
Defaults to tests/fixtures/full_resume.json and each template's default theme.
"""

import json
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from portfolio.generator import TEMPLATE_IDS, render, write_site
from portfolio.schema import Resume, Theme
from portfolio.themes import ThemeError

HERE = Path(__file__).parent
OUT = HERE / "preview"
PORT = 8765


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build(resume_path: Path, theme_path: Path | None) -> None:
    resume = Resume.model_validate(read_json(resume_path))
    theme = Theme.model_validate(read_json(theme_path)) if theme_path else None
    links = []
    for template_id in TEMPLATE_IDS:
        try:
            write_site(render(resume, template_id, theme), OUT / template_id)
            links.append(f'<li><a href="{template_id}/">{template_id}</a></li>')
        except ThemeError as error:
            links.append(f"<li>{template_id}: skipped ({error})</li>")
    (OUT / "index.html").write_text(
        f"<!doctype html><title>Templates</title><h1>Templates</h1><ul>{''.join(links)}</ul>",
        encoding="utf-8",
    )


if __name__ == "__main__":
    resume_path = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "tests/fixtures/full_resume.json"
    theme_path = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    build(resume_path, theme_path)
    print(f"Serving {OUT} at http://localhost:{PORT}")
    handler = partial(SimpleHTTPRequestHandler, directory=OUT)
    ThreadingHTTPServer(("localhost", PORT), handler).serve_forever()
