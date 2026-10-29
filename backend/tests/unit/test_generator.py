import pytest
from jinja2 import DictLoader

from portfolio import generator
from portfolio.generator import (
    UnknownTemplateError,
    date_range,
    format_date,
    inline_css,
    remove_hidden,
    render,
    write_site,
)
from portfolio.schema import Entry, Resume


@pytest.mark.parametrize(
    "value, expected",
    [
        ("2024", "2024"),
        ("2024-01", "Jan 2024"),
        ("2024-12", "Dec 2024"),
        ("2024-06-15", "Jun 2024"),
        (None, "Present"),
    ],
)
def test_format_date(value, expected):
    assert format_date(value) == expected


@pytest.mark.parametrize(
    "start, end, expected",
    [
        ("2025-06", "2025-08", "Jun 2025 – Aug 2025"),
        ("2025-09", None, "Sep 2025 – Present"),
        (None, "2027-05", "May 2027"),
        (None, None, ""),
    ],
)
def test_date_range(start, end, expected):
    assert date_range(Entry(organization="X", start=start, end=end)) == expected


def test_remove_hidden_clears_contact_fields(full_resume):
    full_resume["hidden_fields"] = ["contact.email", "contact.phone", "contact.location"]
    public = remove_hidden(Resume.model_validate(full_resume))
    assert public.contact.email is None
    assert public.contact.phone is None
    assert public.contact.location is None
    assert public.contact.name == "Jordan Lee"
    assert len(public.contact.links) == 2


def test_remove_hidden_clears_sections(full_resume):
    full_resume["hidden_fields"] = ["summary", "education", "experience", "projects", "skills"]
    public = remove_hidden(Resume.model_validate(full_resume))
    assert public.summary is None
    assert public.education == []
    assert public.experience == []
    assert public.projects == []
    assert public.skills == []


def test_remove_hidden_does_not_change_original(full_resume):
    full_resume["hidden_fields"] = ["contact.phone", "skills"]
    resume = Resume.model_validate(full_resume)
    remove_hidden(resume)
    assert resume.contact.phone == "(408) 555-0134"
    assert resume.skills


def test_remove_hidden_with_nothing_hidden_keeps_everything(full_resume):
    resume = Resume.model_validate(full_resume)
    assert remove_hidden(resume) == resume


def test_render_rejects_unknown_template(minimal_resume):
    with pytest.raises(UnknownTemplateError):
        render(Resume.model_validate(minimal_resume), "fancy")


@pytest.fixture
def fake_templates(monkeypatch, tmp_path):
    (tmp_path / "classic").mkdir()
    (tmp_path / "classic" / "style.css").write_text("body {}")
    monkeypatch.setattr(generator, "TEMPLATES_DIR", tmp_path)
    monkeypatch.setattr(
        generator.env,
        "loader",
        DictLoader({"classic/index.html": "{{ resume.contact.name }}|{{ resume.contact.phone }}"}),
    )


def test_render_returns_html_and_css(fake_templates, full_resume):
    files = render(Resume.model_validate(full_resume), "classic")
    assert files == {"index.html": "Jordan Lee|(408) 555-0134", "style.css": "body {}"}


def test_render_applies_hidden_fields(fake_templates, full_resume):
    full_resume["hidden_fields"] = ["contact.phone"]
    files = render(Resume.model_validate(full_resume), "classic")
    assert files["index.html"] == "Jordan Lee|None"


def test_render_escapes_html(fake_templates, malicious_resume):
    html = render(Resume.model_validate(malicious_resume), "classic")["index.html"]
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_write_site_creates_files(tmp_path):
    out = tmp_path / "site"
    write_site({"index.html": "<h1>Hi</h1>", "style.css": "body {}"}, out)
    assert (out / "index.html").read_text() == "<h1>Hi</h1>"
    assert (out / "style.css").read_text() == "body {}"


def test_inline_css_embeds_the_stylesheet():
    files = {"index.html": '<head><link rel="stylesheet" href="style.css"></head>', "style.css": "body {}"}
    assert inline_css(files) == "<head><style>body {}</style></head>"
