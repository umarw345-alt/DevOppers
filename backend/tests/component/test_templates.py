from html.parser import HTMLParser

import pytest

from portfolio.generator import TEMPLATE_IDS, render
from portfolio.schema import Resume, Theme
from portfolio.themes import ThemeError

SECTION_HEADINGS = ["Experience", "Education", "Projects", "Skills"]


class TagCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

    def find(self, tag):
        return [attrs for t, attrs in self.tags if t == tag]


def parse(html):
    collector = TagCollector()
    collector.feed(html)
    return collector


def build(data, template_id):
    return render(Resume.model_validate(data), template_id)


@pytest.fixture(params=TEMPLATE_IDS)
def template_id(request):
    return request.param


def test_every_template_has_html_and_css(full_resume, template_id):
    files = build(full_resume, template_id)
    assert set(files) == {"index.html", "style.css"}
    assert files["style.css"].strip()


def test_full_resume_shows_all_content(full_resume, template_id):
    html = build(full_resume, template_id)["index.html"]
    for text in [
        "Jordan Lee",
        "Backend Engineer",
        "jordan.lee@example.com",
        "(408) 555-0134",
        "San Jose State University",
        "Software Engineering Intern",
        "Acme Robotics",
        "Jun 2025 – Aug 2025",
        "Sep 2025 – Present",
        "Built a REST API for sensor telemetry",
        "Portable Resume",
        "FastAPI",
        *SECTION_HEADINGS,
    ]:
        assert text in html, f"{text!r} missing from {template_id}"


def test_links_point_to_the_right_places(full_resume, template_id):
    hrefs = [a["href"] for a in parse(build(full_resume, template_id)["index.html"]).find("a")]
    assert "mailto:jordan.lee@example.com" in hrefs
    assert "https://github.com/jordanlee" in hrefs
    assert "https://github.com/example/portable-resume" in hrefs


def test_minimal_resume_skips_empty_sections(minimal_resume, template_id):
    html = build(minimal_resume, template_id)["index.html"]
    assert "Sam Rivera" in html
    for heading in [*SECTION_HEADINGS, "About"]:
        assert f">{heading}</h2>" not in html
    assert 'class="contact"' not in html
    assert 'class="headline"' not in html


def test_hidden_fields_are_not_in_the_html(full_resume, template_id):
    full_resume["hidden_fields"] = ["contact.phone", "contact.email", "projects", "summary"]
    html = build(full_resume, template_id)["index.html"]
    assert "(408) 555-0134" not in html
    assert "jordan.lee@example.com" not in html
    assert ">Projects</h2>" not in html
    assert "backend systems and developer tools" not in html
    assert "Acme Robotics" in html


def test_user_text_cannot_inject_html(malicious_resume, template_id):
    html = build(malicious_resume, template_id)["index.html"]
    tags = {tag for tag, _ in parse(html).tags}
    assert not tags & {"script", "img", "iframe", "b"}
    assert "&lt;script&gt;" in html


def test_basic_accessibility(full_resume, template_id):
    page = parse(build(full_resume, template_id)["index.html"])
    assert page.find("html")[0].get("lang") == "en"
    assert any(m.get("name") == "viewport" for m in page.find("meta"))
    assert len(page.find("h1")) == 1
    assert len(page.find("main")) == 1
    assert {"rel": "stylesheet", "href": "style.css"} in page.find("link")
    for section in page.find("section"):
        assert section.get("aria-labelledby")
    for img in page.find("img"):
        assert img.get("alt")


def test_page_title_uses_name(full_resume, template_id):
    html = build(full_resume, template_id)["index.html"]
    assert "<title>Jordan Lee | Portfolio</title>" in html


def test_default_theme_is_applied(full_resume, template_id):
    page = parse(build(full_resume, template_id)["index.html"])
    font_links = [l["href"] for l in page.find("link") if "fonts.googleapis.com/css2" in l.get("href", "")]
    assert len(font_links) == 1


READABLE_ACCENT = {"classic": "#0f5132", "modern": "#0f5132", "minimal": "#0f5132", "dark": "#5eead4"}
UNREADABLE_ACCENT = {"classic": "#ffffff", "modern": "#ffffff", "minimal": "#ffffff", "dark": "#000000"}


def test_custom_theme_is_applied(full_resume, template_id):
    accent = READABLE_ACCENT[template_id]
    theme = Theme(accent=accent, font="display", section_order=["education", "experience"])
    html = render(Resume.model_validate(full_resume), template_id, theme)["index.html"]
    assert f"--accent: {accent};" in html
    assert "Playfair+Display" in html
    assert html.index(">Education</h2>") < html.index(">Experience</h2>")


def test_unreadable_accent_raises(full_resume, template_id):
    theme = Theme(accent=UNREADABLE_ACCENT[template_id])
    with pytest.raises(ThemeError):
        render(Resume.model_validate(full_resume), template_id, theme)


def test_every_section_renders_exactly_once(full_resume, template_id):
    html = build(full_resume, template_id)["index.html"]
    for heading in SECTION_HEADINGS:
        assert html.count(f">{heading}</h2>") == 1
