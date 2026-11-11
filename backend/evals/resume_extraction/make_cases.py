"""Build the synthetic test resumes for the extraction comparison.

Each case is a made-up person whose correct answer (truth.json) is written by hand.
The resume file is rendered from that same data in different layouts (single column,
two-column sidebar, dense two-page, low-quality scan), so the file and the answer
always agree. Run from backend/:  uv run python -m evals.resume_extraction.make_cases
"""

import json
from pathlib import Path

import pymupdf

from portfolio.schema import Resume

HERE = Path(__file__).parent
CASES_DIR = HERE / "cases"
PAGE = pymupdf.paper_rect("letter")
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def entry(org, title, start, end, bullets=(), location=None):
    return {"organization": org, "title": title, "location": location, "start": start, "end": end, "bullets": list(bullets)}


PEOPLE = {
    "maya_patel": {
        "contact": {
            "name": "Maya Patel",
            "headline": "Software Engineering Student",
            "email": "maya.patel@example.com",
            "phone": "(408) 555-0142",
            "location": "San Jose, CA",
            "links": [{"label": "GitHub", "url": "https://github.com/mayapatel-dev"}],
        },
        "summary": "Computer engineering student who enjoys building reliable backend services and developer tools.",
        "education": [
            entry("San José State University", "B.S. Computer Engineering", "2022-08", "2026-05", ["GPA 3.7, Dean's List (4 semesters)"], "San Jose, CA"),
        ],
        "experience": [
            entry("Brightline Robotics", "Software Engineering Intern", "2025-06", "2025-08", [
                "Built a FastAPI service that streams telemetry from 40 warehouse robots",
                "Cut dashboard load time from 6s to 1.2s by adding Redis caching",
            ], "Fremont, CA"),
            entry("SJSU College of Engineering", "Peer Tutor", "2023-09", None, [
                "Tutor 15 students per week in data structures and C programming",
            ], "San Jose, CA"),
        ],
        "projects": [
            {"name": "StudySync", "description": "Real-time study group scheduler", "url": "https://github.com/mayapatel-dev/studysync",
             "bullets": ["React Native app with 300+ active users on campus"]},
            {"name": "Tiny Compiler", "description": "A compiler for a C subset written in Rust", "url": None, "bullets": []},
        ],
        "skills": ["Python", "Rust", "TypeScript", "FastAPI", "PostgreSQL", "Docker", "Git"],
        "hidden_fields": [],
    },
    "diego_ramirez": {
        "contact": {
            "name": "Diego Ramirez",
            "headline": "Product Designer",
            "email": "diego.r.design@example.com",
            "phone": "+1 415 555 0199",
            "location": "Oakland, CA",
            "links": [
                {"label": "Portfolio", "url": "https://diegoramirez.example.com"},
                {"label": "LinkedIn", "url": "https://linkedin.com/in/diego-ramirez-design"},
            ],
        },
        "summary": "Product designer with five years of experience turning messy workflows into calm, accessible interfaces.",
        "education": [
            entry("California College of the Arts", "BFA Interaction Design", "2015-09", "2019-05"),
        ],
        "experience": [
            entry("Fernway Health", "Senior Product Designer", "2023-03", None, [
                "Lead design for the patient intake flow used by 120 clinics",
                "Raised form completion from 61% to 84% after a usability study series",
                "Run a weekly design critique for a team of six designers",
            ], "Remote"),
            entry("Loop & Co.", "Product Designer", "2020-01", "2023-02", [
                "Designed the mobile checkout redesign that lifted conversion 12%",
                "Built the first shared component library in Figma",
            ], "San Francisco, CA"),
            entry("Studio Nueve", "Design Intern", "2019-06", "2019-12", [
                "Produced wireframes and prototypes for three client websites",
            ], "Oakland, CA"),
        ],
        "projects": [],
        "skills": ["Figma", "User research", "Prototyping", "Design systems", "Accessibility (WCAG)", "HTML/CSS"],
        "hidden_fields": [],
    },
    "priya_nair": {
        "contact": {
            "name": "Priya Nair",
            "headline": "Senior Product Manager",
            "email": "priya.nair.pm@example.com",
            "phone": "(650) 555-0177",
            "location": "Palo Alto, CA",
            "links": [{"label": "LinkedIn", "url": "https://linkedin.com/in/priyanair"}],
        },
        "summary": "Product manager with eleven years of experience shipping B2B analytics and payments products from zero to scale.",
        "education": [
            entry("University of Michigan, Ross School of Business", "MBA", "2014-09", "2016-05"),
            entry("University of Washington", "B.S. Informatics", "2008-09", "2012-06"),
        ],
        "experience": [
            entry("Ledgerline", "Senior Product Manager, Payments", "2021-04", None, [
                "Own the payouts roadmap for a product moving $2B per year",
                "Launched instant payouts in 14 countries with a team of 22 engineers",
                "Reduced failed payouts by 37% by redesigning bank verification",
                "Set quarterly OKRs with engineering, risk, and finance leads",
            ], "Palo Alto, CA"),
            entry("Metricly", "Product Manager", "2018-01", "2021-03", [
                "Shipped self-serve dashboards that became 40% of new revenue",
                "Ran 60+ customer interviews to shape the alerting product",
                "Introduced a beta program that shortened feedback cycles to one week",
            ], "Seattle, WA"),
            entry("Metricly", "Associate Product Manager", "2016-06", "2017-12", [
                "Managed the data connectors backlog across 9 integrations",
                "Wrote specs for the first public API",
            ], "Seattle, WA"),
            entry("Northwind Consulting", "Business Analyst", "2012-07", "2014-08", [
                "Built forecasting models for retail clients in Excel and SQL",
                "Presented findings to client executives every quarter",
            ], "Chicago, IL"),
            entry("Seattle Public Library", "Volunteer Tech Mentor", "2010-01", "2012-06", [
                "Taught weekly computer basics classes for adults",
            ], "Seattle, WA"),
        ],
        "projects": [],
        "skills": ["Product strategy", "SQL", "A/B testing", "Roadmapping", "Payments", "Stakeholder management", "Jira", "Amplitude"],
        "hidden_fields": [],
    },
    "kevin_osei": {
        "contact": {
            "name": "Kevin Osei",
            "headline": "Mechanical Engineer",
            "email": "kevin.osei@example.com",
            "phone": "(510) 555-0123",
            "location": "Hayward, CA",
            "links": [],
        },
        "summary": "Recent mechanical engineering graduate focused on product design and manufacturing.",
        "education": [
            entry("California State University, East Bay", "B.S. Mechanical Engineering", "2020-08", "2024-05"),
        ],
        "experience": [
            entry("Pacific Fabrication Inc.", "Manufacturing Engineer I", "2024-07", None, [
                "Designed fixtures in SolidWorks that cut assembly time by 18%",
                "Maintain work instructions for 30 machined parts",
            ], "Hayward, CA"),
            entry("Habitat for Humanity", "Construction Volunteer", "2021-01", "2023-12", [
                "Framed and roofed 6 homes with volunteer crews",
            ], "Oakland, CA"),
        ],
        "projects": [
            {"name": "Formula SAE Suspension", "description": "Designed the rear suspension for the university race car", "url": None,
             "bullets": ["Reduced unsprung mass by 2.3 kg"]},
        ],
        "skills": ["SolidWorks", "AutoCAD", "GD&T", "MATLAB", "CNC machining", "FEA"],
        "hidden_fields": [],
    },
    "lena_fischer": {
        "contact": {
            "name": "Lena Fischer",
            "headline": "Data Analyst",
            "email": "lena.fischer@example.com",
            "phone": "(408) 555-0188",
            "location": "Sunnyvale, CA",
            "links": [{"label": "GitHub", "url": "https://github.com/lenafischer"}],
        },
        "summary": "Data analyst who turns operations data into clear weekly decisions.",
        "education": [
            entry("UC Davis", "B.S. Statistics", "2017-09", "2021-06"),
        ],
        "experience": [
            entry("Greenleaf Grocers", "Data Analyst", "2022-02", None, [
                "Built the weekly inventory forecast used by 85 stores",
                "Automated 12 Excel reports with Python and dbt",
            ], "Sunnyvale, CA"),
            entry("UC Davis Library", "Student Data Assistant", "2019-09", "2021-06", [
                "Cleaned and published circulation datasets",
            ], "Davis, CA"),
        ],
        "projects": [],
        "skills": ["SQL", "Python", "pandas", "dbt", "Tableau", "Excel"],
        "hidden_fields": [],
    },
    "tom_baker": {
        "contact": {
            "name": "Tom Baker",
            "headline": None,
            "email": "tbaker2007@example.com",
            "phone": None,
            "location": "Santa Clara, CA",
            "links": [],
        },
        "summary": None,
        "education": [
            entry("Santa Clara High School", "High School Diploma", "2021", "2025"),
        ],
        "experience": [
            entry("Bayside Pizza", "Cashier", "2023", None, ["Handle orders and payments during evening shifts"]),
        ],
        "projects": [],
        "skills": ["Customer service", "Spanish (conversational)"],
        "hidden_fields": [],
    },
}

# (case id, person, layout, output format)
CASES = [
    ("maya_classic_pdf", "maya_patel", "classic", "pdf"),
    ("diego_sidebar_pdf", "diego_ramirez", "sidebar", "pdf"),
    ("priya_dense_pdf", "priya_nair", "dense", "pdf"),
    ("kevin_scan_jpg", "kevin_osei", "classic", "jpg"),
    ("lena_sidebar_jpg", "lena_fischer", "sidebar", "jpg"),
    ("tom_minimal_pdf", "tom_baker", "classic", "pdf"),
]


def fmt_date(value):
    if value is None:
        return "Present"
    if len(value) == 4:
        return value
    year, month = value[:4], int(value[5:7])
    return f"{MONTHS[month - 1]} {year}"


def entries_html(entries):
    html = ""
    for e in entries:
        where = f" — {e['location']}" if e.get("location") else ""
        html += (
            f"<p><b>{e['title']}</b>, {e['organization']}{where}<br/>"
            f"<i>{fmt_date(e['start'])} – {fmt_date(e['end'])}</i></p>"
        )
        if e["bullets"]:
            html += "<ul>" + "".join(f"<li>{b}</li>" for b in e["bullets"]) + "</ul>"
    return html


def links_text(links):
    # Show links the way people usually write them: no "https://".
    return " · ".join(link["url"].removeprefix("https://") for link in links)


def contact_lines(c):
    return [x for x in (c["email"], c["phone"], c["location"], links_text(c["links"]) or None) if x]


def projects_html(projects):
    html = ""
    for p in projects:
        url = f" ({p['url'].removeprefix('https://')})" if p["url"] else ""
        html += f"<p><b>{p['name']}</b>{url}: {p['description']}</p>"
        if p["bullets"]:
            html += "<ul>" + "".join(f"<li>{b}</li>" for b in p["bullets"]) + "</ul>"
    return html


def main_sections(r, include_education=True):
    html = ""
    if r["summary"]:
        html += f"<h2>Summary</h2><p>{r['summary']}</p>"
    if r["experience"]:
        html += "<h2>Experience</h2>" + entries_html(r["experience"])
    if r["projects"]:
        html += "<h2>Projects</h2>" + projects_html(r["projects"])
    if include_education and r["education"]:
        html += "<h2>Education</h2>" + entries_html(r["education"])
    return html


def classic_html(r):
    c = r["contact"]
    head = f"<h1>{c['name']}</h1>"
    if c["headline"]:
        head += f"<p><i>{c['headline']}</i></p>"
    head += f"<p>{' | '.join(contact_lines(c))}</p>"
    skills = f"<h2>Skills</h2><p>{', '.join(r['skills'])}</p>" if r["skills"] else ""
    return head + main_sections(r) + skills


CSS = {
    "classic": "* {font-family: sans-serif; font-size: 11px;} h1 {font-size: 22px;} h2 {font-size: 14px; margin-top: 10px;}",
    "dense": "* {font-family: serif; font-size: 9.5px;} h1 {font-size: 18px;} h2 {font-size: 12px; margin-top: 6px;}",
    "sidebar": "* {font-family: sans-serif; font-size: 10.5px;} h1 {font-size: 20px;} h2 {font-size: 13px; margin-top: 8px;}",
}


def write_flow(html, css, path):
    """Render HTML across as many pages as it needs."""
    story = pymupdf.Story(html=html, user_css=css)
    writer = pymupdf.DocumentWriter(str(path))
    more = True
    while more:
        device = writer.begin_page(PAGE)
        more, _ = story.place(PAGE + (54, 54, -54, -54))
        story.draw(device)
        writer.end_page()
    writer.close()


def write_sidebar(r, css, path):
    """One page with a narrow left column (contact, skills, education) and a wide right column."""
    c = r["contact"]
    left = f"<h1>{c['name']}</h1>"
    if c["headline"]:
        left += f"<p><i>{c['headline']}</i></p>"
    left += "<h2>Contact</h2>" + "".join(f"<p>{line}</p>" for line in contact_lines(c))
    left += "<h2>Skills</h2><ul>" + "".join(f"<li>{s}</li>" for s in r["skills"]) + "</ul>"
    left += "<h2>Education</h2>" + entries_html(r["education"])
    right = main_sections(r, include_education=False)

    writer = pymupdf.DocumentWriter(str(path))
    device = writer.begin_page(PAGE)
    for html, rect in ((left, pymupdf.Rect(40, 40, 210, PAGE.height - 40)), (right, pymupdf.Rect(235, 40, PAGE.width - 40, PAGE.height - 40))):
        story = pymupdf.Story(html=html, user_css=css)
        more, _ = story.place(rect)
        if more:
            raise RuntimeError(f"{path.name}: sidebar content does not fit on one page")
        story.draw(device)
    writer.end_page()
    writer.close()


def pdf_to_scan_jpg(pdf_path, jpg_path):
    """Low-resolution grayscale JPEG of page 1, like a phone photo or cheap scan."""
    with pymupdf.open(pdf_path) as doc:
        pix = doc[0].get_pixmap(dpi=110, colorspace=pymupdf.csGRAY)
        pix.save(str(jpg_path), jpg_quality=55)


def build():
    CASES_DIR.mkdir(exist_ok=True)
    for case_id, person, layout, fmt in CASES:
        truth = Resume.model_validate(PEOPLE[person])  # the answer must itself be valid
        case_dir = CASES_DIR / case_id
        case_dir.mkdir(exist_ok=True)
        (case_dir / "truth.json").write_text(truth.model_dump_json(indent=2), encoding="utf-8")

        pdf_path = case_dir / "resume.pdf"
        if layout == "sidebar":
            write_sidebar(PEOPLE[person], CSS["sidebar"], pdf_path)
        else:
            write_flow(classic_html(PEOPLE[person]), CSS[layout], pdf_path)

        if fmt == "jpg":
            pdf_to_scan_jpg(pdf_path, case_dir / "resume.jpg")
            pdf_path.unlink()
        print(f"built {case_id}")
    (CASES_DIR / "README.md").write_text(
        "Synthetic resumes for evals/resume_extraction. All people, emails and phone numbers are made up.\n"
        "Regenerate with: uv run python -m evals.resume_extraction.make_cases\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    build()
