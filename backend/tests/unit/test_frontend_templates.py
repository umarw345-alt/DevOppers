"""The app keeps its own copy of each template's default color (src/api.ts) so screens can draw
before any request finishes. This test fails if that copy drifts from portfolio/themes.py."""

import re
from pathlib import Path

from portfolio.themes import TEMPLATES

API_TS = Path(__file__).resolve().parents[3] / "src" / "api.ts"


def test_frontend_template_colors_match_the_backend():
    line = next(line for line in API_TS.read_text(encoding="utf-8").splitlines() if "export const TEMPLATES" in line)
    frontend = dict(re.findall(r"(\w+): '(#[0-9a-fA-F]{6})'", line))
    assert frontend == {template_id: d.accent for template_id, d in TEMPLATES.items()}
