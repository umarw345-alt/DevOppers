"""Render every template into preview/ and serve it at http://localhost:8765.

Usage: uv run python preview.py [resume.json]
Defaults to tests/fixtures/full_resume.json.
"""

import json
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from portfolio.generator import TEMPLATE_IDS, render, write_site
from portfolio.schema import Resume

HERE = Path(__file__).parent
OUT = HERE / "preview"
PORT = 8765


def build(resume_path: Path) -> None:
    resume = Resume.model_validate(json.loads(resume_path.read_text(encoding="utf-8")))
    for template_id in TEMPLATE_IDS:
        write_site(render(resume, template_id), OUT / template_id)
    links = "".join(f'<li><a href="{t}/">{t}</a></li>' for t in TEMPLATE_IDS)
    (OUT / "index.html").write_text(
        f"<!doctype html><title>Templates</title><h1>Templates</h1><ul>{links}</ul>",
        encoding="utf-8",
    )


if __name__ == "__main__":
    resume_path = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "tests/fixtures/full_resume.json"
    build(resume_path)
    print(f"Serving {OUT} at http://localhost:{PORT}")
    handler = partial(SimpleHTTPRequestHandler, directory=OUT)
    ThreadingHTTPServer(("localhost", PORT), handler).serve_forever()
