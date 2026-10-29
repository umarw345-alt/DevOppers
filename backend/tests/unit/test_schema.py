import pytest
from pydantic import ValidationError

from portfolio.schema import Entry, Resume


def test_full_resume_is_valid(full_resume):
    resume = Resume.model_validate(full_resume)
    assert resume.contact.name == "Jordan Lee"
    assert len(resume.experience) == 2
    assert resume.experience[1].end is None


def test_minimal_resume_defaults_to_empty_sections(minimal_resume):
    resume = Resume.model_validate(minimal_resume)
    assert resume.summary is None
    assert resume.education == []
    assert resume.experience == []
    assert resume.projects == []
    assert resume.skills == []
    assert resume.hidden_fields == []


def test_name_is_required():
    with pytest.raises(ValidationError):
        Resume.model_validate({"contact": {}})


def test_empty_name_is_rejected():
    with pytest.raises(ValidationError):
        Resume.model_validate({"contact": {"name": ""}})


def test_invalid_email_is_rejected():
    with pytest.raises(ValidationError):
        Resume.model_validate({"contact": {"name": "A", "email": "not-an-email"}})


@pytest.mark.parametrize("url", ["javascript:alert(1)", "not a url", "ftp://example.com"])
def test_unsafe_link_urls_are_rejected(url):
    with pytest.raises(ValidationError):
        Resume.model_validate(
            {"contact": {"name": "A", "links": [{"label": "x", "url": url}]}}
        )


@pytest.mark.parametrize("value", ["2024", "2024-06", "2024-06-15"])
def test_iso_dates_are_accepted(value):
    assert Entry(organization="X", start=value).start == value


@pytest.mark.parametrize("value", ["June 2024", "06/2024", "Present", "24-06"])
def test_non_iso_dates_are_rejected(value):
    with pytest.raises(ValidationError):
        Entry(organization="X", start=value)


def test_end_before_start_is_rejected():
    with pytest.raises(ValidationError):
        Entry(organization="X", start="2025-06", end="2024-01")


def test_same_month_with_different_precision_is_allowed():
    entry = Entry(organization="X", start="2025-06-15", end="2025-06")
    assert entry.end == "2025-06"


def test_open_ended_entry_is_allowed():
    assert Entry(organization="X", start="2025-06", end=None).end is None


def test_known_hidden_fields_are_accepted(full_resume):
    full_resume["hidden_fields"] = ["contact.phone", "projects"]
    resume = Resume.model_validate(full_resume)
    assert resume.hidden_fields == ["contact.phone", "projects"]


def test_unknown_hidden_field_is_rejected(full_resume):
    full_resume["hidden_fields"] = ["contact.ssn"]
    with pytest.raises(ValidationError):
        Resume.model_validate(full_resume)
