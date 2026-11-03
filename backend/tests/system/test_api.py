import pytest
from fastapi.testclient import TestClient

import preview
from main import app
from portfolio.themes import TEMPLATE_IDS

client = TestClient(app)


def post_preview(resume, template_id="classic", theme=None):
    body = {"resume": resume, "template_id": template_id}
    if theme is not None:
        body["theme"] = theme
    return client.post("/portfolio/preview", json=body)


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


@pytest.mark.parametrize("template_id", TEMPLATE_IDS)
def test_preview_returns_a_full_html_page(full_resume, template_id):
    response = post_preview(full_resume, template_id)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    html = response.text
    assert html.startswith("<!doctype html>")
    assert "Jordan Lee" in html
    assert 'href="style.css"' not in html
    assert ".entry" in html


def test_preview_applies_theme(full_resume):
    theme = {"accent": "#0f5132", "font": "mono", "section_order": ["skills"]}
    html = post_preview(full_resume, "classic", theme).text
    assert "--accent: #0f5132;" in html
    assert "JetBrains+Mono" in html
    assert html.index(">Skills</h2>") < html.index(">Experience</h2>")


def test_preview_respects_hidden_fields(full_resume):
    full_resume["hidden_fields"] = ["contact.phone", "experience"]
    html = post_preview(full_resume).text
    assert "(408) 555-0134" not in html
    assert "Acme Robotics" not in html


def test_preview_escapes_user_text(malicious_resume):
    html = post_preview(malicious_resume).text
    assert "<script>alert" not in html
    assert "&lt;script&gt;" in html


def test_unknown_template_is_rejected(full_resume):
    assert post_preview(full_resume, "fancy").status_code == 422


def test_invalid_resume_is_rejected():
    assert post_preview({"contact": {}}).status_code == 422


def test_invalid_theme_is_rejected(full_resume):
    assert post_preview(full_resume, theme={"accent": "red"}).status_code == 422


def test_unreadable_accent_returns_a_clear_error(full_resume):
    response = post_preview(full_resume, "classic", {"accent": "#ffffff"})
    assert response.status_code == 422
    assert "too hard to read" in response.json()["detail"]


def test_templates_endpoint_lists_every_template():
    body = client.get("/portfolio/templates").json()
    assert [t["id"] for t in body["templates"]] == list(TEMPLATE_IDS)
    assert body["fonts"] == ["serif", "sans", "mono", "display"]
    for template in body["templates"]:
        assert post_preview({"contact": {"name": "A"}}, template["id"], {"accent": template["accent"]}).status_code == 200


def test_preview_script_builds_every_template(monkeypatch, tmp_path):
    monkeypatch.setattr(preview, "OUT", tmp_path)
    preview.build(preview.HERE / "tests/fixtures/full_resume.json", None)
    assert (tmp_path / "index.html").exists()
    for template_id in TEMPLATE_IDS:
        assert (tmp_path / template_id / "index.html").exists()
        assert (tmp_path / template_id / "style.css").exists()


def test_preview_script_skips_templates_a_theme_does_not_fit(monkeypatch, tmp_path):
    theme_path = tmp_path / "theme.json"
    theme_path.write_text('{"accent": "#000000"}')
    monkeypatch.setattr(preview, "OUT", tmp_path / "out")
    preview.build(preview.HERE / "tests/fixtures/full_resume.json", theme_path)
    assert not (tmp_path / "out" / "dark").exists()
    assert (tmp_path / "out" / "classic" / "index.html").exists()
    assert "dark: skipped" in (tmp_path / "out" / "index.html").read_text()
