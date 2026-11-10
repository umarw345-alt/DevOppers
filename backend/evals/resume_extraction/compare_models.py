"""Compare Claude models on resume extraction against the hand-written answers in cases/.

Run from backend/ (costs real money; roughly $0.05 per Sonnet run of all cases):
    uv run --env-file ../.env python -m evals.resume_extraction.compare_models
    uv run --env-file ../.env python -m evals.resume_extraction.compare_models --runs 2 --config claude-haiku-5-5:medium

Scores are 0-100. Each case is the average of six sections: contact, summary,
experience, education, projects, skills. Results are saved to results/ (git-ignored).
"""

import argparse
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

import anthropic

from portfolio.schema import Resume
from resume.extractor import ExtractionError, extract_resume

HERE = Path(__file__).parent
CASES_DIR = HERE / "cases"
RESULTS_DIR = HERE / "results"

# $ per million tokens (input, output)
PRICES = {"claude-haiku-5-5": (0.10, 0.50), "claude-sonnet-5-5": (2.00, 10.00), "claude-opus-5-5": (4.00, 20.00)}
DEFAULT_CONFIGS = ["claude-haiku-5-5:high", "claude-sonnet-5-5:high"]
MIME = {".pdf": "application/pdf", ".jpg": "image/jpeg", ".png": "image/png"}


# ---------- scoring ----------

def norm(text):
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def sim(a, b):
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, norm(a), norm(b)).ratio()


def same(a, b):
    return 1.0 if norm(a) == norm(b) else 0.0


def digits(phone):
    return re.sub(r"\D", "", phone or "")[-10:]


def url_key(url):
    return re.sub(r"^(https?://)?(www\.)?", "", str(url or "").lower()).rstrip("/")


def set_f1(truth, pred):
    t, p = {norm(x) for x in truth}, {norm(x) for x in pred}
    if not t and not p:
        return 1.0
    if not t or not p:
        return 0.0
    hits = len(t & p)
    return 0.0 if hits == 0 else 2 * hits / (len(t) + len(p))


def bullets_score(truth, pred):
    """Fraction of bullets reproduced (near-)verbatim, penalizing extras."""
    if not truth and not pred:
        return 1.0
    if not truth or not pred:
        return 0.0
    used, hits = set(), 0
    for t in truth:
        best = max(((sim(t, p), i) for i, p in enumerate(pred) if i not in used), default=(0, None))
        if best[0] >= 0.9:
            hits += 1
            used.add(best[1])
    return hits / max(len(truth), len(pred))


def match_lists(truth, pred, key, score_pair):
    """Pair each true item with its most similar prediction; extra or missing items count as 0."""
    if not truth and not pred:
        return 1.0, []
    used, total, notes = set(), 0.0, []
    for t in truth:
        best = max(((sim(key(t), key(p)), i) for i, p in enumerate(pred) if i not in used), default=(0, None))
        if best[1] is None or best[0] < 0.6:
            notes.append(f"missing: {key(t)}")
            continue
        used.add(best[1])
        s, pair_notes = score_pair(t, pred[best[1]])
        total += s
        notes += pair_notes
    for i, p in enumerate(pred):
        if i not in used:
            notes.append(f"extra: {key(p)}")
    return total / max(len(truth), len(pred)), notes


def entry_pair(t, p):
    parts = {
        "organization": same(t.organization, p.organization),
        "title": same(t.title, p.title),
        "location": same(t.location, p.location),
        "start": same(t.start, p.start),
        "end": same(t.end, p.end),
        "bullets": bullets_score(t.bullets, p.bullets),
    }
    label = f"{t.title} @ {t.organization}"
    notes = [f"{label}: {k} expected {getattr(t, k)!r} got {getattr(p, k)!r}" for k, v in parts.items() if v < 1 and k != "bullets"]
    if parts["bullets"] < 1:
        notes.append(f"{label}: bullets {parts['bullets']:.0%}")
    return sum(parts.values()) / len(parts), notes


def project_pair(t, p):
    parts = {
        "name": same(t.name, p.name),
        "description": 1.0 if sim(t.description, p.description) >= 0.9 else 0.0,
        "url": 1.0 if url_key(t.url) == url_key(p.url) else 0.0,
        "bullets": bullets_score(t.bullets, p.bullets),
    }
    notes = [f"project {t.name}: {k} wrong" for k, v in parts.items() if v < 1]
    return sum(parts.values()) / len(parts), notes


def score(truth: Resume, pred: Resume):
    tc, pc = truth.contact, pred.contact
    contact_parts = {
        "name": same(tc.name, pc.name),
        "headline": same(tc.headline, pc.headline),
        "email": same(tc.email, pc.email),
        "phone": 1.0 if digits(tc.phone) == digits(pc.phone) else 0.0,
        "location": same(tc.location, pc.location),
        "links": set_f1([url_key(link.url) for link in tc.links], [url_key(link.url) for link in pc.links]),
    }
    notes = [f"contact.{k}: expected {getattr(tc, k)!r} got {getattr(pc, k)!r}" for k, v in contact_parts.items() if v < 1 and k != "links"]
    if contact_parts["links"] < 1:
        notes.append(f"contact.links: expected {[str(link.url) for link in tc.links]} got {[str(link.url) for link in pc.links]}")

    summary = 1.0 if sim(truth.summary, pred.summary) >= 0.9 else 0.0
    if summary < 1:
        notes.append(f"summary: expected {truth.summary!r} got {pred.summary!r}")
    experience, n1 = match_lists(truth.experience, pred.experience, lambda e: f"{e.title} {e.organization}", entry_pair)
    education, n2 = match_lists(truth.education, pred.education, lambda e: f"{e.title} {e.organization}", entry_pair)
    projects, n3 = match_lists(truth.projects, pred.projects, lambda p: p.name, project_pair)
    skills = set_f1(truth.skills, pred.skills)
    if skills < 1:
        notes.append(f"skills: expected {truth.skills} got {pred.skills}")

    sections = {
        "contact": sum(contact_parts.values()) / len(contact_parts),
        "summary": summary,
        "experience": experience,
        "education": education,
        "projects": projects,
        "skills": skills,
    }
    return sections, notes + n1 + n2 + n3


# ---------- running ----------

def load_cases():
    cases = []
    for case_dir in sorted(p for p in CASES_DIR.iterdir() if p.is_dir()):
        file = next(f for f in case_dir.iterdir() if f.name.startswith("resume."))
        truth = Resume.model_validate_json((case_dir / "truth.json").read_text(encoding="utf-8"))
        cases.append((case_dir.name, file, truth))
    return cases


def run_one(client, model, effort, case_id, file, truth, run):
    started = time.perf_counter()
    record = {"model": model, "effort": effort, "case": case_id, "run": run}
    try:
        result = extract_resume(file.read_bytes(), MIME[file.suffix], model=model, effort=effort, client=client)
    except (ExtractionError, anthropic.APIError) as error:
        record.update(error=f"{type(error).__name__}: {error}", seconds=time.perf_counter() - started, cost=0.0, score=0.0)
        return record
    sections, notes = score(truth, result.resume)
    price_in, price_out = PRICES[model]
    record.update(
        seconds=time.perf_counter() - started,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        cost=(result.input_tokens * price_in + result.output_tokens * price_out) / 1_000_000,
        sections=sections,
        score=100 * sum(sections.values()) / len(sections),
        notes=notes,
        output=result.resume.model_dump(mode="json"),
    )
    return record


def summarize(records, configs, cases):
    lines = ["| Model (effort) | Avg score | Worst case | Failures | Avg cost/resume | Avg seconds |", "|---|---|---|---|---|---|"]
    for model, effort in configs:
        rs = [r for r in records if r["model"] == model and r["effort"] == effort]
        per_case = {c: [r["score"] for r in rs if r["case"] == c] for c, _, _ in cases}
        worst = min(per_case.items(), key=lambda kv: sum(kv[1]) / len(kv[1]))
        lines.append(
            f"| {model} ({effort}) | {sum(r['score'] for r in rs) / len(rs):.1f} | "
            f"{worst[0]} {sum(worst[1]) / len(worst[1]):.0f} | {sum('error' in r for r in rs)} | "
            f"${sum(r['cost'] for r in rs) / len(rs):.4f} | {sum(r['seconds'] for r in rs) / len(rs):.1f} |"
        )
    lines += ["", "Per case (average over runs):", ""]
    header = "| Case | " + " | ".join(f"{m} ({e})" for m, e in configs) + " |"
    lines += [header, "|---" * (len(configs) + 1) + "|"]
    for case_id, _, _ in cases:
        cells = []
        for model, effort in configs:
            s = [r["score"] for r in records if r["model"] == model and r["effort"] == effort and r["case"] == case_id]
            cells.append(f"{sum(s) / len(s):.0f}")
        lines.append(f"| {case_id} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", action="append", help="model:effort, repeatable (default: Haiku and Sonnet at high)")
    parser.add_argument("--runs", type=int, default=1, help="repeat each case this many times")
    args = parser.parse_args()
    configs = [tuple(c.split(":")) for c in (args.config or DEFAULT_CONFIGS)]
    cases = load_cases()
    client = anthropic.Anthropic()

    jobs = [(m, e, cid, f, t, run) for m, e in configs for cid, f, t in cases for run in range(args.runs)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(lambda job: run_one(client, *job), jobs))

    table = summarize(records, configs, cases)
    print(table)
    print(f"\nTotal spent: ${sum(r['cost'] for r in records):.3f}")

    RESULTS_DIR.mkdir(exist_ok=True)
    (RESULTS_DIR / ".gitignore").write_text("*\n", encoding="utf-8")
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    (RESULTS_DIR / f"{stamp}.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
    (RESULTS_DIR / f"{stamp}.md").write_text(table + "\n", encoding="utf-8")
    print(f"Saved results/{stamp}.json")


if __name__ == "__main__":
    main()
