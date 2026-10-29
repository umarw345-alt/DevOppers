from pathlib import Path
from typing import Literal, get_args

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from portfolio.schema import Entry, Resume

TemplateId = Literal["classic", "modern", "minimal", "dark"]
TEMPLATE_IDS = get_args(TemplateId)
TEMPLATES_DIR = Path(__file__).parent / "templates"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


class UnknownTemplateError(ValueError):
    pass


def format_date(value: str | None) -> str:
    if value is None:
        return "Present"
    parts = value.split("-")
    if len(parts) == 1:
        return parts[0]
    return f"{MONTHS[int(parts[1]) - 1]} {parts[0]}"


def date_range(entry: Entry) -> str:
    if entry.start is None:
        return format_date(entry.end) if entry.end else ""
    return f"{format_date(entry.start)} – {format_date(entry.end)}"


def remove_hidden(resume: Resume) -> Resume:
    """Return a copy of the resume with every field in hidden_fields blanked out,
    so private info (e.g. phone number) never ends up in the public HTML."""
    hidden = resume.hidden_fields
    contact = resume.contact.model_copy(
        update={f.removeprefix("contact."): None for f in hidden if f.startswith("contact.")}
    )
    sections = {
        f: None if f == "summary" else [] for f in hidden if not f.startswith("contact.")
    }
    return resume.model_copy(update={**sections, "contact": contact, "hidden_fields": []})


# Jinja setup shared by all templates. autoescape turns user text like "<script>"
# into harmless "&lt;script&gt;"; StrictUndefined makes typos in templates fail loudly.
env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=True,
    undefined=StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
)
env.filters["date_range"] = date_range


def render(resume: Resume, template_id: str) -> dict[str, str]:
    """Build the portfolio site for a resume using one of the TEMPLATE_IDS.
    Returns the site's files as {filename: contents}, ready to save or upload."""
    if template_id not in TEMPLATE_IDS:
        raise UnknownTemplateError(f"Unknown template: {template_id}")
    public = remove_hidden(resume)
    html = env.get_template(f"{template_id}/index.html").render(resume=public)
    css = (TEMPLATES_DIR / template_id / "style.css").read_text(encoding="utf-8")
    return {"index.html": html, "style.css": css}


def write_site(files: dict[str, str], out_dir: Path) -> None:
    """Save the files from render() into a folder, e.g. to preview a site locally."""
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        (out_dir / name).write_text(content, encoding="utf-8")
