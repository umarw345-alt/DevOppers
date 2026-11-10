"""Turn an uploaded resume (PDF or JPEG/PNG) into the portfolio Resume JSON using Claude."""

import base64
import os
from dataclasses import dataclass

import anthropic
from pydantic import ValidationError

from portfolio.schema import Resume

DEFAULT_MODEL = "claude-haiku-5-5"
# Adaptive thinking (Haiku 5.5's default) at medium effort scored the same as high
# on evals/resume_extraction, a bit faster.
DEFAULT_EFFORT = "medium"

SUPPORTED_TYPES = {"application/pdf", "image/jpeg", "image/png"}

SYSTEM_PROMPT = """\
You read a resume and fill in JSON for a personal portfolio website. The person will \
review and edit the result before it is published, so accuracy matters more than \
completeness.

- Copy wording exactly as it appears: names, job titles, organizations, bullet points. \
Do not summarize, reword, fix, or invent anything. If something isn't in the resume, \
leave the field empty or null.
- Dates use ISO format: "June 2024" -> "2024-06", "2024" -> "2024", "Summer 2024" -> \
"2024". An ongoing role ("Present", "Current", "Now") has end = null.
- experience: jobs, internships, research, leadership and volunteer positions. \
education: schools and degrees, with the degree in `title` and the school in `organization`.
- bullets: one item per bullet point, without the bullet symbol.
- skills: one skill per item; split comma- or bullet-separated lists into separate items.
- contact.headline: the short professional title shown near the name, if there is one \
(80 characters max).
- contact.links: full URLs; add "https://" when the resume leaves it off. Use the site \
name as the label, e.g. "LinkedIn", "GitHub", "Portfolio".
- summary: the profile, summary, or objective paragraph, if there is one.
- hidden_fields: always an empty list."""


class ExtractionError(Exception):
    """The resume could not be turned into valid Resume JSON."""


@dataclass
class ExtractionResult:
    resume: Resume
    model: str
    input_tokens: int
    output_tokens: int


def _file_block(file_bytes: bytes, mime_type: str) -> dict:
    data = base64.standard_b64encode(file_bytes).decode("ascii")
    if mime_type == "application/pdf":
        return {"type": "document", "source": {"type": "base64", "media_type": mime_type, "data": data}}
    if mime_type in ("image/jpeg", "image/png"):
        return {"type": "image", "source": {"type": "base64", "media_type": mime_type, "data": data}}
    raise ValueError(f"Unsupported file type: {mime_type}")


def extract_resume(
    file_bytes: bytes,
    mime_type: str,
    *,
    model: str | None = None,
    effort: str | None = None,
    client: anthropic.Anthropic | None = None,
) -> ExtractionResult:
    """Send the file to Claude and return a validated Resume.

    Model and effort default to ANTHROPIC_MODEL / ANTHROPIC_EFFORT, then to Haiku 5.5 at medium effort.
    """
    client = client or anthropic.Anthropic()
    model = model or os.getenv("ANTHROPIC_MODEL", DEFAULT_MODEL)
    effort = effort or os.getenv("ANTHROPIC_EFFORT", DEFAULT_EFFORT)

    try:
        response = client.messages.parse(
            model=model,
            max_tokens=16000,
            system=SYSTEM_PROMPT,
            output_config={"effort": effort},
            output_format=Resume,
            messages=[
                {
                    "role": "user",
                    "content": [
                        _file_block(file_bytes, mime_type),
                        {"type": "text", "text": "Extract this resume."},
                    ],
                }
            ],
        )
    except ValidationError as error:
        # Claude returned JSON that breaks a schema rule (e.g. an end date before the start).
        raise ExtractionError(f"Extracted resume failed validation: {error.error_count()} error(s)") from error

    if response.stop_reason == "refusal":
        raise ExtractionError("The model declined to process this file")
    if response.stop_reason == "max_tokens":
        raise ExtractionError("The resume was too long to extract in one pass")
    if response.parsed_output is None:
        raise ExtractionError("The model did not return resume JSON")

    return ExtractionResult(
        resume=response.parsed_output,
        model=response.model,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
    )
