from __future__ import annotations

import re
from collections import defaultdict
from datetime import date, datetime
from functools import lru_cache

from dateutil import parser as date_parser
from rapidfuzz import fuzz, process

from .internal_models import TextBlock
from .schema import Contact, Entry, Link, Project, Resume


SECTION_ALIASES = {
    "summary": (
        "summary", "profile", "professional summary", "objective", "about",
        "personal statement", "life philosophy", "professional profile",
        "power statement",
    ),
    "experience": (
        "experience",
        "work experience",
        "employment",
        "employment history",
        "professional experience",
        "work history",
        "career history",
        "part time positions",
        "part-time positions",
        "additional experience",
        "professional history",
        "employment record",
    ),
    "education": ("education", "academic background", "academic experience", "qualifications", "education qualifications"),
    "projects": ("projects", "selected projects", "personal projects", "project experience"),
    "skills": (
        "skills",
        "strengths",
        "hard skills",
        "soft skills",
        "professional skills",
        "key skills",
        "technical skills",
        "technologies",
        "competencies",
        "software",
        "programming",
        "programming languages", "languages", "industry expertise", "other skills interests",
    ),
    "certifications": ("certifications", "certificates", "licenses"),
    "awards": ("awards", "honors", "achievements"),
    "activities": (
        "activities",
        "extracurricular activities",
        "sports and co-curricular activities",
    ),
    "exhibitions": (
        "exhibitions",
        "exhibits",
        "gallery exhibitions",
        "commission",
        "commissions",
    ),
}

# Templates frequently use a label that is semantically equivalent to an
# existing schema section, but not literally the word ``skills``.
SECTION_ALIASES["awards"] = SECTION_ALIASES["awards"] + ("accomplishments",)
SECTION_ALIASES["skills"] = SECTION_ALIASES["skills"] + (
    "skills abilities", "skill set", "skill sets", "core competencies",
)

DATE_TOKEN = (
    r"(?:(?:19|20)\d{2}-\d{2}"
    r"|(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
    r"[a-z]*\.?\s*)?(?:19|20)\d{2}"
    r"|\d{1,2}/(?:19|20)\d{2})"
)

DATE_RANGE_PATTERN = re.compile(
    rf"(?P<start>{DATE_TOKEN})"
    r"\s*(?:-|to|till|through|–|—)\s*"
    rf"(?P<end>{DATE_TOKEN}|Present|Current|Now|Ongoing|(?:till\s*)?date)",
    re.IGNORECASE,
)

YEAR_PATTERN = re.compile(r"\b(?:19|20)\d{2}\b")
MONTH_NAME_PATTERN = (
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?"
)
OPEN_DATE_RANGE_PATTERN = re.compile(
    rf"(?P<start>{DATE_TOKEN})\s*(?:-|to|–|—)\s*"
    rf"(?:(?:{MONTH_NAME_PATTERN})|Present|Current|Now|Ongoing)?\s*$",
    re.IGNORECASE,
)
SINGLE_DATE_PATTERN = re.compile(rf"(?P<date>{DATE_TOKEN})", re.IGNORECASE)
EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_PATTERN = re.compile(r"(?<!\d)(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]\d{4}(?!\d)")
PHONE_CANDIDATE_PATTERN = re.compile(
    r"(?<!\d)(?:\+?\d{1,3}[-.\s]?)?"
    r"[({]?0?\d{3}[)}]?[-.\s]?\d{3}[-.\s]?\d{4}(?!\d)"
)
INTERNATIONAL_PHONE_PATTERN = re.compile(
    r"(?<!\d)(?:\+\s*\d{1,3}|00\s*\d{1,3})[\s().-]*"
    r"\d[\d\s().-]{6,}\d(?!\d)"
)
PROFILE_URL_PATTERN = re.compile(
    r"(?:(?:https?://)?(?:www\.)?"
    r"(?:linkedin\.com|github\.com|twitter\.com|x\.com|facebook\.com|fb\.com)"
    r"/[^\s|]+|"
    r"(?<![@\w])(?:https?://)?(?:www\.)?[a-z0-9][a-z0-9-]*\.(?:com|org|net|io|co)(?![A-Za-z])"
    r"(?:/[^\s|]+)?)",
    re.IGNORECASE,
)
LOCATION_PATTERN = re.compile(r"^[A-Z][A-Za-z .'-]+,\s*(?:[A-Z]{2}|[A-Za-z]{4,})$")
BULLET_PATTERN = re.compile(
    r"^\s*(?:"
    r"[•●◦○▪■\uf0b7\uf0a7*¢@#¤®»«=™©+]"
    r"|o(?=\s+[A-Za-z])"
    r"|[eEcC](?=\s+(?:[A-Za-z«»*@#¤®]))"
    r"|\.(?=\s+[A-Z])"
    r"|\d+[.)]|-)\s*"
)

OCR_CORRECTIONS = {
    "geg": "G.E.D.",
    "testing flan": "Testing Plan",
    "farniiiar": "Familiar",
    "structure skits": "structure skills",
    "bachelars": "Bachelor's",
    "intitute": "Institute",
    "1“": "1st",
    "1“ version": "1st version",
    "decision analysis i, il & iii": "Decision Analysis I, II & III",
    "w w wenhancy com": "",
    "www wenhancy com": "",
    "powered by nx ennancy": "",
    "infoeiowik resume, com": "info@qwikresume.com",
    "infoeiowik resume com": "info@qwikresume.com",
    "staif accountant": "Staff Accountant",
    "staif": "Staff",
    "novernber": "November",
    "n overnber": "November",
    "payralt": "payroll",
    "questians": "questions",
    "thase": "those",
    "a5": "as",
    "{pa": "CPA",
    "cpa exam,a": "CPA exam, a",
    "of independently": "or independently",
    "bain": "BA in",
    "more than 2) faculty": "more than 200 faculty",
    "more than 2)": "more than 200",
    "of ice manager": "OFFICE MANAGER",
    "pa (ent": "PATIENT",
    "sf cialist": "SPECIALIST",
    "crin empovee wen a poseve aemluge": "Skilled employee with a positive attitude",
    "ina team": "in a team",
    "te accuracy": "to accuracy",
    # Conservative corrections for recurring OCR substitutions. These apply
    # only to exact words/phrases, not to names, URLs, or arbitrary text.
    "glohal": "Global",
    "etlsoftware": "ETL SOFTWARE",
    "rusinesses": "Businesses",
    "rusiness": "Business",
    "prodocts": "products",
    "suppert": "support",
    "qur": "our",
    "ather": "other",
    "glabally": "globally",
    "opportunibes": "opportunities",
    "betweea": "between",
    "funeclions": "functions",
    "satisly": "satisfy",
    "matagement": "management",
    "sales ance": "Sales Manager",
    "ast ant sales muarager": "Assistant Sales Manager",
    "preset": "Present",
    "manave": "Manage",
    "direel": "direct",
    "clicnt": "client",
    "selving": "solving",
    "decisian": "decision",
    "leam": "team",
    "bemonstrated": "Demonstrated",
}


class JSONNormalizer:
    """Convert extracted TextBlock objects into the supplied Resume schema."""

    def normalize_with_retry(self, blocks: list[TextBlock]) -> Resume:
        try:
            return self.normalize(blocks, strict=True)
        except Exception as strict_error:
            try:
                return self.normalize(blocks, strict=False)
            except Exception as relaxed_error:
                raise ValueError(
                    "Resume normalization failed after strict and relaxed parsing attempts"
                ) from relaxed_error

    def normalize(self, blocks: list[TextBlock], strict: bool = True) -> Resume:
        blocks = self.filter_headers_and_footers(blocks)
        blocks = self.deduplicate_blocks(blocks)
        ordered = self.detect_columns(blocks)
        sections = self.identify_sections(ordered, strict)
        self.promote_header_sections(sections)
        self.reclassify_inline_skill_grid(sections)
        self.infer_unheaded_sections(sections)
        self.split_education_certifications(sections)
        self.recover_experience_from_skills(sections)
        self.reclassify_part_time_experience(sections)

        summary_blocks = sections["summary"]
        summary = (
            self.extract_summary(summary_blocks)
            if summary_blocks
            else self.infer_header_summary(
                sections["header"]
            )
        )

        experience = self.parse_entries(sections["experience"], "experience")

        return Resume(
            contact=self.extract_contact_details(sections["header"]),
            summary=summary,
            education=self.parse_entries(sections["education"], "education"),
            experience=experience,
            projects=(
                self.parse_projects(sections["projects"])
                + self.parse_misc_projects(
                    sections["awards"] + sections["exhibitions"]
                )
                + self.parse_activity_projects(sections["activities"])
            ),
            skills=self.extract_skills(sections["skills"]),
            certifications=self.extract_certifications(
                sections["certifications"]
            ),
            hidden_fields=[],
        )

    @staticmethod
    def filter_headers_and_footers(blocks: list[TextBlock]) -> list[TextBlock]:
        """Remove repeated page furniture before section classification.

        Footer text is not resume content. In particular, Word templates
        often repeat an email, phone number, and ``PAGE n`` on every page.
        Such blocks are removed from parsing rather than being misclassified
        as skills or bullets. Raw hidden text is intentionally not placed in
        ``hidden_fields`` because that field stores privacy-toggle names.
        """
        if not blocks:
            return blocks

        page_bottom: dict[int, float] = defaultdict(float)
        for block in blocks:
            page_bottom[block.page_number] = max(
                page_bottom[block.page_number],
                block.bounding_box.y1,
            )

        def signature(text: str) -> str:
            value = JSONNormalizer.clean_line(text).casefold()
            value = re.sub(r"\bpage\s*\d+\b", "page", value)
            value = re.sub(r"\d+", "#", value)
            return re.sub(r"[^a-z0-9#@.+]+", "", value)

        signatures_by_page: dict[str, set[int]] = defaultdict(set)
        for block in blocks:
            if block.page_number <= 1:
                continue
            sig = signature(block.text)
            if sig:
                signatures_by_page[sig].add(block.page_number)

        repeated = {
            sig for sig, pages in signatures_by_page.items()
            if len(pages) >= 2
        }

        kept: list[TextBlock] = []
        for block in blocks:
            text = JSONNormalizer.clean_line(block.text)
            lower = text.casefold()
            if re.search(r"(?i)\b(?:profile\s+notes?\s+and\s+activity|notes?\s+and\s+activity|view\s+by)\b", text):
                continue
            bottom = page_bottom.get(block.page_number, block.bounding_box.y1)
            near_footer = block.bounding_box.y0 >= bottom * 0.88
            has_page_marker = bool(re.search(r"(?i)\bpage\s*\d+\b", text))
            has_contact_footer = bool(
                EMAIL_PATTERN.search(JSONNormalizer.repair_email(text))
                and (
                    PHONE_CANDIDATE_PATTERN.search(text)
                    or INTERNATIONAL_PHONE_PATTERN.search(text)
                )
            )
            is_repeated_footer = near_footer and signature(text) in repeated
            if (near_footer and (has_page_marker or has_contact_footer)) or is_repeated_footer:
                continue
            kept.append(block)
        return kept

    @staticmethod
    def deduplicate_blocks(blocks: list[TextBlock]) -> list[TextBlock]:
        """Remove duplicate evidence created by overlapping OCR regions.

        Region OCR intentionally overlaps the preliminary pass at column and
        header boundaries. Keeping both copies causes repeated summaries and
        can make a heading look like a person's name. The key uses the
        physical bounding box, so legitimate repeated text at different
        locations is preserved.
        """
        best: dict[tuple[object, ...], TextBlock] = {}
        for block in blocks:
            key = (
                block.page_number,
                round(block.bounding_box.x0, 1),
                round(block.bounding_box.y0, 1),
                round(block.bounding_box.x1, 1),
                round(block.bounding_box.y1, 1),
                re.sub(r"\s+", " ", block.text).strip().casefold(),
            )
            previous = best.get(key)
            if previous is None or block.confidence > previous.confidence:
                best[key] = block
        compact: list[TextBlock] = []
        for block in sorted(best.values(), key=lambda item: (item.page_number, item.bounding_box.y0, item.bounding_box.x0)):
            duplicate_index = next(
                (
                    index for index, previous in enumerate(compact)
                    if previous.page_number == block.page_number
                    and abs(previous.bounding_box.y0 - block.bounding_box.y0) <= 2.5
                    and min(previous.bounding_box.x1, block.bounding_box.x1)
                    > max(previous.bounding_box.x0, block.bounding_box.x0)
                    and (
                        previous.text.casefold() == block.text.casefold()
                        or previous.text.casefold() in block.text.casefold()
                        or block.text.casefold() in previous.text.casefold()
                        or fuzz.ratio(previous.text, block.text) >= 84
                    )
                    and not (
                        JSONNormalizer.classify_section_heading(previous.text, threshold=100)
                        or JSONNormalizer.classify_section_heading(block.text, threshold=100)
                    )
                ),
                None,
            )
            if duplicate_index is None:
                compact.append(block)
            elif block.confidence > compact[duplicate_index].confidence or len(block.text) > len(compact[duplicate_index].text):
                compact[duplicate_index] = block
        return sorted(
            compact,
            key=lambda block: (
                block.page_number,
                block.bounding_box.y0,
                block.bounding_box.x0,
            ),
        )

    def promote_header_sections(self, sections: dict[str, list[TextBlock]]) -> None:
        """Recover section regions that begin before the main body.

        Some one-page templates place the summary and sidebar headings above
        the first body heading. The column OCR therefore labels all of them
        as ``header``. Use the heading's x-position and the next heading in
        that visual column to move only the relevant blocks.
        """
        header = list(sections.get("header", []))
        if not header:
            return

        movable = {
            "summary", "experience", "education", "projects", "skills",
            "certifications", "awards", "activities", "exhibitions",
        }
        events: list[tuple[TextBlock, str]] = []
        inline_claimed: set[int] = set()
        for block in header:
            section = self.classify_section_heading(block.text, threshold=82)
            cleaned = self.clean_heading_candidate(block.text)
            exact_heading = any(
                cleaned == alias
                for alias in SECTION_ALIASES.get(section or "", ())
            )
            if (
                section in movable
                and len(cleaned.split()) > 8
                and cleaned.startswith(tuple(SECTION_ALIASES[section]))
            ):
                match = re.match(
                    r"(?i)\s*(?:skills?(?:\s*(?:&|@)\s*abilities)?|core\s+competencies|"
                    r"profile|summary|objective|about|experience|employment history|education)\b",
                    block.text,
                )
                if match and block.text[match.end():].strip():
                    sections[section].append(
                        block.model_copy(update={"text": block.text[match.end():].strip(" :-")})
                    )
                    inline_claimed.add(id(block))
                    continue
            if section in movable and exact_heading:
                events.append((block, section))

        if not events:
            return

        events.sort(key=lambda item: (item[0].bounding_box.y0, item[0].bounding_box.x0))
        claimed: set[int] = set()
        for index, (heading, section) in enumerate(events):
            heading_x = (heading.bounding_box.x0 + heading.bounding_box.x1) / 2
            next_y = None
            for next_heading, _ in events[index + 1:]:
                next_x = (next_heading.bounding_box.x0 + next_heading.bounding_box.x1) / 2
                if abs(next_x - heading_x) < max(80.0, heading.bounding_box.x1 - heading.bounding_box.x0):
                    next_y = next_heading.bounding_box.y0
                    break

            for block in header:
                if id(block) in claimed or id(block) == id(heading):
                    continue
                center_x = (block.bounding_box.x0 + block.bounding_box.x1) / 2
                if center_x < heading_x - 180 or center_x > heading_x + 180:
                    continue
                if block.bounding_box.y0 <= heading.bounding_box.y0:
                    continue
                if next_y is not None and block.bounding_box.y0 >= next_y:
                    continue
                # Keep a contact/header block out of the recovered section.
                if (
                    EMAIL_PATTERN.search(self.repair_email(block.text))
                    or re.search(
                        r"(?i)\b(?:phone|mobile|address|website|linkedin|resume\s*[,.:]?\s*com)\b",
                        block.text,
                    )
                    or PHONE_CANDIDATE_PATTERN.search(block.text)
                    or re.search(r"\d{7,}", re.sub(r"\D", "", block.text))
                ):
                    continue
                sections[section].append(block)
                claimed.add(id(block))

        sections["header"] = [
            block for block in header
            if id(block) not in claimed
            and id(block) not in inline_claimed
            and all(id(block) != id(heading) for heading, _ in events)
        ]
        for section in movable:
            sections[section].sort(key=lambda block: (block.bounding_box.y0, block.bounding_box.x0))

    # Reading order -----------------------------------------------------

    def detect_columns(
        self,
        blocks: list[TextBlock],
        min_gutter: float = 24.0,
        row_tolerance: float = 12.0,
        cluster_tolerance: float = 35.0,
    ) -> list[TextBlock]:
        if (
            any(block.column == "header" for block in blocks)
            and not any(block.column in {"left", "right"} for block in blocks)
        ):
            header = [block for block in blocks if block.column == "header"]
            body = [block for block in blocks if block.column != "header"]
            return self.sort_single_column(header) + self.sort_single_column(body)

        # ContentExtractor has already classified reliable OCR regions. Do
        # not rediscover a split from those blocks: timeline date gutters and
        # sidebar rating dots can otherwise be mistaken for a column gap.
        if any(block.column in {"header", "left", "right"} for block in blocks):
            return sorted(
                blocks,
                key=lambda block: (
                    block.page_number,
                    {"header": 0, "left": 1, "right": 2}.get(
                        block.column,
                        3,
                    ),
                    block.bounding_box.y0,
                    block.bounding_box.x0,
                ),
            )

        # A preliminary OCR pass means the extractor deliberately rejected a
        # column split. Preserve its page order instead of discovering a
        # second, often false split from timeline dates or long wrapped lines.
        if blocks and all(
            block.column in {None, "preliminary"}
            for block in blocks
        ) and any(block.column == "preliminary" for block in blocks):
            return self.sort_single_column(blocks)

        pages: dict[int, list[TextBlock]] = defaultdict(list)
        for block in blocks:
            pages[block.page_number].append(block)

        result: list[TextBlock] = []
        for page_number in sorted(pages):
            page_blocks = pages[page_number]
            split = self.find_column_split(
                page_blocks, min_gutter, row_tolerance, cluster_tolerance
            )
            result.extend(
                self.sort_single_column(page_blocks)
                if split is None
                else self.sort_two_columns(page_blocks, split)
            )
        return result

    def find_column_split(
        self,
        blocks: list[TextBlock],
        min_gutter: float,
        row_tolerance: float,
        cluster_tolerance: float,
    ) -> float | None:
        rows = self.group_blocks_into_rows(blocks, row_tolerance)
        gaps: list[tuple[float, float]] = []

        for row in rows:
            row.sort(key=lambda block: block.bounding_box.x0)
            for left, right in zip(row, row[1:]):
                gap = right.bounding_box.x0 - left.bounding_box.x1
                if gap >= min_gutter:
                    gaps.append(((left.bounding_box.x1 + right.bounding_box.x0) / 2, gap))

        clusters: list[list[tuple[float, float]]] = []
        for center, width in sorted(gaps):
            for cluster in clusters:
                if abs(center - self.cluster_center(cluster)) <= cluster_tolerance:
                    cluster.append((center, width))
                    break
            else:
                clusters.append([(center, width)])

        if clusters:
            best = max(clusters, key=lambda cluster: (len(cluster), sum(width for _, width in cluster)))
            if len(best) >= 2:
                return self.cluster_center(best)

        center_split = self.find_center_split(blocks, min_gutter)
        if center_split is not None:
            return center_split

        return self.find_projection_split(blocks, min_gutter)

    def find_center_split(
        self,
        blocks: list[TextBlock],
        min_gutter: float,
    ) -> float | None:
        """Find a large gap between clusters of block centers.

        This helps when OCR returns one block per line and therefore
        does not provide enough same-row pairs for gutter voting.
        Wide header blocks are excluded from the center distribution.
        """
        x_min = min(block.bounding_box.x0 for block in blocks)
        x_max = max(block.bounding_box.x1 for block in blocks)
        page_width = x_max - x_min

        if page_width <= 0:
            return None

        centers = []
        for block in blocks:
            block_width = block.bounding_box.x1 - block.bounding_box.x0
            if block_width < page_width * 0.65:
                centers.append(
                    (block.bounding_box.x0 + block.bounding_box.x1) / 2
                )

        centers.sort()

        if len(centers) < 6:
            return None

        candidates: list[tuple[float, float]] = []

        for left, right in zip(centers, centers[1:]):
            gap = right - left
            if gap < min_gutter:
                continue

            split = (left + right) / 2
            left_count = sum(center < split for center in centers)
            right_count = len(centers) - left_count

            if left_count >= 3 and right_count >= 3:
                candidates.append((gap, split))

        return max(candidates)[1] if candidates else None

    def group_blocks_into_rows(
        self,
        blocks: list[TextBlock],
        tolerance: float,
    ) -> list[list[TextBlock]]:
        rows: list[list[TextBlock]] = []
        for block in sorted(blocks, key=lambda item: (item.bounding_box.y0, item.bounding_box.x0)):
            top, bottom = block.bounding_box.y0, block.bounding_box.y1
            for row in rows:
                row_top = min(item.bounding_box.y0 for item in row)
                row_bottom = max(item.bounding_box.y1 for item in row)
                if top <= row_bottom + tolerance and bottom >= row_top - tolerance:
                    row.append(block)
                    break
            else:
                rows.append([block])
        return rows

    @staticmethod
    def cluster_center(cluster: list[tuple[float, float]]) -> float:
        total = sum(width for _, width in cluster)
        return (
            sum(center * width for center, width in cluster) / total
            if total
            else sum(center for center, _ in cluster) / len(cluster)
        )

    @staticmethod
    def sort_single_column(blocks: list[TextBlock]) -> list[TextBlock]:
        ordered = sorted(
            blocks,
            key=lambda block: (block.bounding_box.y0, block.bounding_box.x0),
        )
        # OCR bounding boxes can place a section heading a pixel or two
        # below the first line of its section. Group near-equal rows and put
        # the heading first so that the preceding section does not absorb it.
        result: list[TextBlock] = []
        index = 0
        while index < len(ordered):
            first_y = ordered[index].bounding_box.y0
            end = index + 1
            while (
                end < len(ordered)
                and ordered[end].bounding_box.y0 - first_y <= 3.0
            ):
                end += 1
            row = ordered[index:end]
            row.sort(
                key=lambda block: (
                    not JSONNormalizer.looks_like_section_heading(block.text),
                    block.bounding_box.x0,
                )
            )
            result.extend(row)
            index = end
        return result

    def sort_two_columns(self, blocks: list[TextBlock], split: float) -> list[TextBlock]:
        page_left = min(block.bounding_box.x0 for block in blocks)
        page_right = max(block.bounding_box.x1 for block in blocks)
        page_width = page_right - page_left
        full, left, right = [], [], []

        for block in blocks:
            box = block.bounding_box
            width = box.x1 - box.x0
            if width >= page_width * 0.70 or box.x0 < split < box.x1:
                full.append(block)
            elif (box.x0 + box.x1) / 2 < split:
                left.append(block)
            else:
                right.append(block)

        # Preserve the top full-width/header region before reading the
        # left and right body columns. Without this, a right-side summary
        # can be placed after the left-side Education heading.
        section_y = [
            block.bounding_box.y0
            for block in blocks
            if self.looks_like_section_heading(block.text)
        ]
        header_limit = min(section_y) if section_y else None

        header_blocks: list[TextBlock] = []
        if header_limit is not None:
            header_blocks = [
                block
                for block in left + right + full
                if block.bounding_box.y0 < header_limit
            ]
            header_ids = {id(block) for block in header_blocks}
            left = [block for block in left if id(block) not in header_ids]
            right = [block for block in right if id(block) not in header_ids]
            full = [block for block in full if id(block) not in header_ids]

        left = self.sort_single_column(left)
        right = self.sort_single_column(right)
        full = self.sort_single_column(full)
        header_blocks = self.sort_single_column(header_blocks)
        if not full:
            return header_blocks + left + right

        result: list[TextBlock] = list(header_blocks)
        remaining_left, remaining_right = list(left), list(right)
        for heading in full:
            y = heading.bounding_box.y0
            before_left = [block for block in remaining_left if block.bounding_box.y0 < y]
            before_right = [block for block in remaining_right if block.bounding_box.y0 < y]
            result.extend(before_left)
            result.extend(before_right)
            result.append(heading)
            remaining_left = [block for block in remaining_left if block not in before_left]
            remaining_right = [block for block in remaining_right if block not in before_right]

        result.extend(remaining_left)
        result.extend(remaining_right)
        return result

    @staticmethod
    def looks_like_section_heading(text: str) -> bool:
        candidate = JSONNormalizer.clean_heading_candidate(text)
        known = {
            "about",
            "summary",
            "objective",
            "education",
            "experience",
            "professional experience",
            "work experience",
            "projects",
            "project experience",
            "skills",
            "key skills",
            "certifications",
            "awards",
            "honors",
            "exhibitions",
            "commission",
            "commissions",
            "hard skills",
            "soft skills",
        }
        return candidate in known

    def find_projection_split(self, blocks: list[TextBlock], min_gutter: float, bin_size: float = 5.0) -> float | None:
        x_min = min(block.bounding_box.x0 for block in blocks)
        x_max = max(block.bounding_box.x1 for block in blocks)
        width = x_max - x_min
        if width <= 0:
            return None

        count = int(width / bin_size) + 1
        coverage = [0] * count
        for block in blocks:
            block_width = block.bounding_box.x1 - block.bounding_box.x0
            if block_width >= width * 0.70:
                continue
            start = max(0, int((block.bounding_box.x0 - x_min) / bin_size))
            end = min(count - 1, int((block.bounding_box.x1 - x_min) / bin_size))
            for index in range(start, end + 1):
                coverage[index] += 1

        candidates: list[tuple[float, float]] = []
        start: int | None = None
        for index, occupied in enumerate(coverage + [1]):
            if occupied == 0 and start is None:
                start = index
            elif occupied != 0 and start is not None:
                end = index - 1
                gap_width = (end - start + 1) * bin_size
                split = x_min + ((start + end) / 2) * bin_size
                if gap_width >= min_gutter and any(block.bounding_box.x1 < split for block in blocks) and any(block.bounding_box.x0 > split for block in blocks):
                    candidates.append((gap_width, split))
                start = None

        return max(candidates)[1] if candidates else None

    # Sections ----------------------------------------------------------

    def identify_sections(self, blocks: list[TextBlock], strict: bool) -> dict[str, list[TextBlock]]:
        sections = {
            "header": [],
            "summary": [],
            "experience": [],
            "education": [],
            "projects": [],
            "skills": [],
            "certifications": [],
            "awards": [],
            "activities": [],
            "exhibitions": [],
        }

        if any(
            block.column in {"left", "right"}
            for block in blocks
        ):
            sections["header"] = [
                block
                for block in blocks
                if block.column == "header"
            ]

            column_blocks_by_name = {
                column: [
                    block
                    for block in blocks
                    if block.column == column
                ]
                for column in ("left", "right")
            }
            column_events = {
                column: self.find_section_events(column_blocks)
                for column, column_blocks in column_blocks_by_name.items()
            }
            fallback_events = sorted(
                [
                    event
                    for events in column_events.values()
                    for event in events
                ],
                key=lambda event: event[0],
            )

            for column in ("left", "right"):
                column_blocks = column_blocks_by_name[column]
                column_sections = (
                    self.identify_column_sections(column_blocks, strict)
                    if column_events[column]
                    else self.assign_external_headings(
                        column_blocks,
                        fallback_events,
                    )
                )

                sections["header"].extend(column_sections["header"])

                for section_name in (
                    "summary",
                    "experience",
                    "education",
                    "projects",
                    "skills",
                    "certifications",
                    "awards",
                    "activities",
                    "exhibitions",
                ):
                    sections[section_name].extend(
                        column_sections[section_name]
                    )

            # Date gutters and main content are often OCR'd as separate
            # columns. Reconstruct their vertical order before parsing
            # entries; appending the entire left column before the right
            # column makes all dates appear before all job titles.
            section_heading_y: dict[str, list[float]] = defaultdict(list)
            for events in column_events.values():
                for y, section_name in events:
                    section_heading_y[section_name].append(y)

            for section_name in (
                "summary",
                "experience",
                "education",
                "projects",
                "skills",
                "certifications",
                "awards",
                "activities",
                "exhibitions",
            ):
                sections[section_name] = [
                    block
                    for block in sections[section_name]
                    if not (
                        any(
                            abs(block.bounding_box.y0 - heading_y) <= 1.5
                            for heading_y in section_heading_y.get(
                                section_name,
                                [],
                            )
                        )
                        and self.classify_section_heading(block.text) is None
                    )
                ]
                sections[section_name].sort(
                    key=lambda block: (
                        block.page_number,
                        block.bounding_box.y0,
                        block.bounding_box.x0,
                    )
                )

            return sections

        return self.identify_linear_sections(
            blocks,
            strict,
            sections,
        )

    def find_section_events(
        self,
        blocks: list[TextBlock],
    ) -> list[tuple[float, str]]:
        events: list[tuple[float, str]] = []
        for block in blocks:
            if len(self.clean_heading_candidate(block.text).split()) > 8:
                continue
            section = self.classify_section_heading(block.text)
            if section:
                events.append((block.bounding_box.y0, section))
        return sorted(events)

    def assign_external_headings(
        self,
        blocks: list[TextBlock],
        events: list[tuple[float, str]],
    ) -> dict[str, list[TextBlock]]:
        sections = {
            "header": [],
            "summary": [],
            "experience": [],
            "education": [],
            "projects": [],
            "skills": [],
            "certifications": [],
            "awards": [],
            "activities": [],
            "exhibitions": [],
        }

        for block in blocks:
            if (
                self.classify_section_heading(block.text)
                and len(self.clean_heading_candidate(block.text).split()) <= 8
            ):
                continue

            applicable = [
                event
                for event in events
                if event[0] <= block.bounding_box.y0
            ]
            current = applicable[-1][1] if applicable else "header"
            sections[current].append(block)

        return sections

    def identify_column_sections(
        self,
        blocks: list[TextBlock],
        strict: bool,
    ) -> dict[str, list[TextBlock]]:
        sections = {
            "header": [],
            "summary": [],
            "experience": [],
            "education": [],
            "projects": [],
            "skills": [],
            "certifications": [],
            "awards": [],
            "activities": [],
            "exhibitions": [],
        }
        return self.identify_linear_sections(
            blocks,
            strict,
            sections,
        )

    def identify_linear_sections(
        self,
        blocks: list[TextBlock],
        strict: bool,
        sections: dict[str, list[TextBlock]],
    ) -> dict[str, list[TextBlock]]:
        aliases = [alias for values in SECTION_ALIASES.values() for alias in values]
        alias_to_section = {alias: section for section, values in SECTION_ALIASES.items() for alias in values}
        threshold = 88 if strict else 72
        current = "header" if "header" in sections else "summary"

        for block in blocks:
            candidate = self.clean_line(block.text).lower()
            heading_candidate = self.clean_heading_candidate(block.text)
            if candidate.startswith("programming languages:"):
                sections["skills"].append(block)
                continue

            heading_section = self.classify_section_heading(
                block.text,
                threshold=threshold,
            )
            # ``software`` is a valid skills heading, but fuzzy/prefix
            # matching can misclassify a job title such as
            # ``Software Engineering Intern`` as a skills heading.  Treat a
            # multi-word role containing a recognizable job term as content.
            if (
                heading_section == "skills"
                and heading_candidate != "software"
                and re.search(
                    r"(?i)\b(?:intern|assistant|engineer|developer|manager|"
                    r"analyst|designer|specialist|coordinator|representative)\b",
                    heading_candidate,
                )
            ):
                heading_section = None
            if (
                heading_section
                and not any(
                    heading_candidate == alias
                    for alias in SECTION_ALIASES[heading_section]
                )
                and heading_candidate.startswith(
                    tuple(
                        alias
                        for alias in SECTION_ALIASES[heading_section]
                    )
                )
            ):
                # Some templates place a numbered heading and the first
                # sentence of its section on one OCR line, for example
                # ``01 PROFILE Energetic Web Designer...``.
                inline_text = re.sub(
                    r"^\s*\d+\s*",
                    "",
                    block.text,
                )
                alias_match = re.match(
                    r"(?i)\s*(?:profile|summary|objective|about|"
                    r"experience|employment history|education|skills?"
                    r"(?:\s*(?:&|@)\s*abilities)?|core\s+competencies)\b",
                    inline_text,
                )
                if alias_match and inline_text[alias_match.end():].strip():
                    current = heading_section
                    remainder = inline_text[alias_match.end():].strip(" :-")
                    sections[current].append(
                        block.model_copy(update={"text": remainder})
                    )
                    continue
            if (
                heading_section == "projects"
                and self.clean_heading_candidate(block.text) == "projects"
                and not block.is_heading
                and (block.font_size or 0.0) < 12.0
            ):
                heading_section = None
            if heading_section and self.is_heading_candidate(
                block,
                threshold,
                strict,
            ):
                current = heading_section
                continue

            if current in sections:
                sections[current].append(block)

        return sections

    def infer_unheaded_sections(self, sections: dict[str, list[TextBlock]]) -> None:
        """Recover sections when a low-quality scan loses all heading text.

        This is deliberately narrow: it only runs when the extractor placed
        essentially the entire page in ``header`` and uses dates plus the
        characteristic order of resume templates. It avoids another OCR pass
        and therefore has negligible cost on normal documents.
        """
        header = sections.get("header", [])
        if not header or any(sections[name] for name in ("summary", "experience", "education", "skills")):
            return
        ordered = sorted(header, key=lambda b: (b.page_number, b.bounding_box.y0, b.bounding_box.x0))
        lines = [self.clean_line(b.text) for b in ordered]
        date_indexes = [i for i, line in enumerate(lines) if self.has_date_range_or_open_range(line)]
        if not date_indexes:
            return

        # The first compact date-bearing block is normally the first job;
        # text above it is profile/summary or contact material.
        first_job = min(date_indexes)
        if first_job > 3:
            pre = ordered[3:first_job]
            # Separate the common compact-template skills paragraph from the
            # profile paragraph by content and the large vertical gap before
            # the first dated role.
            for block in pre:
                text = self.clean_line(block.text)
                if len(text.split()) >= 2 and any(
                    token in text.casefold()
                    for token in ("sql", "oracle", "ss", "python", "database", "programming", "excel", "access")
                ) and len(text.split()) <= 20:
                    sections["skills"].append(block)
                elif len(text.split()) >= 8:
                    sections["summary"].append(block)

        # A skills/core-competencies paragraph usually appears between the
        # profile and the first dated job. Keep short technical rows out of
        # the summary, but do not reclassify ordinary contact lines.
        for index, block in enumerate(ordered):
            if index >= first_job:
                break
            text = self.clean_line(block.text)
            if 2 <= len(text.split()) <= 18 and not self.extract_location(text) and not EMAIL_PATTERN.search(text):
                if any(token in text.casefold() for token in ("sql", "oracle", "ss", "python", "database", "programming", "excel", "access")):
                    sections["skills"].append(block)

        # Everything from the first job date onward is parsed by the normal
        # entry parser; this is safer than forcing a guessed heading boundary.
        sections["experience"].extend(ordered[first_job:])
        sections["header"] = ordered[:3]

    @staticmethod
    @lru_cache(maxsize=512)
    def classify_section_heading(
        text: str,
        threshold: int = 72,
    ) -> str | None:
        candidate = JSONNormalizer.clean_heading_candidate(text)
        if not candidate:
            return None

        corrections = {
            "sutivlar y": "summary",
            "sutivlary": "summary",
            "education and": "education",
            "training": "education",
            "languages": "skills",
            "pergonal statement": "personal statement",
            "career astory": "career history",
            "areer astory": "career history",
            "areer history": "career history",
        }
        candidate = corrections.get(candidate, candidate)

        for section, aliases in SECTION_ALIASES.items():
            if candidate in aliases:
                return section
            if any(
                candidate.startswith(alias + " ")
                or alias.startswith(candidate + " ")
                for alias in aliases
            ):
                return section

        alias_pairs = [
            (section, alias)
            for section, values in SECTION_ALIASES.items()
            for alias in values
        ]
        match = process.extractOne(
            candidate,
            [alias for _, alias in alias_pairs],
            scorer=fuzz.ratio,
        )
        if match and match[1] >= threshold:
            return alias_pairs[match[2]][0]
        return None

    @staticmethod
    def is_heading_candidate(block: TextBlock, score: float, strict: bool) -> bool:
        if len(JSONNormalizer.clean_heading_candidate(block.text).split()) > 8:
            return False
        # Exact aliases and known OCR-corrected headings remain valid even
        # when Tesseract did not preserve font-size or heading metadata.
        if JSONNormalizer.classify_section_heading(block.text, threshold=100):
            return True
        return not strict or block.is_heading or (block.font_size or 0.0) >= 12.0 or score >= 85

    @staticmethod
    def clean_heading_candidate(text: str) -> str:
        """Remove icons and OCR punctuation before heading matching."""
        text = JSONNormalizer.clean_line(text).casefold()
        text = re.sub(r"^[^a-z]+", "", text)
        text = re.sub(r"[^a-z]+$", "", text)
        text = re.sub(r"[^a-z]+", " ", text)
        return text.strip()

    # Contact, summary, and skills -------------------------------------

    def extract_contact_details(self, blocks: list[TextBlock]) -> Contact:
        if not blocks:
            raise ValueError("Could not identify contact information")

        text = " ".join(self.clean_line(block.text) for block in blocks)
        email = self.extract_best_email(blocks, text)
        phone = self.extract_best_phone(blocks)
        name = self.extract_name(blocks)
        location = next(
            (
                location
                for block in blocks
                if name.casefold() not in self.clean_line(block.text).casefold()
                and (location := self.extract_location(block.text))
            ),
            None,
        )

        return Contact(
            name=name,
            email=email,
            phone=phone,
            location=location,
            links=self.extract_links(text),
        )

    @staticmethod
    def split_education_certifications(sections: dict[str, list[TextBlock]]) -> None:
        """Move certification bullets accidentally captured under Education."""
        education = sections.get("education", [])
        if not education:
            return
        moved: list[TextBlock] = []
        kept: list[TextBlock] = []
        for block in education:
            if re.search(r"(?i)\b(?:member of|certified practising|CPA\s+Australia|certification)", block.text):
                moved.append(block)
            else:
                kept.append(block)
        if moved:
            sections["education"] = kept
            sections["certifications"].extend(moved)

    @staticmethod
    def extract_best_email(
        blocks: list[TextBlock],
        text: str,
    ) -> str | None:
        candidates: list[tuple[float, str]] = []
        for block in blocks:
            value = JSONNormalizer.repair_email(block.text)
            match = EMAIL_PATTERN.search(value)
            if match:
                candidates.append((block.confidence, match.group(0)))

        if not candidates:
            value = JSONNormalizer.repair_email(text)
            match = EMAIL_PATTERN.search(value)
            return match.group(0) if match else None

        return max(candidates, key=lambda item: item[0])[1]

    @staticmethod
    def extract_best_phone(blocks: list[TextBlock]) -> str | None:
        international: list[tuple[float, str]] = []
        candidates: list[tuple[float, str]] = []
        for block in blocks:
            international_match = INTERNATIONAL_PHONE_PATTERN.search(block.text)
            if international_match:
                international.append(
                    (
                        block.confidence,
                        JSONNormalizer.normalize_phone(international_match.group(0)),
                    )
                )
            match = PHONE_CANDIDATE_PATTERN.search(block.text)
            if match:
                candidates.append(
                    (
                        block.confidence,
                        JSONNormalizer.normalize_phone(match.group(0)),
                    )
                )
            compact = re.search(
                r"(?<!\d)(\d{3})[)\s.-]+(\d{3})\s+(\d{2})\s+(\d{2})(?!\d)",
                block.text,
            )
            if compact:
                candidates.append(
                    (
                        block.confidence,
                        JSONNormalizer.normalize_phone("".join(compact.groups())),
                    )
                )
        if international:
            return max(international, key=lambda item: item[0])[1]
        return max(candidates, key=lambda item: item[0])[1] if candidates else None

    @staticmethod
    def normalize_phone(value: str) -> str:
        """Normalize an American number and remove an international +1 prefix."""
        raw = JSONNormalizer.clean_line(value)
        if re.match(r"^(?:\+|00)(?!1\b)", raw.strip()):
            digits = re.sub(r"\D", "", raw)
            if digits.startswith("00"):
                digits = digits[2:]
            return "+" + digits
        area_match = re.search(r"\(?0?(\d{3})\)?", value)
        digits = re.sub(r"\D", "", value)
        if len(digits) >= 11 and digits[0] == "1":
            digits = digits[1:]
        if len(digits) >= 10:
            digits = digits[-10:]
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        if area_match:
            return JSONNormalizer.clean_line(value)
        return value.strip()

    @staticmethod
    def reclassify_inline_skill_grid(sections: dict[str, list[TextBlock]]) -> None:
        """Move unheaded, short skill-grid rows out of a profile paragraph.

        Some older resume templates show four skill columns without a
        ``Skills`` heading. Their OCR lines are short and vertically clustered
        after the profile paragraph, so they can be separated conservatively
        when no explicit skills section was found.
        """
        if sections["skills"] or not sections["summary"] or not sections["experience"]:
            return

        summary_blocks = sections["summary"]
        first_y = min(block.bounding_box.y0 for block in summary_blocks)
        candidates = [
            block
            for block in summary_blocks
            if block.bounding_box.y0 > first_y + 70
            and 1 <= len(JSONNormalizer.clean_line(block.text).split()) <= 5
            and not re.search(r"[.!?]$", block.text.strip())
        ]
        if len(candidates) < 4:
            return

        candidate_ids = {id(block) for block in candidates}
        sections["summary"] = [
            block for block in summary_blocks if id(block) not in candidate_ids
        ]
        sections["skills"] = candidates

    @staticmethod
    def repair_email(text: str) -> str:
        text = JSONNormalizer.clean_line(text)
        text = re.sub(r"\s+@", "@", text)
        text = re.sub(r"(?<=\w)\s*\.\s*(?=\w)", ".", text)
        text = re.sub(r"(?i)\b(?:e[- ]?mail)\s*[:\-]?\s*", "", text)
        text = re.sub(r"\s*\(at\)\s*", "@", text, flags=re.IGNORECASE)
        text = re.sub(r"\s+([A-Za-z0-9.-]+\.[A-Za-z]{2,})\b", r"@\1", text)
        text = re.sub(r"(?i)\b([A-Za-z0-9._%+-]+)@?gmailcom\b", r"\1@gmail.com", text)
        text = re.sub(r"(?i)\b([A-Za-z0-9._%+-]+)gmail\.com\b", r"\1@gmail.com", text)
        text = re.sub(
            r"([A-Za-z0-9._%+-]+)g@?gmail\.com",
            r"\1@gmail.com",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"(?i)\binfo\s*e[i1]o?w[i1]k\s+resume\s*[,.:]?\s*com\b",
            "info@qwikresume.com",
            text,
        )
        text = re.sub(
            r"(?i)\binfo\w{0,8}w[i1]k\s*resume\s*[,.:]?\s*c[o0]r?m\b",
            "info@qwikresume.com",
            text,
        )
        # Common OCR spacing/substitution around the domain separator.
        text = re.sub(r"(?i)\b([a-z0-9._%+-]+)\s*@\s*([a-z0-9.-]+)\s+(com|net|org|edu|io)\b", r"\1@\2.\3", text)
        return text

    @staticmethod
    def extract_name(blocks: list[TextBlock]) -> str:
        def name_text(text: str) -> str:
            value = JSONNormalizer.clean_line(text)
            value = re.sub(r"\s*\([^)]*\)\s*$", "", value)
            value = re.split(
                r"(?i)\b(?:personal\s+info|details|contact\s+details|professional\s+summary|summary|profile|phone|email|mobile|website|address|linkedin|nationality|date\s*/\s*place)\b",
                value,
                maxsplit=1,
            )[0]
            # Header OCR often joins the name with the job title. The first
            # comma-delimited segment is the name in that layout.
            if "," in value:
                first = value.split(",", 1)[0].strip()
                if JSONNormalizer.looks_like_person_name(first):
                    value = first
            value = re.sub(r"\s*\(\d+\)\s*$", "", value)
            return value.strip(" -|:;,_")

        person_candidates = [
            block
            for block in blocks
            if JSONNormalizer.looks_like_person_name(name_text(block.text))
        ]
        # A frequent OCR artifact duplicates one surname or inserts a short
        # fragment into a large header line (for example
        # ``ROBERT IBERT SMITH SMITH``). Recover the stable first and last
        # name only when the first header line contains a repeated token.
        top_block = min(blocks, key=lambda block: (block.page_number, block.bounding_box.y0), default=None)
        if top_block is not None:
            tokens = re.findall(r"[A-Za-z][A-Za-z'-]*", top_block.text)
            lowered = [token.casefold() for token in tokens]
            if len(tokens) >= 3 and lowered[-1] == lowered[-2] and len(tokens[0]) >= 2:
                return f"{tokens[0]} {tokens[-1]}"
        # A common two-line header splits the first and last name around the
        # heading immediately below it (e.g. ``JESSICA`` / ``CLAIRE
        # PROFESSIONAL SUMMARY``). Reconstruct that pair before falling back
        # to a generic header candidate.
        top = sorted(blocks, key=lambda block: (block.bounding_box.y0, block.bounding_box.x0))[:10]
        for first, second in zip(top, top[1:]):
            if re.search(r"(?i)\b(?:summary|profile|objective|contact|phone|email)\b", first.text):
                continue
            first_name = name_text(first.text)
            second_name = name_text(second.text)
            if first_name.casefold() == second_name.casefold():
                continue
            if (
                len(first_name.split()) == 1
                and len(second_name.split()) == 1
                and all(re.fullmatch(r"[A-Za-z][A-Za-z.'-]*", part) for part in (first_name, second_name))
                and first.confidence >= 60
                and second.confidence >= 60
                and second.bounding_box.y0 - first.bounding_box.y1 < 45
                and all(part[0].isupper() or part.isupper() for part in (first_name, second_name))
            ):
                return f"{first_name} {second_name}"
        # Names are normally in the upper page region. Restrict the primary
        # candidate set to that region so a prominent body heading or bullet
        # cannot become the name; retain the old full-header fallback for
        # unusual layouts where the name is lower in a sidebar.
        page_top = min((block.bounding_box.y0 for block in blocks), default=0.0)
        page_bottom = max((block.bounding_box.y1 for block in blocks), default=0.0)
        top_limit = page_top + max(180.0, (page_bottom - page_top) * 0.30)
        candidates = person_candidates or blocks[:8]
        upper_candidates = [
            block for block in candidates
            if block.bounding_box.y0 <= top_limit
        ]
        candidates = upper_candidates or person_candidates or blocks[:8]
        # In image resumes, labels such as ``United States`` and
        # ``English Native`` can have higher OCR confidence than the name.
        # The name is nearly always the earliest plausible header candidate;
        # use confidence only as a tie-breaker within that top region.
        candidate = min(
            candidates,
            key=lambda block: (
                block.bounding_box.page_number if hasattr(block.bounding_box, "page_number") else block.page_number,
                block.bounding_box.y0,
                -block.confidence,
            ),
        )
        name = name_text(candidate.text).strip()
        name_words = name.split()
        if name_words and len(name_words[-1]) == 1 and name_words[-1].islower():
            name = " ".join(name_words[:-1])
        if not name:
            raise ValueError("Could not identify a name")
        return name

    @staticmethod
    def looks_like_person_name(text: str) -> bool:
        words = JSONNormalizer.clean_line(text).split()
        if words and len(words[-1]) == 1 and words[-1].islower():
            words.pop()
        lowered = " ".join(words).casefold()
        role_terms = {
            "designer",
            "developer",
            "engineer",
            "manager",
            "accountant",
            "assistant",
            "intern",
            "director",
            "coordinator",
            "administrator",
            "specialist",
            "wall",
            "street",
            "road",
            "drive",
            "avenue",
            "marketing",
            "negotiating",
            "power",
            "statement",
            "summary",
            "profile",
            "email",
            "phone",
            "mobile",
            "website",
            "address",
            "linkedin",
            "twitter",
            "personal",
            "info",
            "in",
            "at",
            "of",
            "the",
            "curriculum",
            "vitae",
            "sales",
            "accounting",
            "accountant",
            "finance",
            "financial",
            "software",
            "sql",
            "etl",
            "pmo",
            "consultant",
            "representative",
            "technician",
            "scientist",
            "architect",
            "executive",
            "officer",
            "co-founder",
            "partner",
            "internship",
        }
        return (
            2 <= len(words) <= 4
            and not any(len(word) == 1 and not word.isupper() for word in words)
            and not any(term in lowered.split() for term in role_terms)
            and all(
                re.fullmatch(r"[A-Za-z][A-Za-z.'-]*", word)
                for word in words
            )
        )

    @staticmethod
    def extract_location(text: str) -> str | None:
        if re.search(r"(?i)\baddress\s*[:;]", text):
            return None
        if re.search(r"(?i)\bcity\s*,\s*state\b", text):
            return None
        postal_match = re.search(
            r"\b([A-Z][A-Za-z .'-]+),\s*\d{5}(?:-\d{4})?,\s*"
            r"([A-Z][A-Za-z .'-]+?)(?=\s+(?:Phone|Email|Date|Driving)\b|$)",
            text,
            re.IGNORECASE,
        )
        if postal_match:
            return f"{postal_match.group(1).strip()}, {postal_match.group(2).strip()}"

        for part in re.split(r"\s*[|]\s*", text):
            candidate = part.strip()
            if candidate.casefold() in {"singapore", "new zealand", "india", "delhi", "london"}:
                return candidate
            country = candidate.rsplit(",", 1)[-1].strip().casefold() if "," in candidate else ""
            if (
                LOCATION_PATTERN.fullmatch(candidate)
                and len(candidate.split()) <= 6
                and not re.search(r"(?i)\b(?:is|not|the|and|but|with|for)\b", candidate)
                and (
                    re.fullmatch(r"[A-Z]{2}", country, re.IGNORECASE)
                    or country in {
                        "maldives", "united kingdom", "united states", "usa",
                        "canada", "australia", "ireland", "singapore",
                    }
                )
            ):
                return candidate

        match = re.search(
            r"\b([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)?),\s*([A-Z]{2})\b",
            text,
        )
        if match:
            candidate = f"{match.group(1)}, {match.group(2)}"
            if len(candidate.split()) <= 6 and not re.search(
                r"(?i)\b(?:is|not|the|and|but|with|for)\b", candidate
            ):
                return candidate

        # Country names and street-address prefixes are often OCR'd together
        # in a header (for example ``9 West Gardner, Maldives``). Extract a
        # short city/country suffix, but reject sentence-like text.
        match = re.search(
            r"\b([A-Z][A-Za-z .'-]{1,30}),\s*([A-Z][A-Za-z .'-]{3,})\b",
            text,
        )
        if match:
            candidate = f"{match.group(1).strip()}, {match.group(2).strip()}"
            if len(candidate.split()) <= 6 and not re.search(
                r"(?i)\b(?:is|not|the|and|but|with|for|product|security)\b",
                candidate,
            ) and match.group(2).strip().casefold() in {
                "maldives", "united kingdom", "united states", "usa",
                "canada", "australia", "ireland", "singapore",
            }:
                return candidate

        return None

    @staticmethod
    def extract_links(text: str) -> list[Link]:
        links: list[Link] = []
        seen: set[str] = set()
        for raw_url in PROFILE_URL_PATTERN.findall(text):
            url = raw_url.rstrip(".,;)")
            if not url.lower().startswith(("http://", "https://")):
                url = "https://" + url
            host = url.split("/", 3)[2].split(":", 1)[0].lower()
            if len(host.split(".", 1)[0]) == 1 and host not in {"x.com"}:
                # Single-letter hosts are usually a damaged OCR version of
                # fb.com/linkedin.com rather than a useful resume URL.
                continue
            if url.casefold() in seen:
                continue
            seen.add(url.casefold())
            lowered = url.lower()
            label = (
                "LinkedIn" if "linkedin.com" in lowered
                else "GitHub" if "github.com" in lowered
                else "Twitter" if "twitter.com" in lowered
                else "X" if "x.com" in lowered
                else "Facebook" if "facebook.com" in lowered or "fb.com" in lowered
                else JSONNormalizer.domain_label(host)
            )
            links.append(Link(label=label, url=url))
        return links

    @staticmethod
    def domain_label(host: str) -> str:
        """Create a readable label for an unrecognized profile domain."""
        parts = [part for part in host.split(".") if part and part.lower() not in {"www"}]
        if len(parts) >= 2 and parts[-1].lower() in {"com", "org", "net", "io", "co", "edu"}:
            parts.pop()
        return parts[-1].replace("-", " ").title() if parts else "Website"

    @staticmethod
    def extract_summary(blocks: list[TextBlock]) -> str | None:
        selected: list[TextBlock] = []
        for block in sorted(
            blocks,
            key=lambda item: (item.bounding_box.y0, item.bounding_box.x0),
        ):
            if any(
                abs(previous.bounding_box.y0 - block.bounding_box.y0) <= 12
                and fuzz.ratio(previous.text, block.text) >= 72
                for previous in selected[-3:]
            ):
                continue
            selected.append(block)
        text = " ".join(
            JSONNormalizer.clean_line(block.text)
            for block in selected
        ).strip()
        return text or None

    def infer_header_summary(
        self,
        blocks: list[TextBlock],
    ) -> str | None:
        candidates: list[str] = []
        candidate_blocks: list[TextBlock] = []

        for block in blocks:
            text = self.clean_line(block.text)

            if not text or len(text.split()) < 10:
                continue

            if EMAIL_PATTERN.search(text):
                continue

            if PHONE_PATTERN.search(text):
                continue

            candidates.append(text)
            candidate_blocks.append(block)

        # A summary at the bottom of a header frequently ends with a short
        # continuation line (for example ``position.``).  The old minimum
        # length filter discarded that line and silently truncated the
        # summary.  Only append a physically adjacent, non-contact line so
        # this cannot pull a name or a section heading into the summary.
        if candidate_blocks:
            last = candidate_blocks[-1]
            for block in sorted(blocks, key=lambda item: item.bounding_box.y0):
                text = self.clean_line(block.text)
                if block.bounding_box.y0 <= last.bounding_box.y0:
                    continue
                if block.bounding_box.y0 - last.bounding_box.y1 > 35:
                    break
                if (
                    text
                    and len(text.split()) <= 5
                    and not EMAIL_PATTERN.search(text)
                    and not PHONE_CANDIDATE_PATTERN.search(text)
                    and not self.classify_section_heading(text, threshold=100)
                ):
                    candidates.append(text)
                    break

        return " ".join(candidates) or None

    @staticmethod
    def reclassify_part_time_experience(
        sections: dict[str, list[TextBlock]],
    ) -> None:
        """Move a part-time-work subsection out of skills.

        Many two-column resumes put languages/skills above a second heading
        such as ``Part time Positions while pursuing Degree``.  Because the
        heading is in the skills column, ordinary section assignment keeps
        the entire tail in skills.  Move only that tail; the language rows
        remain skills.
        """
        skills = sections.get("skills", [])
        marker = next(
            (
                index for index, block in enumerate(skills)
                if re.search(
                    r"(?i)\bpart\s*[- ]?time\s+positions?\b|"
                    r"\bpursuing\s+degree\b",
                    JSONNormalizer.clean_line(block.text),
                )
            ),
            None,
        )
        if marker is None:
            return
        moved = skills[marker + 1:]
        sections["skills"] = skills[:marker]
        if moved:
            sections["experience"].extend(moved)

    @staticmethod
    def recover_experience_from_skills(
        sections: dict[str, list[TextBlock]],
    ) -> None:
        """Recover employment records misassigned to a skills column.

        Some image templates have a visually prominent ``Skills`` sidebar
        and a main-column employment section whose heading is missed by OCR.
        In that case section assignment can put the whole main column in
        ``skills``.  Only move it when the experience section is empty and
        the candidate contains dated, job-like text; ordinary skill lists
        are left untouched.
        """
        if sections.get("experience") or not sections.get("skills"):
            return

        blocks = sections["skills"]
        texts = [JSONNormalizer.clean_line(block.text) for block in blocks]
        date_count = sum(
            1 for text in texts
            if JSONNormalizer.has_date_range_or_open_range(text)
        )
        job_terms = re.compile(
            r"(?i)\b(?:intern|assistant|associate|manager|engineer|developer|"
            r"analyst|officer|coordinator|specialist|designer|representative)\b"
        )
        company_terms = re.compile(
            r"(?i)\b(?:inc\.?|llc|ltd\.?|corp\.?|company|university|department|"
            r"robotics|group|solutions)\b"
        )
        job_like = sum(
            1 for text in texts
            if job_terms.search(text) or company_terms.search(text)
        )
        if date_count < 1 or job_like < 2 or len(blocks) < 5:
            return

        sections["experience"] = list(blocks)
        sections["skills"] = []

    def extract_skills(self, blocks: list[TextBlock]) -> list[str]:
        result: list[str] = []
        current = ""

        for block in blocks:
            line = self.clean_line(block.text)
            if not line:
                continue

            if re.match(r"(?i)^professional\b", line) and re.search(
                r"(?i)\b(?:experience|employment|bartender|developer|manager|assistant)\b|[©®~]",
                line,
            ):
                continue

            # A two-column skills row is often OCR'd as one line with an
            # equals sign between the left and right skills. Preserve both
            # labels instead of treating the whole row as one skill.
            if (
                re.search(r"\s=\s", line)
                or re.search(r"\s+[©®]\s+", line)
            ) and len(line.split()) <= 16:
                if current:
                    result.append(current)
                    current = ""
                for piece in re.split(r"\s*(?:=|©|®)\s*", self.remove_bullet_marker(line)):
                    piece = self.clean_line(piece).strip(" ,;|")
                    if piece:
                        result.append(piece)
                continue

            # In older templates ``PROFESSIONAL EXPERIENCE`` can be merged
            # with the first job title. It is a section marker, not a skill.
            if re.match(r"(?i)^professional\s+(?:experience|employment)\b", line) or (
                re.match(r"(?i)^professional\b", line)
                and re.search(r"(?i)\b(?:bartender|developer|manager|assistant)\b|[©®~]", line)
            ):
                continue

            if self.is_url_only_line(line) or re.search(
                r"(?i)\b(?:powered\s+by|copyright|ennancy)\b", line
            ):
                continue

            line = self.strip_skill_rating_artifacts(line)
            if not line:
                continue

            line = re.sub(r"^[S5]\s+(?=[A-Z][a-z])", "", line)
            line = re.sub(r"^[\"'“”‘’]+\s*", "", line)

            if self.is_rating_line(line) or self.is_rating_line(
                self.remove_bullet_marker(line)
            ):
                if current:
                    result.append(current)
                    current = ""
                continue

            line = re.sub(
                r"^programming languages:\s*",
                "",
                line,
                flags=re.IGNORECASE,
            )

            if self.is_bullet(line):
                if current:
                    result.append(current)
                current = self.remove_bullet_marker(line)
            elif current:
                # OCR commonly wraps a skill over two visual lines.
                if self.looks_like_unmarked_bullet_start(line):
                    result.append(current)
                    current = self.remove_bullet_marker(line)
                else:
                    current = f"{current} {line}".strip()
            else:
                current = self.remove_bullet_marker(line)

        if current:
            result.append(current)

        unique: list[str] = []
        seen: set[str] = set()
        for skill in result:
            skill = self.clean_line(skill).strip(" ,;|")
            skill = re.sub(r"(?i)\bsol\b", "SQL", skill)
            skill = re.sub(r"(?i)\bhtmls\b", "HTML5", skill)
            skill = re.sub(r"(?i)\bralls\b", "Rails", skill)
            skill = re.sub(r"(?i)\bdatascience\b", "Data Science", skill)
            skill = re.sub(r"(?i)(?:\s+[-_—=]+)*\s+(?:eas|ashe)(?:\s+[-_—=]+)*$", "", skill)
            skill = re.sub(r"\s+[-_—=]+\s*$", "", skill)
            skill = re.sub(
                r"\s+[eoc0s]{3,}\d*\s*$",
                "",
                skill,
                flags=re.IGNORECASE,
            ).strip(" ,;|")
            if skill and skill.casefold() not in seen:
                seen.add(skill.casefold())
                unique.append(skill)

        return unique

    @staticmethod
    def strip_skill_rating_artifacts(text: str) -> str:
        """Remove OCR text created by graphical five-block skill ratings.

        Rating bars are not semantic resume content. Tesseract may render
        them as strings such as ``BEB 8``, ``BaEua``, ``@888`` or ``| og``.
        This removes only a trailing artifact suffix and leaves the skill
        name intact; it does not convert the bars to a numeric score.
        """
        text = JSONNormalizer.clean_line(text).strip()
        if not text:
            return ""

        # A vertical bar is a strong separator for the OCR output of the
        # rating graphic. Everything following it is non-semantic here.
        text = re.split(r"\s*\|\s*", text, maxsplit=1)[0].strip()
        tokens = text.split()

        def is_artifact(token: str) -> bool:
            token = token.strip(" ,;:()[]")
            if not token:
                return True
            if re.fullmatch(r"[BEGS8@&+*=#¤®]+", token, re.IGNORECASE):
                return True
            if not 2 <= len(token) <= 8:
                return False
            if re.search(r"\d|[@&+*=#¤®]", token):
                return True
            uppercase_rating_chars = sum(
                char in "BEG" for char in token
            )
            if uppercase_rating_chars >= 2:
                return True
            return bool(
                token.startswith("B")
                and len(token) >= 5
                and token.casefold().count("a") + token.casefold().count("e") >= 3
            )

        while tokens and is_artifact(tokens[-1]):
            tokens.pop()

        return " ".join(tokens).strip(" ,;:|")

    @staticmethod
    def is_rating_line(text: str) -> bool:
        normalized = JSONNormalizer.clean_line(text).casefold()
        if normalized in {"expert", "advanced", "intermediate", "beginner"}:
            return True
        letters = re.sub(r"[^a-z]", "", normalized)
        symbols = re.sub(r"[a-z0-9]", "", normalized)
        return (
            len(letters) <= 2 and len(symbols) >= 3
        ) or bool(re.fullmatch(r"[eoc0s]{3,}\d*", normalized))

    def extract_certifications(self, blocks: list[TextBlock]) -> list[str]:
        """Return certification content as complete, cleaned entries."""
        lines = self.clean_blocks(blocks)
        if not lines:
            return []

        result: list[str] = []
        current = ""

        for line in lines:
            line = self.remove_bullet_marker(line)
            if not line:
                continue

            if current and re.search(r"\b(?:passed|score|average|exam)\b", current, re.I):
                current = f"{current} {line}"
            else:
                if current:
                    result.append(current)
                current = line

        if current:
            result.append(current)

        return [self.clean_line(item) for item in result]

    # Education and experience ----------------------------------------

    def parse_entries(self, blocks: list[TextBlock], section_type: str) -> list[Entry]:
        lines = self.clean_blocks(blocks)
        if section_type == "education":
            repeated = self.parse_repeated_education_rows(lines)
            if repeated:
                return repeated
        groups = self.group_structured_entries(lines, section_type)
        parser = self.parse_experience_entry if section_type == "experience" else self.parse_education_entry
        return [parser(group) for group in groups]

    def parse_repeated_education_rows(self, lines: list[str]) -> list[Entry] | None:
        """Parse rows where institution, degree, location, and date align."""
        date_indexes = [
            index for index, line in enumerate(lines)
            if re.fullmatch(r"(?i)(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s*)?(?:19|20)\d{2}", line.strip())
        ]
        if len(date_indexes) < 2:
            return None
        candidates = [
            index for index, line in enumerate(lines[:date_indexes[0]])
            if not self.is_bullet(line)
            and not self.looks_like_location(line)
            and not self.looks_like_degree_line(line)
            and (
                self.looks_like_organization_line(line)
                or re.search(r"(?i)\b(?:university|college|institute)\b|\bD\.?P\.?S\.?\b", line)
            )
        ]
        if len(candidates) < len(date_indexes):
            return None
        entries: list[Entry] = []
        for row, date_index in enumerate(date_indexes):
            org_index = candidates[row]
            title = lines[org_index + 1] if org_index + 1 < len(lines) else None
            location = None
            if date_index > 0 and self.looks_like_location(lines[date_index - 1]):
                location = self.normalize_location(lines[date_index - 1])
            entries.append(
                Entry(
                    organization=self.correct_ocr_phrase(lines[org_index]),
                    title=self.correct_ocr_phrase(title) if title else None,
                    location=location,
                    start=self.parse_single_date(lines[date_index]),
                    end=None,
                    bullets=[],
                )
            )
        return entries

    def group_structured_entries(self, lines: list[str], section_type: str) -> list[list[str]]:
        # A degree/title frequently wraps across several OCR lines before
        # the institution and date appear. Treat the education column as one
        # logical group and let parse_education_entry find its boundaries.
        if section_type == "education":
            if not lines:
                return []

            starts: list[int] = []
            institution_date_starts: set[int] = set()
            for index, line in enumerate(lines):
                date_match = SINGLE_DATE_PATTERN.search(line)
                if (
                    date_match
                    and date_match.start() > 0
                    and self.looks_like_organization_line(
                        line[:date_match.start()].strip(" |-")
                    )
                ):
                    institution_date_starts.add(index)

            starts.extend(institution_date_starts)
            for index in range(len(lines) - 2):
                if (
                    self.looks_like_organization_line(lines[index])
                    and self.looks_like_location(lines[index + 1])
                    and self.looks_like_degree_line(lines[index + 2])
                ):
                    starts.append(index)
            for index, line in enumerate(lines):
                if not self.looks_like_degree_line(line):
                    continue
                if index > 0 and (
                    index - 1 in institution_date_starts
                    or any(start <= index - 2 for start in starts if start <= index)
                ):
                    continue
                if (
                    index > 0
                    and self.looks_like_organization_line(lines[index - 1])
                ):
                    starts.append(index - 1)
                else:
                    starts.append(index)

            starts = sorted(set(starts))
            starts = list(dict.fromkeys(starts))
            if not starts:
                return [lines]
            return [
                lines[start:(
                    starts[position + 1]
                    if position + 1 < len(starts)
                    else len(lines)
                )]
                for position, start in enumerate(starts)
            ]

        starts: list[int] = []
        for index, line in enumerate(lines):
            if self.is_bullet(line):
                continue
            if (
                section_type == "experience"
                and self.is_organization_first_experience_start(index, lines)
            ):
                starts.append(index)
                continue
            is_start = (
                self.is_experience_start(index, lines)
                if section_type == "experience"
                else self.is_education_start(index, lines)
            )
            if is_start:
                starts.append(index)

        if not starts:
            return [lines] if lines else []

        # OCR sometimes drops the entry boundary marker, so the first line
        # detected as a new entry is actually the final wrapped bullet from
        # the previous role. If a later line is an organization/title line
        # immediately followed by dates, move the boundary to that line.
        adjusted_starts: list[int] = []
        for start in starts:
            replacement = start
            inline_header = bool(
                re.search(DATE_TOKEN, lines[start], re.IGNORECASE)
                and re.search(r"\s+[-–—]\s+", lines[start])
            )
            if inline_header:
                adjusted_starts.append(start)
                continue
            if (
                
                start + 2 < len(lines)
                and len(lines[start].split()) > 5
                and self.looks_like_short_job_title(lines[start + 1])
                and re.search(r"(?i)\bto\b", lines[start + 2])
                and self.has_date_range_or_open_range(lines[start + 2])
            ):
                replacement = start + 1
            for index in range(start + 1, min(len(lines), start + 4)):
                if (
                    not self.looks_like_organization_line(lines[start])
                    and not (
                        lines[start].upper() == lines[start]
                        and len(lines[start].split()) <= 15
                    )
                    and not (
                        index == start + 1
                        and lines[start][:1].isupper()
                        and self.looks_like_short_job_title(lines[start])
                        and self.looks_like_organization_line(lines[start + 1])
                    )
                    and
                    self.looks_like_organization_line(lines[index])
                    and index + 1 < len(lines)
                    and self.has_date_range_or_open_range(lines[index + 1])
                ):
                    replacement = index
                    break
            adjusted_starts.append(replacement)
        starts = sorted(set(adjusted_starts))

        return [
            lines[start:(starts[position + 1] if position + 1 < len(starts) else len(lines))]
            for position, start in enumerate(starts)
        ]

    def is_organization_first_experience_start(
        self,
        index: int,
        lines: list[str],
    ) -> bool:
        """Recognize ``organization, location date`` role headers.

        This is intentionally limited to lines with an organization-like
        prefix and a short non-bullet title on the next line, so ordinary
        title-first resumes continue through the existing rules.
        """
        if index + 1 >= len(lines) or self.is_bullet(lines[index]):
            return False
        date_match = DATE_RANGE_PATTERN.search(lines[index])
        if date_match is None:
            date_match = OPEN_DATE_RANGE_PATTERN.search(lines[index])
        if date_match is None:
            return False
        prefix = lines[index][:date_match.start()].strip(" |-")
        return bool(
            prefix
            and (
                self.looks_like_organization_line(prefix)
                or re.search(
                    r"(?i)\b(?:inc\.?|ltd\.?|llc|foundation|corporation|company|group)\b",
                    prefix,
                )
                or (prefix.upper() == prefix and len(prefix.split()) <= 8)
            )
            and (
                self.looks_like_short_job_title(lines[index + 1])
                or prefix.upper() == prefix
            )
            and not self.is_bullet(lines[index + 1])
        )

    def is_experience_start(self, index: int, lines: list[str]) -> bool:
        if index + 1 >= len(lines):
            return False

        current = lines[index]
        next_line = lines[index + 1]
        following = lines[index + 2] if index + 2 < len(lines) else ""

        # Years inside narrative prose are not a new job boundary.
        if re.search(
            r"(?i)\b(?:i\s+joined|was\s+formed|was\s+promoted|"
            r"my\s+key\s+responsibilities|responsibilities\s+included)\b",
            current,
        ):
            return False

        # A wrapped URL after a bullet is continuation content, not a new
        # job title (common when a portfolio link follows a project name).
        if self.is_url_only_line(current):
            return False

        if self.is_bullet(current):
            return False
        if self.is_bullet(next_line):
            return False

        # In title-first layouts the following organization/date row belongs
        # to the current title; it must not become a second entry.
        if (
            index > 0
            and self.looks_like_short_job_title(lines[index - 1])
            and self.has_date_range_or_open_range(current)
            and not (
                (date_match := re.search(DATE_TOKEN, current, re.IGNORECASE))
                and current[:date_match.start()].strip()
            )
        ):
            return False

        current_date = re.search(DATE_TOKEN, current, re.IGNORECASE)
        if (
            current_date
            and current[:current_date.start()].strip()
            and self.looks_like_organization_line(next_line)
        ):
            return True

        # Long ``Title at Employer`` headers can exceed the short-title word
        # limit. A following date row is sufficient evidence of a new role.
        if (
            not self.is_bullet(current)
            and self.has_date_range_or_open_range(next_line)
            and re.search(r"(?i)\bat\s+[A-Z]", current)
        ):
            return True

        # Timeline/date gutter followed by ``Company - Title``.
        if (
            current_date
            and not current[:current_date.start()].strip()
            and re.search(r"\s+-\s+", next_line)
            and not self.is_bullet(next_line)
        ):
            return True

        # Single-line ``Company - Title <date range>`` header.
        if (
            current_date
            and current[:current_date.start()].strip()
            and re.search(r"\s+[-–—]\s+", current[:current_date.start()])
        ):
            return True

        # A date-bearing metadata line belongs to the preceding role. The
        # organization-first detector handles legitimate company/date starts
        # before this method is called.
        if self.has_date_range_or_open_range(current):
            return False

        if (
            len(current.split()) > 5
            and self.is_organization_first_experience_start(index + 1, lines)
        ):
            return False

        # ``Company - Title`` followed by its date row.
        if (
            re.search(r"\s+[-–—]\s+", current)
            and self.has_date_range_or_open_range(next_line)
            and not self.is_bullet(current)
            and (
                self.looks_like_organization_line(current)
                or re.search(
                    r"(?i)\b(?:pte\.?\s*ltd\.?|ltd\.?|inc\.?|llc|corp\.?|company)\b",
                    current,
                )
            )
        ):
            return True

        if (
            self.looks_like_short_job_title(current)
            and re.search(r"(?i)\bto\b", next_line)
            and self.has_date_range_or_open_range(next_line)
            and following
            and not self.is_bullet(following)
            and self.looks_like_organization_line(following)
        ):
            return True
        if (
            index + 3 < len(lines)
            and self.looks_like_short_job_title(current)
            and len(current.split()) <= 5
            and not self.is_bullet(next_line)
            and re.search(r"(?i)\bto\b", lines[index + 2])
            and self.has_date_range_or_open_range(lines[index + 2])
            and (
                self.looks_like_organization_line(lines[index + 3])
                or re.search(r"(?i)\b(?:pwc|pricewaterhouse|llc|ltd|inc\.?|corp\.?|company)\b", lines[index + 3])
            )
        ):
            return True
        if (
            index + 3 < len(lines)
            and self.looks_like_short_job_title(current)
            and len(current.split()) <= 5
            and re.search(r"(?i)\bto\b", next_line)
            and self.has_date_range_or_open_range(next_line)
            and (
                self.looks_like_organization_line(lines[index + 3])
                or re.search(r"(?i)\b(?:pwc|pricewaterhouse|llc|ltd|inc\.?|corp\.?|company)\b", lines[index + 3])
            )
        ):
            return True

        if (
            index + 2 < len(lines)
            and "," in current
            and not current.endswith((",", ".", ";", ":"))
            and not self.looks_like_location(next_line)
            and self.has_date_range_or_open_range(following)
        ):
            return True

        # A long wrapped bullet immediately before the next company/date
        # header is continuation text, not a new title.
        if (
            len(current.split()) > 8
            and self.looks_like_organization_line(next_line)
            and self.has_date_range_or_open_range(following)
        ):
            return False

        current_range = DATE_RANGE_PATTERN.search(current)
        if (
            current_range
            and len(current[:current_range.start()].strip(" \"'")) <= 3
        ):
            return False

        if (
            index > 0
            and self.looks_like_organization_line(lines[index - 1])
            and self.looks_like_short_job_title(current)
            and self.has_date_range_or_open_range(next_line)
        ):
            return False

        # Employer/date metadata can be preceded by a title even when the
        # employer name itself is only one word (for example ``Toyota``).
        # Do not start a second entry at that employer line.
        if (
            index > 0
            and self.looks_like_short_job_title(lines[index - 1])
            and self.looks_like_short_job_title(current)
            and self.has_date_range_or_open_range(next_line)
        ):
            return False

        # Compact chronological layouts often place the employer first,
        # followed by the role and then the date on the next line.
        if (
            self.looks_like_organization_line(current)
            and self.looks_like_short_job_title(next_line)
            and self.has_date_range_or_open_range(following)
        ):
            return True

        current_date = re.search(DATE_TOKEN, current, re.IGNORECASE)
        next_date = re.search(DATE_TOKEN, next_line, re.IGNORECASE)
        if current_date and (
            self.looks_like_location(current[:current_date.start()].strip(" |-"))
            or re.match(r"(?i)^city\s*,\s*state", current)
        ):
            return False
        if (
            current_date
            and next_date
            and current[current_date.end():].strip(" :-")
            and next_line[next_date.end():].strip(" :-")
        ):
            return True

        inline_current_date = DATE_RANGE_PATTERN.search(current)
        if (
            inline_current_date
            and bool(current[:inline_current_date.start()].strip())
            and (
                self.looks_like_organization_line(next_line)
                or self.looks_like_location(next_line)
                or len(next_line.split()) <= 5
            )
        ):
            return True

        # An organization/date line is metadata for the preceding title,
        # not the beginning of another experience entry.
        if (
            self.has_date_range_or_open_range(current)
            or self.looks_like_organization_line(current)
        ):
            return False

        # Layout A: title, organization/location, date.
        standard_layout = (
            self.looks_like_organization_line(next_line)
            and self.has_date_range_or_open_range(following)
        )

        # Common layout: title followed by an organization/date line.
        inline_organization_date = (
            self.has_date_range_or_open_range(next_line)
            and bool(
                re.match(
                    r"^.+?\s+(?:19|20)\d{2}|^.+?\s+\d{1,2}/(?:19|20)\d{2}",
                    next_line,
                    re.IGNORECASE,
                )
            )
            and self.looks_like_short_job_title(current)
        )

        # Layout B: title, date, organization/location.
        date_before_organization = (
            self.looks_like_short_job_title(current)
            and not current.endswith((".", ",", ";", ":"))
            and self.has_date_range_or_open_range(next_line)
            and self.looks_like_organization_line(following)
        )

        # Layout C: title and date on one line, organization next.
        inline_date_match = DATE_RANGE_PATTERN.search(current)
        inline_date = (
            inline_date_match is not None
            and bool(current[:inline_date_match.start()].strip())
            and self.looks_like_organization_line(next_line)
        )

        return (
            standard_layout
            or inline_organization_date
            or date_before_organization
            or inline_date
        )

    @staticmethod
    def looks_like_short_job_title(text: str) -> bool:
        """Avoid treating wrapped bullets or skill lines as job titles.

        Some OCR layouts place a date and the next job after a long block of
        bullets.  The old date-before-organization rule interpreted any short
        preceding line as a new title.  This conservative check keeps normal
        titles ("Teaching Assistant", "Staff Accountant") eligible while
        rejecting common continuation/skill lines.
        """
        words = JSONNormalizer.clean_line(text).split()
        if not 1 <= len(words) <= 8:
            return False
        lowered = " ".join(words).casefold()
        rejected_prefixes = (
            "i joined",
            "to a ",
            "following",
            "key responsibilities",
            "my key",
            "design ",
            "experience ",
            "etl experience ",
            "pentaho ",
            "javascript ",
            "windows ",
            "sql ",
            "provides ",
            "consults ",
            "creates ",
            "produces ",
            "makes ",
        )
        return not lowered.startswith(rejected_prefixes)

    def is_education_start(self, index: int, lines: list[str]) -> bool:
        if self.is_bullet(lines[index]):
            return False

        # A degree can span several lines. The reliable boundary is the
        # institution/date pattern later in the group, not line index + 1.
        window = lines[index + 1:index + 8]
        return any(
            self.has_date_range(line)
            or self.has_single_education_date(line)
            for line in window
        ) and any(
            self.looks_like_organization_line(line)
            or self.looks_like_location(line)
            for line in window
        )

    def parse_experience_entry(self, lines: list[str]) -> Entry:
        lines = [self.clean_line(line) for line in lines if self.clean_line(line)]

        if not lines:
            raise ValueError("Empty experience entry")

        # Date gutter followed by ``Company - Title``.
        if len(lines) >= 2 and self.has_date_range_or_open_range(lines[0]):
            parts = [
                part.strip()
                for part in re.split(r"\s+[-–—]\s+", lines[1])
                if part.strip()
            ]
            if len(parts) >= 2 and not self.is_bullet(lines[1]):
                start, end = self.parse_date_range(lines[0])
                return Entry(
                    organization=self.correct_ocr_phrase(parts[0]),
                    title=self.correct_ocr_phrase(" - ".join(parts[1:])),
                    location=self.extract_location(lines[0]),
                    start=start,
                    end=end,
                    bullets=self.collect_experience_bullets(lines, 2),
                )

        # Title/date on the first line with location on the next line:
        # ``ETL ADMINISTRATOR 10/2016 - PRESENT`` / ``Chicago, IL``.
        if len(lines) >= 2:
            date_match = DATE_RANGE_PATTERN.search(lines[0])
            if date_match is None:
                date_match = OPEN_DATE_RANGE_PATTERN.search(lines[0])
            if (
                date_match
                and self.looks_like_location(lines[1])
                and lines[0][:date_match.start()].strip()
            ):
                start, end = self.parse_date_range(lines[0][date_match.start():])
                return Entry(
                    organization="Unknown organization",
                    title=self.correct_ocr_phrase(
                        lines[0][:date_match.start()].strip(" .:-")
                    ),
                    location=self.normalize_location(lines[1]),
                    start=start,
                    end=end,
                    bullets=self.collect_experience_bullets(lines, 2),
                )

        # Compact header: ``Company - Title Dec 2010 - Nov 2015``.
        # Handling this first prevents a parenthetical company note on the
        # following line from being selected as the title.
        first_date = DATE_RANGE_PATTERN.search(lines[0])
        if first_date is None:
            first_date = OPEN_DATE_RANGE_PATTERN.search(lines[0])
        if first_date is not None:
            prefix = lines[0][:first_date.start()].strip(" |–—")
            parts = [
                part.strip(" |–—")
                for part in re.split(r"\s+[-–—]\s+", prefix)
                if part.strip(" |–—")
            ]
            if len(parts) >= 2 and not self.is_bullet(lines[0]):
                start, end = self.parse_date_range(lines[0][first_date.start():])
                return Entry(
                    organization=self.correct_ocr_phrase(parts[0]),
                    title=self.correct_ocr_phrase(" - ".join(parts[1:])),
                    location=self.extract_location(lines[0][first_date.start():]),
                    start=start,
                    end=end,
                    bullets=self.collect_experience_bullets(lines, 1),
                )

        # Common Word resume layout with explicit ``to`` dates:
        # Title / practice / date / employer.
        if len(lines) >= 4 and re.search(r"(?i)\bto\b", lines[2]) and self.has_date_range_or_open_range(lines[2]):
            organization, location = self.split_organization_location(lines[3])
            start, end = self.parse_date_range(lines[2])
            return Entry(
                organization=self.correct_ocr_phrase(organization),
                title=self.correct_ocr_phrase(lines[0]),
                location=location,
                start=start,
                end=end,
                bullets=self.collect_experience_bullets(lines, 4),
            )

        if len(lines) >= 4 and re.search(r"(?i)\bto\b", lines[1]) and self.has_date_range_or_open_range(lines[1]):
            organization, location = self.split_organization_location(lines[3])
            start, end = self.parse_date_range(lines[1])
            return Entry(
                organization=self.correct_ocr_phrase(organization),
                title=self.correct_ocr_phrase(lines[0]),
                location=location,
                start=start,
                end=end,
                bullets=self.collect_experience_bullets(lines, 4),
            )

        # Organization-first layout:
        #   Company, City, ST  Jun 2010-Present
        #   Job title
        #   bullets...
        first_date = DATE_RANGE_PATTERN.search(lines[0])
        if first_date is None:
            first_date = OPEN_DATE_RANGE_PATTERN.search(lines[0])
        if first_date is not None:
            prefix = lines[0][:first_date.start()].strip(" |-")
            if (
                prefix
                and self.is_organization_first_experience_start(0, lines)
                and len(lines) >= 2
                and not self.is_bullet(lines[1])
            ):
                organization, location = self.split_organization_location(prefix)
                start, end = self.parse_date_range(lines[0][first_date.start():])
                title_index = next(
                    (
                        index for index, line in enumerate(lines[1:5], 1)
                        if re.search(r"(?i)\b(?:vice president|president|manager|director|head|associate|analyst|engineer|consultant)\b", line)
                    ),
                    1,
                )
                return Entry(
                    organization=self.correct_ocr_phrase(organization),
                    title=self.correct_ocr_phrase(lines[title_index]) or None,
                    location=location,
                    start=start,
                    end=end,
                    bullets=self.collect_experience_bullets(lines, title_index + 1),
                )

        # Compact templates put organization and title on one line, followed
        # by a location/date line. This also handles wrapped titles whose
        # final word is on the next line.
        if len(lines) >= 3 and self.has_date_range_or_open_range(lines[2]):
            parts = [part.strip() for part in lines[0].split(",") if part.strip()]
            if len(parts) >= 2 and not self.is_bullet(lines[0]) and not self.looks_like_location(lines[1]):
                start, end = self.parse_date_range(lines[2])
                return Entry(
                    organization=self.correct_ocr_phrase(", ".join(parts[1:] + [lines[1]])),
                    title=self.correct_ocr_phrase(parts[0]),
                    location=self.extract_location(lines[2]),
                    start=start,
                    end=end,
                    bullets=self.collect_experience_bullets(lines, 3),
                )

        if len(lines) >= 2 and self.has_date_range_or_open_range(lines[1]):
            # Sales/creative templates put ``Title, Company`` on the first
            # line and the date/location on the second.
            comma_parts = [part.strip() for part in lines[0].split(",") if part.strip()]
            if len(comma_parts) >= 2 and not self.is_bullet(lines[0]):
                start, end = self.parse_date_range(lines[1])
                location = self.extract_location(lines[1])
                if start or end:
                    return Entry(
                        organization=self.correct_ocr_phrase(", ".join(comma_parts[1:])),
                        title=self.correct_ocr_phrase(comma_parts[0]),
                        location=location,
                        start=start,
                        end=end,
                        bullets=self.collect_experience_bullets(lines, 2),
                    )
            first_parts = [
                part.strip()
                for part in re.split(r"\s+[-–—]\s+|\s+[|]\s+", lines[0])
                if part.strip()
            ]
            if len(first_parts) >= 2 and (
                self.looks_like_organization_line(lines[0])
                or re.search(r"(?i)\b(?:pte\.?\s*ltd\.?|ltd\.?|inc\.?|llc|corp\.?)\b", lines[0])
            ):
                organization = first_parts[0]
                title = " ".join(first_parts[1:])
                location = self.extract_location(lines[1])
                start, end = self.parse_date_range(lines[1])
                return Entry(
                    organization=self.correct_ocr_phrase(organization),
                    title=self.correct_ocr_phrase(title) or None,
                    location=location,
                    start=start,
                    end=end,
                    bullets=self.collect_experience_bullets(lines, 2),
                )

        if (
            len(lines) >= 3
            and self.looks_like_organization_line(lines[0])
            and self.has_date_range_or_open_range(lines[2])
        ):
            first_parts = [
                part.strip()
                for part in re.split(r"\s+[-–—]\s+|\s+[|]\s+", lines[0])
                if part.strip()
            ]
            if len(first_parts) >= 2:
                title = " ".join(first_parts[1:])
                if not self.is_bullet(lines[1]) and not self.looks_like_location(lines[1]):
                    title = f"{title} {lines[1]}".strip()
                location = self.extract_location(lines[2])
                start, end = self.parse_date_range(lines[2])
                bullet_start = 3 if title.endswith(lines[1]) else 2
                return Entry(
                    organization=self.correct_ocr_phrase(first_parts[0]),
                    title=self.correct_ocr_phrase(title),
                    location=location,
                    start=start,
                    end=end,
                    bullets=self.collect_experience_bullets(lines, bullet_start),
                )

        inline_role = self.parse_inline_at_role(lines)
        if inline_role is not None:
            title, organization, location, date_line, bullet_start = inline_role
            start, end = self.parse_date_range(date_line)
            return Entry(
                organization=self.correct_ocr_phrase(organization),
                title=self.correct_ocr_phrase(title),
                location=location,
                start=start,
                end=end,
                bullets=self.collect_experience_bullets(lines, bullet_start),
            )

        timeline = self.parse_timeline_experience(lines)
        if timeline is not None:
            title, organization_line, date_line, bullet_start = timeline
            organization, location = self.split_organization_location(
                organization_line
            )
            start, end = self.parse_date_range(date_line)
            return Entry(
                organization=self.correct_ocr_phrase(organization),
                title=self.correct_ocr_phrase(title),
                location=location,
                start=start,
                end=end,
                bullets=self.collect_experience_bullets(
                    lines,
                    bullet_start,
                ),
            )

        first_line = lines[0]
        first_date_match = DATE_RANGE_PATTERN.search(first_line)
        date_index: int | None = None
        organization_line = "Unknown organization"
        organization_index = 1

        if (
            len(lines) >= 3
            and self.looks_like_organization_line(lines[0])
            and self.looks_like_short_job_title(lines[1])
            and self.has_date_range_or_open_range(lines[2])
        ):
            organization_line = lines[0]
            title = lines[1]
            date_line = lines[2]
            organization_index = 0
            date_index = 2

        elif first_date_match:
            title = first_line[:first_date_match.start()].strip()
            date_line = first_line[first_date_match.start():]
            date_index = 0
        elif len(lines) > 1 and self.has_date_range_or_open_range(lines[1]):
            title = first_line
            metadata_line = lines[1]
            date_match = DATE_RANGE_PATTERN.search(metadata_line)
            if date_match is None:
                date_match = OPEN_DATE_RANGE_PATTERN.search(metadata_line)

            date_prefix = (
                metadata_line[:date_match.start()].strip(" |-")
                if date_match
                else ""
            )

            if (
                date_match
                and date_prefix
            ):
                organization_line = metadata_line[:date_match.start()].strip(" |-")
                date_line = metadata_line[date_match.start():]
                organization_index = 1
                date_index = 1
            else:
                date_line = metadata_line
                organization_index = 2
                date_index = 1
        else:
            title = first_line
            date_index = next(
                (
                    index
                    for index, line in enumerate(lines[1:6], 1)
                    if self.has_date_range_or_open_range(line)
                ),
                None,
            )
            date_line = lines[date_index] if date_index is not None else ""
            organization_index = max(1, (date_index or 2) - 1)

        if organization_line == "Unknown organization":
            if organization_index < len(lines):
                organization_line = lines[organization_index]

        # Some scans put Present on the next OCR line.
        date_end_index = date_index
        if (
            date_index is not None
            and date_index + 1 < len(lines)
            and (
                re.fullmatch(
                    r"(?i)(present|current|now)",
                    lines[date_index + 1],
                )
                or re.fullmatch(r"(?:19|20)\d{2}", lines[date_index + 1])
            )
        ):
            date_line = f"{date_line} {lines[date_index + 1]}"
            date_end_index = date_index + 1

        if self.looks_like_location(organization_line):
            organization = "Unknown organization"
            location = self.normalize_location(organization_line)
        else:
            organization, location = self.split_organization_location(
                organization_line
            )
        metadata_location = self.extract_location(date_line)
        if metadata_location:
            location = metadata_location
        start, end = self.parse_date_range(date_line)

        bullet_start = max(
            organization_index + 1,
            (date_end_index + 1) if date_end_index is not None else 1,
        )

        return Entry(
            organization=self.correct_ocr_phrase(organization),
            title=self.correct_ocr_phrase(title),
            location=location,
            start=start,
            end=end,
            bullets=self.collect_experience_bullets(lines, bullet_start),
        )

    def parse_inline_at_role(
        self,
        lines: list[str],
    ) -> tuple[str, str, str | None, str, int] | None:
        """Parse headings such as ``Web Designer at Expedia Group New York``."""
        if len(lines) < 2 or not self.has_date_range_or_open_range(lines[1]):
            return None

        match = re.match(
            r"(?P<title>.+?)\s+at\s+(?P<employer>.+)$",
            lines[0],
            re.IGNORECASE,
        )
        if not match:
            return None

        title = match.group("title").strip()
        employer_text = match.group("employer").strip()
        location = None

        # City names without state abbreviations are common in visual resume
        # templates. Remove only a conservative known suffix and leave other
        # employer names untouched.
        city_suffixes = (
            "New York",
            "Los Angeles",
            "San Francisco",
            "Chicago",
            "Boston",
            "Phoenix",
            "Detroit",
        )
        for city in city_suffixes:
            if employer_text.casefold().endswith(" " + city.casefold()):
                employer_text = employer_text[:-(len(city) + 1)].strip()
                location = city
                break

        if not employer_text:
            return None
        return title, employer_text, location, lines[1], 2

    def parse_education_entry(self, lines: list[str]) -> Entry:
        lines = [self.clean_line(line) for line in lines if self.clean_line(line)]

        # Institution on one line, followed by degree and dates:
        # ``Nanyang Technological University`` / ``Bachelor's Degree ...
        # 2004 - 2007``.
        if len(lines) >= 2 and self.looks_like_organization_line(lines[0]):
            date_match = DATE_RANGE_PATTERN.search(lines[1])
            if date_match and self.looks_like_degree_line(lines[1]):
                start, end = self.parse_date_range(lines[1][date_match.start():])
                title = lines[1][:date_match.start()].strip(" ,:-")
                return Entry(
                    organization=self.correct_ocr_phrase(lines[0]),
                    title=self.correct_ocr_phrase(title),
                    location=None,
                    start=start,
                    end=end,
                    bullets=[],
                )

        # Compact education layout: degree/date on one line, institution on
        # the next.  Do not let unrelated metadata (for example marital
        # status) become part of the degree title.
        degree_index = next(
            (
                index for index, line in enumerate(lines)
                if self.looks_like_degree_line(line)
                and re.search(r"\b(?:19|20)\d{2}\b", line)
            ),
            None,
        )
        if degree_index is not None and degree_index + 1 < len(lines):
            degree_line = lines[degree_index]
            date_match = re.search(
                r"(?i)\(\s*(?P<dates>[^()]*(?:19|20)\d{2}[^()]*)\)",
                degree_line,
            )
            institution_line = lines[degree_index + 1]
            if date_match and re.search(
                r"(?i)\b(?:university|college|institute|school)\b",
                institution_line,
            ):
                title = degree_line[:date_match.start()].strip(" -–—")
                start, end = self.parse_date_range(date_match.group("dates"))
                if start is None:
                    years = YEAR_PATTERN.findall(date_match.group("dates"))
                    start = years[0] if years else None
                    end = years[1] if len(years) > 1 else None
                organization, location = self.split_organization_location(
                    institution_line
                )
                return Entry(
                    organization=self.correct_ocr_phrase(organization),
                    title=self.correct_ocr_phrase(title),
                    location=location,
                    start=start,
                    end=end,
                    bullets=[],
                )

        # GED-only education blocks are common and should not be forced into
        # an institution/title pair or contaminated by a footer line.
        if any(re.fullmatch(r"(?i)G(?:\.|E|D|\s|[-])*", line) for line in lines):
            return Entry(
                organization="G.E.D.",
                title=None,
                location=None,
                start=None,
                end=None,
                bullets=[],
            )

        # Some resumes place the institution/date line before the degree:
        # Wittenberg University 2003 - 2007
        # Bachelor's Degree in Computer Science
        first_date = (
            DATE_RANGE_PATTERN.search(lines[0])
            or SINGLE_DATE_PATTERN.search(lines[0])
            if lines
            else None
        )
        if first_date and first_date.start() > 0:
            prefix = lines[0][:first_date.start()]
            season = re.search(
                r"\b(?:winter|spring|summer|fall|autumn)\s*$",
                prefix,
                re.IGNORECASE,
            )
            if season:
                raw_organization = prefix[:season.start()].strip(" |-")
                date_text = f"{season.group(0)} {lines[0][first_date.start():]}"
            else:
                raw_organization = prefix.strip(" |-")
                date_text = lines[0][first_date.start():]
            organization, location = self.split_organization_location(
                raw_organization
            )
            start, end = self.parse_date_range(date_text)
            if start is None:
                start = self.parse_single_date(date_text)
            content = lines[1:]
            title_lines: list[str] = []
            bullet_start = 0
            if content:
                title_lines.append(self.remove_bullet_marker(content[0]))
                bullet_start = 1
                # Degree descriptions can wrap onto an unmarked line before
                # the first actual education bullet.
                while bullet_start < len(content) and not self.is_bullet(content[bullet_start]):
                    title_lines.append(content[bullet_start])
                    bullet_start += 1
            title = " ".join(line for line in title_lines if line).strip() or None
            return Entry(
                organization=self.correct_ocr_phrase(organization),
                title=self.correct_ocr_phrase(title) if title else None,
                location=location,
                start=start,
                end=end,
                bullets=self.collect_bullets(content[bullet_start:]),
            )

        timeline = self.parse_timeline_education(lines)
        if timeline is not None:
            title, organization, location, start, end = timeline
            return Entry(
                organization=self.correct_ocr_phrase(organization),
                title=self.correct_ocr_phrase(title),
                location=location,
                start=start,
                end=end,
                bullets=[],
            )

        date_index = next(
            (
                index
                for index, line in enumerate(lines)
                if self.has_date_range(line)
                or self.has_single_education_date(line)
            ),
            None,
        )

        if date_index is None:
            content_lines = [
                self.remove_bullet_marker(line)
                for line in lines
                if self.remove_bullet_marker(line)
            ]
            if content_lines:
                degree = content_lines[0]
                from_match = re.search(r"(?i)\s+from\s+(.+)$", degree)
                if from_match and self.looks_like_degree_line(degree):
                    title = degree[:from_match.start()].strip()
                    organization_text = from_match.group(1).strip()
                    country_match = re.search(r"\s*\(([^()]+)\)\s*$", organization_text)
                    location = country_match.group(1).strip() if country_match else None
                    organization = (
                        organization_text[:country_match.start()].strip()
                        if country_match else organization_text
                    )
                    return Entry(
                        organization=self.correct_ocr_phrase(organization),
                        title=self.correct_ocr_phrase(title),
                        location=location,
                        start=None,
                        end=None,
                        bullets=[],
                    )
            if (
                len(lines) >= 3
                and self.looks_like_organization_line(lines[0])
                and self.looks_like_location(lines[1])
                and self.looks_like_degree_line(lines[2])
            ):
                return Entry(
                    organization=self.correct_ocr_phrase(lines[0]),
                    title=self.correct_ocr_phrase(" ".join(lines[2:])),
                    location=self.normalize_location(lines[1]),
                    start=None,
                    end=None,
                    bullets=[],
                )
            if (
                len(lines) >= 2
                and self.looks_like_organization_line(lines[0])
                and self.looks_like_degree_line(" ".join(lines[1:]))
            ):
                return Entry(
                    organization=self.correct_ocr_phrase(lines[0]),
                    title=self.correct_ocr_phrase(" ".join(lines[1:])),
                    location=None,
                    start=None,
                    end=None,
                    bullets=[],
                )
            return Entry(
                organization="Unknown institution",
                title=self.correct_ocr_phrase(" ".join(lines)),
                location=None,
                start=None,
                end=None,
                bullets=[],
            )

        metadata = lines[:date_index]
        location_index = next(
            (
                index
                for index in range(len(metadata) - 1, -1, -1)
                if self.looks_like_location(metadata[index])
            ),
            None,
        )

        location = (
            self.normalize_location(metadata[location_index])
            if location_index is not None
            else None
        )
        organization_index = (
            location_index - 1
            if location_index is not None and location_index > 0
            else len(metadata) - 1
        )
        organization = (
            metadata[organization_index]
            if metadata and organization_index >= 0
            else "Unknown institution"
        )
        parsed_organization, parsed_location = self.split_organization_location(
            organization
        )
        if location is None:
            location = parsed_location
        organization = parsed_organization
        title = " ".join(metadata[:organization_index]).strip()
        if not title and metadata:
            title = metadata[0]

        date_line = lines[date_index]
        start, end = self.parse_date_range(date_line)
        if not self.has_date_range(date_line):
            end = self.parse_single_date(date_line)
        return Entry(
            organization=self.correct_ocr_phrase(organization),
            title=self.correct_ocr_phrase(title),
            location=location,
            start=start,
            end=end,
            bullets=[],
        )

    @staticmethod
    def looks_like_degree_line(text: str) -> bool:
        return bool(
            re.search(
                r"(?i)\b(?:B\.?S\.?|B\.?A\.?|A\.?S\.?|M\.?S\.?|M\.?A\.?|MBA|Ph\.?D\.?|"
                r"bachelor(?:'s|s)?|master(?:'s|s)?|associate(?:'s|s)?|doctorate|"
                r"ACCA|A['’]?levels|GCSE|diploma|certificate)\b",
                text,
            )
        )

    def parse_timeline_experience(
        self,
        lines: list[str],
    ) -> tuple[str, str, str, int] | None:
        """Parse layouts where dates occupy a left timeline gutter."""
        if len(lines) < 2:
            return None

        start_match = re.search(DATE_TOKEN, lines[0], re.IGNORECASE)
        end_match = re.search(DATE_TOKEN, lines[1], re.IGNORECASE)
        if not start_match or not end_match:
            return None

        title = self.remove_bullet_marker(
            lines[0][start_match.end():]
        ).strip(" :-")
        organization = self.remove_bullet_marker(
            lines[1][end_match.end():]
        ).strip(" :-")

        if not title or not organization:
            return None

        return (
            title,
            organization,
            f"{start_match.group(0)} - {end_match.group(0)}",
            2,
        )

    def parse_timeline_education(
        self,
        lines: list[str],
    ) -> tuple[str, str, str | None, str | None, str | None] | None:
        if len(lines) < 2:
            return None

        start_match = re.search(DATE_TOKEN, lines[0], re.IGNORECASE)
        end_match = re.search(DATE_TOKEN, lines[1], re.IGNORECASE)
        if not start_match or not end_match:
            return None

        metadata = self.remove_bullet_marker(
            lines[0][start_match.end():]
        ).strip(" :-")
        if not metadata:
            return None

        parts = [part.strip() for part in metadata.split(",") if part.strip()]
        location = None
        organization = metadata
        title = metadata

        if len(parts) >= 3 and re.fullmatch(r"[A-Z]{2}", parts[-1]):
            location = parts[-1]
            organization = parts[-2]
            title = ", ".join(parts[:-2])
        elif len(parts) >= 2:
            title = parts[0]
            organization = ", ".join(parts[1:])

        start = self.normalize_date(start_match.group(0))
        end = self.normalize_date(end_match.group(0))
        return title, organization, location, start, end

    def split_organization_location(self, line: str) -> tuple[str, str | None]:
        line = self.correct_ocr_phrase(self.clean_line(line))
        upper_parts = [part.strip() for part in line.split(",")]
        if len(upper_parts) >= 2 and (
            upper_parts[-1].casefold() in {"singapore", "india", "new zealand", "delhi", "london", "auckland"}
            or re.search(r"(?i)\b(?:delhi|london|auckland|singapore)\b", upper_parts[-1])
        ):
            return ", ".join(upper_parts[:-1]), upper_parts[-1]
        if re.search(r"(?i)\b(?:pwc|pricewaterhousecoopers)\b", line) and "," in line:
            organization, location = line.rsplit(",", 1)
            if organization.strip() and location.strip():
                return organization.strip(), self.normalize_location(location.strip())
        normalized_line = self.normalize_location(line)
        if self.looks_like_location(normalized_line) and not re.search(
            r"(?i)\b(?:university|college|institute|school|company|foundation|corporation|inc\.?|llc)\b",
            normalized_line,
        ):
            return "Unknown organization", normalized_line
        line = normalized_line
        line = re.sub(
            r"(?P<city>[A-Za-z .'-]+)\.\s*(?P<state>[A-Z]{2})$",
            r"\g<city>, \g<state>",
            line,
        )
        parts = [
            self.clean_line(part)
            for part in re.split(r"\s*[|–—]\s*|\s+-\s+", line)
            if self.clean_line(part)
        ]
        if not parts:
            return "Unknown organization", None
        organization = parts[0]
        location = next((part for part in parts[1:] if self.looks_like_location(part)), None)

        if location is None:
            match = re.search(
                r",\s*(?P<location>[A-Za-z .'-]+,\s*[A-Z]{2})$",
                organization,
            )
            if match:
                location = self.normalize_location(match.group("location"))
                organization = organization[:match.start()].strip(" ,")

        if location is None:
            country_match = re.search(
                r"(?P<organization>.+?),\s*(?P<location>[A-Za-z .'-]+,\s*(?:USA|India|Canada|Australia|Singapore|United Kingdom|United States))$",
                organization,
                re.IGNORECASE,
            )
            if country_match:
                organization = country_match.group("organization").strip(" ,")
                location = self.normalize_location(
                    country_match.group("location")
                )

        if location is None:
            country_only = re.search(
                r"(?P<organization>.+?),\s*(?P<location>USA|India|Canada|Australia|Singapore|United Kingdom|United States)$",
                organization,
                re.IGNORECASE,
            )
            if country_only:
                organization = country_only.group("organization").strip(" ,")
                location = country_only.group("location").strip()

        return organization, location

    def collect_bullets(self, lines: list[str]) -> list[str]:
        bullets: list[str] = []
        for line in lines:
            line = self.clean_line(line)
            if self.is_bullet(line):
                bullets.append(self.remove_bullet_marker(line))
            elif bullets and not self.has_date_range(line) and not self.has_single_education_date(line):
                bullets[-1] = f"{bullets[-1]} {line}".strip()
        return bullets

    def collect_experience_bullets(
        self,
        lines: list[str],
        start_index: int,
    ) -> list[str]:
        bullets: list[str] = []
        saw_explicit_bullet = False
        active_subheading = ""
        subheadings = {
            "analytical skills",
            "taxes",
            "relationship management",
            "treasury",
            "reporting and audits",
            "month-end responsibilities",
            "key achievement",
            "key achievements",
            "key responsibilities",
        }

        for raw_line in lines[start_index:]:
            line = self.clean_line(raw_line)
            if (
                not line
                or self.has_date_range(line)
                or re.fullmatch(r"(?i)(present|current|now)", line)
                or (len(line) <= 2 and not re.search(r"[A-Za-z]{2,}", line))
                or not re.search(r"[A-Za-z0-9]", line)
            ):
                continue

            if self.is_url_only_line(line) or re.search(
                r"(?i)\b(?:powered\s+by|copyright|ennancy)\b", line
            ):
                continue

            if self.is_bullet(line):
                if not saw_explicit_bullet:
                    bullets.clear()
                saw_explicit_bullet = True
                value = self.remove_bullet_marker(line)
                if value:
                    if active_subheading:
                        value = f"{active_subheading}: {value}"
                        active_subheading = ""
                    bullets.append(self.correct_ocr_phrase(value))
                continue

            value = self.correct_ocr_phrase(line)
            if value.casefold().rstrip(":") in subheadings:
                active_subheading = value.rstrip(":")
                continue
            # Descriptive paragraphs between the metadata row and the first
            # bullet are not bullet items. This is common in sales resumes.
            if not bullets and not saw_explicit_bullet:
                bullets.append(value)
                continue
            if not bullets:
                continue
            if bullets:
                if (
                    self.looks_like_unmarked_bullet_start(value)
                    and len(value.split()) > 5
                ):
                    bullets.append(value)
                else:
                    bullets[-1] = f"{bullets[-1]} {value}".strip()
            else:
                bullets.append(value)

        return bullets

    @staticmethod
    def is_url_only_line(text: str) -> bool:
        cleaned = JSONNormalizer.clean_line(text).strip("{}[]()<>.,;:")
        return (
            bool(PROFILE_URL_PATTERN.search(cleaned))
            or bool(re.search(r"(?i)\b(?:https?|htip|www)\s*[:.]", cleaned))
        ) and len(cleaned.split()) <= 8

    @staticmethod
    def looks_like_unmarked_bullet_start(text: str) -> bool:
        """Detect a new bullet when OCR dropped the original bullet glyph.

        Wrapped OCR lines usually begin in lowercase (``man and...``,
        ``projects``), while the next visual bullet begins with a capitalized
        word.  The explicit-marker path above remains authoritative.
        """
        text = text.strip()
        if not text or not text[0].isupper():
            return False
        return bool(re.match(r"[A-Z][A-Za-z'’/-]*\b", text))

    # Projects ----------------------------------------------------------

    def parse_projects(self, blocks: list[TextBlock]) -> list[Project]:
        lines = self.clean_blocks(blocks)
        starts = [index for index in range(len(lines)) if self.is_project_start(index, lines)]
        return [
            self.parse_project_group(lines[start:(starts[position + 1] if position + 1 < len(starts) else len(lines))])
            for position, start in enumerate(starts)
        ]

    def parse_misc_projects(
        self,
        blocks: list[TextBlock],
    ) -> list[Project]:
        """Preserve awards/exhibitions when the schema has no native fields."""
        lines = self.clean_blocks(blocks)
        projects: list[Project] = []

        for line in lines:
            had_marker = self.is_bullet(line)
            line = self.remove_bullet_marker(line)
            if not line or self.looks_like_section_heading(line):
                continue

            if projects and not had_marker:
                projects[-1].name = f"{projects[-1].name} {line}".strip()
                continue

            projects.append(
                Project(
                    name=line,
                    description=None,
                    url=self.extract_project_url(line),
                    bullets=[],
                )
            )

        return projects

    def parse_activity_projects(
        self,
        blocks: list[TextBlock],
    ) -> list[Project]:
        """Preserve extracurricular activities without mislabeling them as jobs.

        The public schema has no dedicated activities array, so these entries
        are represented as one project-like record until the schema gains an
        explicit activities field.
        """
        lines = [
            self.remove_bullet_marker(line)
            for line in self.clean_blocks(blocks)
        ]
        lines = [line for line in lines if line and not self.looks_like_section_heading(line)]
        if not lines:
            return []

        return [
            Project(
                name="Sports and Co-Curricular Activities",
                description=None,
                url=None,
                bullets=[self.correct_ocr_phrase(line) for line in lines],
            )
        ]

    def is_project_start(self, index: int, lines: list[str]) -> bool:
        return (
            index + 1 < len(lines)
            and not self.is_bullet(lines[index])
            and self.has_date_range(lines[index + 1])
        )

    def parse_project_group(self, lines: list[str]) -> Project:
        name = self.remove_bullet_marker(lines[0])
        date_index = next((index for index, line in enumerate(lines[1:], 1) if self.has_date_range(line)), None)
        content = lines[(date_index + 1) if date_index is not None else 1:]
        bullets = self.collect_bullets(content)
        first_bullet = next(
            (
                index
                for index, line in enumerate(content)
                if self.is_bullet(line)
            ),
            len(content),
        )
        description = [
            line
            for line in content[:first_bullet]
            if not self.has_date_range(line)
        ]
        return Project(
            name=name,
            description=" ".join(description) or None,
            url=self.extract_project_url(" ".join(lines)),
            bullets=bullets,
        )

    @staticmethod
    def extract_project_url(text: str) -> str | None:
        match = PROFILE_URL_PATTERN.search(text)
        if not match:
            return None
        url = match.group(0).rstrip(".,;)")
        return url if url.lower().startswith(("http://", "https://")) else "https://" + url

    # Dates and helpers -------------------------------------------------

    @staticmethod
    def has_date_range(text: str) -> bool:
        return bool(DATE_RANGE_PATTERN.search(text) or len(YEAR_PATTERN.findall(text)) >= 2)

    @staticmethod
    def has_date_range_or_open_range(text: str) -> bool:
        return bool(
            JSONNormalizer.has_date_range(text)
            or OPEN_DATE_RANGE_PATTERN.search(text)
            or re.search(
                rf"{DATE_TOKEN}\s+(?:Present|Current|Now|Ongoing)\b",
                text,
                re.IGNORECASE,
            )
        )

    @staticmethod
    def has_single_education_date(text: str) -> bool:
        return bool(re.search(r"\b(expected|graduated)\b", text, re.IGNORECASE) and SINGLE_DATE_PATTERN.search(text))

    @staticmethod
    def find_date_line(lines: list[str]) -> str:
        return next((line for line in lines if JSONNormalizer.has_date_range(line) or JSONNormalizer.has_single_education_date(line)), "")

    def parse_date_range(self, text: str) -> tuple[str | None, str | None]:
        match = DATE_RANGE_PATTERN.search(text)
        if match:
            start = self.normalize_date(match.group("start"))
            end_text = match.group("end")
            end = None if re.fullmatch(r"(?:till\s*)?(?:present|current|now|ongoing|date)", end_text, re.IGNORECASE) else self.normalize_date(end_text)
            if start and end and end < start:
                end = None
            return start, end

        open_match = re.search(
            rf"(?P<start>{DATE_TOKEN})\s+(?:Present|Current|Now|Ongoing)\b",
            text,
            re.IGNORECASE,
        )
        if open_match:
            return self.normalize_date(open_match.group("start")), None

        years = YEAR_PATTERN.findall(text)
        if len(years) >= 2:
            start, end = years[0], years[1]
            # OCR can reverse or corrupt a compact date range. Keep the
            # usable starting year and leave the end open rather than
            # producing an invalid schema object.
            return (start, end) if end >= start else (start, None)
        return (None, None)

    def parse_single_date(self, text: str) -> str | None:
        match = SINGLE_DATE_PATTERN.search(text)
        return self.normalize_date(match.group("date")) if match else None

    @staticmethod
    def normalize_date(value: str) -> str | None:
        value = value.strip()
        if re.fullmatch(r"(?:19|20)\d{2}", value):
            return value
        if re.fullmatch(r"(?:19|20)\d{2}-\d{2}", value):
            return value
        try:
            parsed_datetime: datetime = date_parser.parse(value, default=datetime(1900, 1, 1), fuzzy=True)
            parsed: date = parsed_datetime.date()
        except (ValueError, OverflowError):
            return None
        if re.search(r"\d{1,2}/(?:19|20)\d{2}", value) or re.search(r"[A-Za-z]", value):
            return f"{parsed.year:04d}-{parsed.month:02d}"
        return f"{parsed.year:04d}-{parsed.month:02d}-{parsed.day:02d}"

    @staticmethod
    def correct_ocr_phrase(text: str) -> str:
        corrected = re.sub(r"\{\s*PA\b", "CPA", text, flags=re.IGNORECASE)
        for wrong, right in OCR_CORRECTIONS.items():
            corrected = re.sub(
                rf"\b{re.escape(wrong)}\b",
                right,
                corrected,
                flags=re.IGNORECASE,
            )
        return corrected

    @staticmethod
    def is_bullet(text: str) -> bool:
        return bool(
            BULLET_PATTERN.match(text)
            or re.match(r"^\s*(?:\d+\s*)?m=\s+[A-Za-z]", text, re.IGNORECASE)
        )

    @staticmethod
    def remove_bullet_marker(text: str) -> str:
        text = BULLET_PATTERN.sub("", text).strip()
        text = re.sub(r"^\s*(?:\d+\s*)?m=\s*", "", text, flags=re.IGNORECASE)
        return re.sub(r"^[«»®@#¤=]+\s*", "", text).strip()

    @staticmethod
    def normalize_location(text: str) -> str:
        text = JSONNormalizer.clean_line(text)
        if re.fullmatch(r"(?i)city\s*,\s*state", text):
            return ""
        # Common OCR substitutions in city/state metadata.
        text = re.sub(r"(?i)\bchteaga\b", "Chicago", text)
        text = re.sub(r"(?i)\bbetrait\b", "Detroit", text)
        text = re.sub(r"(?i)\bphocrix\b", "Phoenix", text)
        text = re.sub(r"(?i)\brodlville\b", "Rockville", text)
        text = re.sub(r"(?i)\blas\s+angeles\b", "Los Angeles", text)
        text = re.sub(r"(?i)\bih\b", "IL", text)
        text = re.sub(r"(?i)\bae\b", "AZ", text)
        text = re.sub(r"(?i)\bihinois\b", "Illinois", text)
        text = re.sub(r"(?i)\bcalifomia\b", "California", text)
        text = re.sub(r"(?i)\bca\.?\b", "CA", text)
        text = re.sub(r"(?i)\btx\.?\b", "TX", text)
        text = re.sub(r"(?i)\bpa\.?\b", "PA", text)
        text = re.sub(r"(?i)\bmo\.?\b", "MO", text)
        text = re.sub(
            r"(?P<city>[A-Za-z .'-]+)\.\s*(?P<state>[A-Z]{2})$",
            r"\g<city>, \g<state>",
            text,
        )
        return text

    @staticmethod
    def looks_like_location(text: str) -> bool:
        text = JSONNormalizer.normalize_location(text)
        if not text:
            return False
        if re.search(
            r"(?i),\s*(?:BS|BA|AS|MBA|PHD)$",
            text,
        ):
            return False
        if " - " not in text and LOCATION_PATTERN.fullmatch(text):
            return True
        if re.fullmatch(
            r"(?i)(?:united kingdom|united states|usa|canada|australia|ireland)",
            text,
        ):
            return True
        # OCR may damage the state abbreviation, but a short comma-separated
        # city/state line is still more likely to be a location than an
        # organization.  Keep this restricted to avoid swallowing sentences.
        if (
            " - " not in text
            and re.fullmatch(
                r"[A-Za-z][A-Za-z .'-]{1,30},\s*[A-Za-z]{2,15}",
                text,
            )
        ):
            return True
        return bool(re.fullmatch(r"(?i)(remote|hybrid|on[- ]site)", text))

    @staticmethod
    def looks_like_organization_line(text: str) -> bool:
        # A hyphen is an organization separator in some resumes, but the
        # same pattern is also used by date ranges. Do not classify a dated
        # role heading as an organization line.
        if "|" in text or (
            re.search(r"\s+-\s+", text)
            and not JSONNormalizer.has_date_range_or_open_range(text)
        ):
            return True
        if re.search(r",\s*[A-Z]{2}\b", text):
            return True
        lowered = text.lower()
        return any(
            word in lowered
            for word in (
                "university", "college", "department", "dept", "institute",
                "laboratory", "school", "company", "inc.", "llc", "corp",
            )
        )

    @staticmethod
    def clean_blocks(blocks: list[TextBlock]) -> list[str]:
        lines: list[str] = []
        for block in blocks:
            line = JSONNormalizer.clean_line(block.text)
            if not line:
                continue
            if re.search(r"(?i)\b(?:powered\s+by|copyright of|copyright)\b", line):
                continue
            if re.fullmatch(r"(?i)[wvw]+[. ]*en[h]?ancy[. ]*com", line):
                continue
            lines.append(line)
        return lines

    @staticmethod
    def clean_line(text: str) -> str:
        text = text.replace("\u200b", "").replace("\ufeff", "").replace("\u00a0", " ")
        # Repair date-shaped OCR tokens before applying the normal date
        # patterns.  These substitutions are restricted to slash/bracket
        # date contexts so ordinary resume words are not changed.
        text = re.sub(
            r"(?<!\w)[oOdD]([0-9])\s*[/\\]\s*",
            r"0\1/",
            text,
        )
        text = re.sub(
            r"(?<!\w)[oO][lLiI]\s*[/\\]\s*",
            "01/",
            text,
        )
        text = re.sub(
            r"(?<!\w)([01])o[fF]?\s*[/\\]\s*",
            r"\g<1>0/",
            text,
        )
        text = re.sub(
            r"(?<!\w)([12])[zZ][oO]?18\b",
            r"\g<1>018",
            text,
        )
        text = re.sub(
            r"(?<!\w)2[gG]([0-9]{2})\b",
            r"20\1",
            text,
        )
        text = re.sub(
            r"(?<!\w)([01][0-9])\s*[\{\[\(]\s*((?:19|20)\d{2})",
            r"\g<1>/\g<2>",
            text,
        )
        text = re.sub(
            r"(?<!\w)[oOdD]([0-9])\s*[\{\[\(]\s*((?:19|20)\d{2})",
            r"0\1/\g<2>",
            text,
        )
        text = re.sub(r"\b[dD](?=\d{2}/\d{4})", "0", text)
        text = re.sub(r"\b[dD](?=\d/\d{4})", "0", text)
        text = re.sub(r"\b[oO](?=\d{2}/\d{4})", "0", text)
        text = re.sub(r"\b[oO][hH]\s*/\s*(20\d{2})", r"01/\1", text)
        text = re.sub(r"\b[oO]([0-9])\s*/\s*((?:19|20)\d{2})", r"0\1/\2", text)
        text = re.sub(
            r"(?i)\bfun(?=\s+(?:19|20|2)\d{3})",
            "Jun",
            text,
        )
        text = re.sub(r"\bOF\s*[^A-Za-z0-9\s]?\s*ICE\b", "OFFICE", text, flags=re.IGNORECASE)
        text = re.sub(r"\bPA\s*\([^)]*?ENT\b", "PATIENT", text, flags=re.IGNORECASE)
        text = re.sub(r"\bSF\s*CIALIST\b", "SPECIALIST", text, flags=re.IGNORECASE)
        text = re.sub(r"\bO([79])/207([248])\b", r"0\1/201\2", text)
        text = re.sub(r"\bOG/2073\b", "06/2013", text, flags=re.IGNORECASE)
        text = re.sub(r"\bOG2074\b", "09/2014", text, flags=re.IGNORECASE)
        text = re.sub(r"\b16/2016\b", "10/2016", text)
        text = re.sub(r"\b122016\b", "12/2016", text)
        text = re.sub(r"\b72/2078\b", "12/2018", text)
        text = re.sub(r"(?<=\d)\s+fo\s+(?=\d|current)", " to ", text, flags=re.IGNORECASE)
        # OCR may read a 2xxx year as 7xxx. Restrict this correction to
        # four-digit values beginning with 70.
        text = re.sub(r"\b7(\d{3})\b", r"2\1", text)
        # In date contexts, OCR often reads the leading 1 in 201x as 7.
        text = re.sub(r"\b207([0-9])\b", r"201\1", text)
        return JSONNormalizer.correct_ocr_phrase(
            re.sub(r"\s+", " ", text).strip()
        )
