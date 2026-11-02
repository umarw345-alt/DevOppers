import json
from pathlib import Path

from upload.schema import Resume


def test_sample_resume_matches_schema() -> None:
    sample_path = Path("upload/full_resume.json")
    data = json.loads(
        sample_path.read_text(encoding="utf-8")
    )

    resume = Resume.model_validate(data)

    assert resume.contact.name == "Jordan Lee"
    assert len(resume.education) == 1
    assert len(resume.experience) == 2
    assert resume.experience[1].end is None
