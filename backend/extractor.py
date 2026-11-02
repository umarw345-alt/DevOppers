from __future__ import annotations

import io
import re
from collections import defaultdict
from typing import Any

import cv2
import numpy as np
import pymupdf
import pytesseract
from PIL import Image
from pytesseract import Output
from rapidfuzz import fuzz, process

from .internal_models import (
    Rectangle,
    SourceType,
    TextBlock,
    WordToken,
)


class ContentExtractor:
    """Extract text and layout information from PDFs and JPEG files."""

    OCR_DPI = 300
    OCR_LANGUAGE = "eng"
    PRELIMINARY_PSM = 3
    REGION_PSM = 6
    TEXT_LAYER_THRESHOLD = 20
    LAYOUT_MAX_DIMENSION = 1800
    MIN_COLUMN_WORDS = 8
    MIN_COLUMN_GUTTER = 24.0

    SECTION_HEADINGS = (
        "summary",
        "profile",
        "professional summary",
        "personal statement",
        "power statement",
        "objective",
        "about",
        "experience",
        "employment history",
        "professional experience",
        "work experience",
        "employment",
        "education",
        "projects",
        "project experience",
        "skills",
        "skills abilities",
        "core competencies",
        "strengths",
        "languages",
        "industry expertise",
        "accomplishments",
        "key skills",
        "technical skills",
        "hard skills",
        "soft skills",
        "software",
        "programming",
        "programming languages",
        "certifications",
        "awards",
        "honors",
        "exhibitions",
        "commission",
        "commissions",
        "personal info",
    )

    def extract(
        self,
        file_bytes: bytes,
        mime_type: str,
    ) -> list[TextBlock]:
        if mime_type == "application/pdf":
            return self.extract_pdf(file_bytes)

        if mime_type == "image/jpeg":
            return self.extract_jpeg(file_bytes)

        raise ValueError(f"Unsupported MIME type: {mime_type}")

    def has_text_layer(self, file_bytes: bytes) -> bool:
        document = pymupdf.open(
            stream=file_bytes,
            filetype="pdf",
        )

        try:
            return any(
                len(page.get_text("text").strip())
                >= self.TEXT_LAYER_THRESHOLD
                for page in document
            )
        finally:
            document.close()

    def extract_pdf(
        self,
        file_bytes: bytes,
    ) -> list[TextBlock]:
        """Use embedded text per page and OCR scanned pages."""
        document = pymupdf.open(
            stream=file_bytes,
            filetype="pdf",
        )
        blocks: list[TextBlock] = []

        try:
            for page_index, page in enumerate(document):
                page_number = page_index + 1
                embedded_text = page.get_text("text").strip()

                if len(embedded_text) >= self.TEXT_LAYER_THRESHOLD:
                    blocks.extend(
                        self.extract_embedded_page(
                            page,
                            page_number,
                        )
                    )
                else:
                    blocks.extend(
                        self.extract_ocr_page(
                            page,
                            page_number,
                        )
                    )

            return blocks
        finally:
            document.close()

    def extract_embedded_page(
        self,
        page: Any,
        page_number: int,
    ) -> list[TextBlock]:
        page_dict = page.get_text("dict")
        blocks: list[TextBlock] = []

        for raw_block in page_dict.get("blocks", []):
            if raw_block.get("type") != 0:
                continue

            for raw_line in raw_block.get("lines", []):
                words: list[WordToken] = []

                for span in raw_line.get("spans", []):
                    text = self.clean_text(span.get("text", ""))
                    bbox = span.get("bbox")

                    if not text or not bbox:
                        continue

                    words.append(
                        WordToken(
                            text=text,
                            confidence=100.0,
                            bounding_box=Rectangle(
                                x0=float(bbox[0]),
                                y0=float(bbox[1]),
                                x1=float(bbox[2]),
                                y1=float(bbox[3]),
                            ),
                            page_number=page_number,
                            source=SourceType.PDF_TEXT,
                            font_size=float(span.get("size", 0.0)),
                        )
                    )

                if not words:
                    continue

                text = self.clean_text(
                    " ".join(word.text for word in words)
                )
                font_size = max(
                    word.font_size or 0.0
                    for word in words
                )

                blocks.append(
                    TextBlock(
                        text=text,
                        confidence=100.0,
                        bounding_box=self.combine_boxes(words),
                        page_number=page_number,
                        is_heading=self.looks_like_heading(
                            text,
                            font_size,
                        ),
                        words=words,
                        source=SourceType.PDF_TEXT,
                        font_size=font_size,
                    )
                )

        return blocks

    def extract_ocr_page(
        self,
        page: Any,
        page_number: int,
    ) -> list[TextBlock]:
        pixmap = page.get_pixmap(
            dpi=self.OCR_DPI,
            colorspace=pymupdf.csRGB,
            alpha=False,
        )

        image = Image.frombytes(
            "RGB",
            [pixmap.width, pixmap.height],
            pixmap.samples,
        )

        return self.extract_ocr_image(
            image,
            page_number,
            dpi=self.OCR_DPI,
        )

    def extract_jpeg(
        self,
        file_bytes: bytes,
    ) -> list[TextBlock]:
        image = Image.open(
            io.BytesIO(file_bytes)
        ).convert("RGB")

        return self.extract_ocr_image(
            image,
            page_number=1,
            dpi=None,
        )

    def extract_ocr_image(
        self,
        image: Image.Image,
        page_number: int,
        dpi: int | None,
    ) -> list[TextBlock]:
        """OCR one image, using separate column crops when detected."""
        # Layout detection does not need the full 300-DPI raster.  Keeping a
        # smaller, physically scaled copy for this first pass substantially
        # reduces preprocessing and Tesseract time on scanned PDFs. Region
        # OCR below still uses the original image, so layout reduction does
        # not reduce final text quality. The adjusted DPI preserves
        # coordinates in the original page's point system.
        layout_image = image
        layout_dpi = dpi
        if dpi and max(image.size) > self.LAYOUT_MAX_DIMENSION:
            layout_scale = self.LAYOUT_MAX_DIMENSION / max(image.size)
            layout_image = image.resize(
                (
                    max(1, int(image.width * layout_scale)),
                    max(1, int(image.height * layout_scale)),
                ),
                Image.Resampling.BILINEAR,
            )
            layout_dpi = dpi * layout_scale

        layout_image = self.preprocess_image(layout_image)

        # First pass: obtain approximate word locations and identify
        # whether the page has a multi-column layout.
        preliminary_words = self.run_tesseract_ocr(
            layout_image,
            page_number=page_number,
            dpi=layout_dpi,
            psm=self.PRELIMINARY_PSM,
            column="preliminary",
        )
        preliminary_blocks = self.group_words_into_lines(
            preliminary_words
        )

        body_top = self.find_body_top(preliminary_blocks)
        split_x = self.find_column_split(
            preliminary_words,
            body_top=body_top,
        )

        # PSM 3 is efficient for ordinary pages, but dense single-column
        # templates can collapse the whole page into a few long lines. A low
        # confidence page gets one sparse-layout pass so headings, bullets,
        # and compact job headers remain separately addressable.
        average_confidence = (
            sum(block.confidence for block in preliminary_blocks)
            / len(preliminary_blocks)
            if preliminary_blocks
            else 0.0
        )
        if split_x is None and average_confidence < 60.0:
            sparse_words = self.run_tesseract_ocr(
                layout_image,
                page_number=page_number,
                dpi=layout_dpi,
                psm=11,
                column="preliminary",
            )
            sparse_blocks = self.group_words_into_lines(sparse_words)
            if len(sparse_blocks) > len(preliminary_blocks):
                preliminary_blocks = sparse_blocks
                body_top = self.find_body_top(preliminary_blocks)

        if split_x is None:
            final_blocks = preliminary_blocks
        else:
            final_blocks = self.ocr_regions(
                original_image=image,
                preliminary_blocks=preliminary_blocks,
                page_number=page_number,
                dpi=dpi,
                split_x=split_x,
                body_top=body_top or 0,
            )

        # Sidebar contact information is often lower than the main column's
        # first heading. OCR it as its own region only when the preliminary
        # pass did not already recover a complete contact line.
        # Do not run a broad header crop merely because a city/state was not
        # recognized.  If an email and phone are already present, retrying
        # cannot improve the contact payload and can cost several seconds on
        # a page-sized crop.
        header_text = " ".join(
            block.text
            for block in preliminary_blocks
            if body_top is None or block.bounding_box.y0 < body_top
        )
        has_header_email = bool(re.search(r"@|\bemail\b", header_text, re.I))
        has_header_phone = bool(
            re.search(r"(?<!\d)\d{3}\D+\d{3}\D+\d{2,4}(?!\d)", header_text)
            or len(re.sub(r"\D", "", header_text)) >= 7
        )
        if not (has_header_email and has_header_phone):
            final_blocks.extend(
                self.ocr_contact_header(
                    original_image=image,
                    preliminary_blocks=preliminary_blocks,
                    body_top=body_top,
                    page_number=page_number,
                    dpi=dpi,
                )
            )

        if split_x is None and average_confidence < 60.0:
            final_blocks.extend(
                self.ocr_top_banner(
                    original_image=image,
                    page_number=page_number,
                    dpi=dpi,
                )
            )
        final_blocks.extend(
            self.ocr_contact_sidebar(
                original_image=image,
                preliminary_blocks=preliminary_blocks,
                split_x=split_x,
                page_number=page_number,
                dpi=dpi,
            )
        )
        final_blocks.extend(
            self.ocr_graphical_skill_labels(
                original_image=image,
                preliminary_blocks=preliminary_blocks,
                split_x=split_x,
                page_number=page_number,
                dpi=dpi,
            )
        )

        recognized_name = None
        header_has_address = any(
            (body_top is None or block.bounding_box.y0 < body_top)
            and re.search(
                r"(?i)\b(?:street|st\.?|road|drive|avenue|island)\b",
                block.text,
            )
            for block in preliminary_blocks
        )
        if (
            not self.has_reliable_header_name(preliminary_blocks, body_top)
            or header_has_address
        ):
            recognized_name = self.recognize_header_name(
                original_image=image,
                preliminary_blocks=preliminary_blocks,
                body_top=body_top,
                dpi=dpi,
            )

        if recognized_name:
            final_blocks = self.replace_header_name(
                final_blocks,
                recognized_name,
                body_top,
            )

        # Auxiliary crops are appended after the main OCR pass. Restore
        # document order before normalization so a top banner cannot be
        # mistaken for content belonging to the last section.
        return sorted(
            final_blocks,
            key=lambda block: (
                block.page_number,
                block.bounding_box.y0,
                block.bounding_box.x0,
            ),
        )

    def ocr_top_banner(
        self,
        original_image: Image.Image,
        page_number: int,
        dpi: int | None,
    ) -> list[TextBlock]:
        """Re-read a compact name/contact banner at the top of a page."""
        width, height = original_image.size
        bottom = max(80, min(height, int(height * 0.20)))
        crop = original_image.crop((0, 0, width, bottom))
        crop = crop.resize((crop.width * 3, crop.height * 3), Image.Resampling.LANCZOS)
        words = self.run_tesseract_ocr(
            crop,
            page_number=page_number,
            dpi=(dpi * 3 if dpi else 216),
            psm=6,
            x_offset=0,
            y_offset=0,
            column="header",
        )
        # Contact banners are frequently confined to the upper-right portion
        # beside a large job title. A second sparse pass prevents the title
        # from crowding out the email and telephone line.
        right_start = int(width * 0.40)
        right_crop = original_image.crop((right_start, 0, width, bottom))
        right_crop = right_crop.resize(
            (right_crop.width * 3, right_crop.height * 3),
            Image.Resampling.LANCZOS,
        )
        words.extend(
            self.run_tesseract_ocr(
                right_crop,
                page_number=page_number,
                dpi=(dpi * 3 if dpi else 216),
                psm=6,
                x_offset=right_start * 3,
                y_offset=0,
                column="header",
            )
        )
        return self.group_words_into_lines(words)

    @classmethod
    def has_reliable_header_name(
        cls,
        blocks: list[TextBlock],
        body_top: float | None,
    ) -> bool:
        """Avoid a second name OCR pass when the first pass is sufficient."""
        return any(
            (body_top is None or block.bounding_box.y0 < body_top)
            and block.confidence >= 70.0
            and cls.looks_like_person_name(cls.clean_name_candidate(block.text))
            for block in blocks
        )

    @staticmethod
    def has_reliable_header_contact(
        blocks: list[TextBlock],
        body_top: float | None,
    ) -> bool:
        """Check whether the first pass found both phone and location data."""
        header_text = " ".join(
            block.text
            for block in blocks
            if body_top is None or block.bounding_box.y0 < body_top
        )
        has_phone = bool(
            re.search(
                r"(?<!\d)\d{3}\D+\d{3}\D+\d{4}(?!\d)",
                header_text,
            )
        )
        has_location = bool(
            re.search(
                r"\b[A-Z][A-Za-z .'-]+,\s*(?:[A-Z]{2}|[A-Za-z]{4,})\b",
                header_text,
            )
        )
        return has_phone and has_location

    def ocr_contact_header(
        self,
        original_image: Image.Image,
        preliminary_blocks: list[TextBlock],
        body_top: float | None,
        page_number: int,
        dpi: int | None,
    ) -> list[TextBlock]:
        """Re-OCR the compact address/phone line independently.

        A full-page pass can drop a digit when an address and phone number
        share one centered line.  A narrow, enlarged line crop gives
        Tesseract a second opportunity without changing the page reading
        order or replacing the original evidence.
        """
        candidates = [
            block
            for block in preliminary_blocks
            if (body_top is None or block.bounding_box.y0 < body_top)
            and re.search(r"\d", block.text)
            and not self.looks_like_person_name(block.text)
        ]
        if not candidates:
            return []

        target = min(candidates, key=lambda block: block.bounding_box.y0)
        scale = dpi / 72 if dpi else 1.0
        array = np.array(original_image.convert("RGB"))
        grayscale = cv2.cvtColor(array, cv2.COLOR_RGB2GRAY)
        # Preserve thin phone strokes in one pass and use Otsu in the other
        # through the already-preprocessed source image only when needed.
        crop_source = Image.fromarray(grayscale)
        header_candidates = [
            block for block in candidates
            if re.search(r"(?i)(?:phone|mobile|email|website|linkedin|@|www)", block.text)
        ]
        # Contact details are normally in a compact header panel. Prefer the
        # right half when labels are present there (as in the Robert Smith
        # template); otherwise retain the full-width narrow crop for headers
        # where phone and email share one line.
        right_panel = any(
            block.bounding_box.x0 > max(
                candidate.bounding_box.x1 for candidate in preliminary_blocks
            ) * 0.45
            for block in header_candidates
        )
        left = int(original_image.width * 0.42) if right_panel else 0
        top = max(0, int((target.bounding_box.y0 - 8) * scale))
        right = original_image.width
        bottom = min(
            original_image.height,
            int((target.bounding_box.y1 + 8) * scale),
        )
        if bottom <= top:
            return []

        crop = crop_source.crop((left, top, right, bottom))
        crop = crop.resize(
            (crop.width * 4, crop.height * 4),
            Image.Resampling.LANCZOS,
        )

        words = self.run_tesseract_ocr(
            crop,
            page_number=page_number,
            dpi=(dpi * 3 if dpi else 216),
            psm=6,
            x_offset=0,
            y_offset=top * 3,
            column="header",
        )

        return self.group_words_into_lines(words)

    def ocr_graphical_skill_labels(
        self,
        original_image: Image.Image,
        preliminary_blocks: list[TextBlock],
        split_x: float | None,
        page_number: int,
        dpi: int | None,
    ) -> list[TextBlock]:
        """Read labels inside graphical skill bubbles when present.

        A normal page OCR pass tends to treat filled circles and bars as
        decorative noise.  If a ``Programming`` heading is detected in a
        narrow column, make one inexpensive high-contrast pass over the
        remaining panel.  This is deliberately additive: ordinary text OCR
        remains the source of truth and no rating value is emitted.
        """
        if split_x is None or not preliminary_blocks:
            return []

        programming = [
            block for block in preliminary_blocks
            if self.clean_text(block.text).casefold().strip(" :-")
            in {"programming", "programming languages"}
            and (block.bounding_box.x0 + block.bounding_box.x1) / 2 < split_x
        ]
        if not programming:
            return []

        start_y = max(block.bounding_box.y1 for block in programming)
        scale = dpi / 72 if dpi else 1.0
        left = 0
        right = max(1, int((split_x - 6) * scale))
        top = max(0, int((start_y + 4) * scale))
        bottom = original_image.height
        if bottom <= top or right <= left:
            return []

        array = np.array(original_image.convert("RGB"))
        hsv = cv2.cvtColor(array, cv2.COLOR_RGB2HSV)
        # Filled colored shapes have substantially more saturation than the
        # pale sidebar. Use their bounding extent to avoid OCRing the whole
        # contact panel again; fall back to the full lower panel if the
        # template uses outlines instead of filled shapes.
        panel = hsv[top:bottom, left:right]
        mask = cv2.inRange(panel, (70, 35, 20), (150, 255, 220))
        nonzero = cv2.findNonZero(mask)
        if nonzero is not None:
            x, y, w, h = cv2.boundingRect(nonzero)
            if w >= 30 and h >= 30:
                left += max(0, x - 8)
                top += max(0, y - 8)
                right = min(right, left + w + 16)
                bottom = min(bottom, top + h + 16)

        crop = Image.fromarray(cv2.cvtColor(array, cv2.COLOR_RGB2GRAY)).crop(
            (left, top, right, bottom)
        )
        crop = crop.resize((crop.width * 3, crop.height * 3), Image.Resampling.LANCZOS)
        words = self.run_tesseract_ocr(
            crop,
            page_number=page_number,
            dpi=(dpi * 3 if dpi else 216),
            psm=11,
            x_offset=left * 3,
            y_offset=top * 3,
            # Let the normal column/heading classifier assign this to the
            # Skills section; using a synthetic column name would exclude it
            # from two-column section reconstruction.
            column="left",
        )
        # Bubble labels are small and often overlap the filled shape in a
        # whole-panel segmentation. A few relative, overlapping probes give
        # Tesseract a text-sized crop without assuming the rating values.
        if nonzero is not None:
            panel_width = max(1, right - left)
            panel_height = max(1, bottom - top)
            probes = (
                (0.08, 0.15, 0.50, 0.55),  # SQL-like left bubble
                (0.42, 0.05, 0.88, 0.45),  # HTML-like upper bubble
                (0.08, 0.45, 0.50, 0.88),  # UNIX-like lower-left bubble
                (0.38, 0.34, 0.70, 0.72),  # CSS-like center bubble
                (0.54, 0.55, 0.94, 0.99),  # Ruby-like lower-right bubble
            )
            for x0, y0, x1, y1 in probes:
                px0 = max(0, int(left + x0 * panel_width - 8))
                py0 = max(0, int(top + y0 * panel_height - 8))
                px1 = min(original_image.width, int(left + x1 * panel_width + 8))
                py1 = min(original_image.height, int(top + y1 * panel_height + 8))
                if px1 <= px0 or py1 <= py0:
                    continue
                probe = Image.fromarray(
                    cv2.cvtColor(array, cv2.COLOR_RGB2GRAY)
                ).crop((px0, py0, px1, py1))
                probe = Image.fromarray(
                    cv2.threshold(
                        np.array(probe),
                        150,
                        255,
                        cv2.THRESH_BINARY,
                    )[1]
                )
                probe = probe.resize(
                    (probe.width * 5, probe.height * 5),
                    Image.Resampling.LANCZOS,
                )
                words.extend(
                    self.run_tesseract_ocr(
                        probe,
                        page_number=page_number,
                        dpi=(dpi * 5 if dpi else 360),
                        psm=6,
                        x_offset=px0 * 5,
                        y_offset=py0 * 5,
                        column="left",
                    )
                )
        programming_labels = (
            "SQL", "HTML5", "UNIX", "CSS", "Ruby on Rails", "Python",
            "Java", "JavaScript", "C++", "C#", "PHP", "Go", "R",
            "React", "Vue", "Angular", "Tableau", "Excel", "GIS",
        )
        label_words: list[WordToken] = []
        for word in words:
            candidate = self.clean_text(word.text).strip("|()[]{}.,;:").replace("5", "S")
            match = process.extractOne(candidate, programming_labels, scorer=fuzz.ratio)
            if not match:
                continue
            label, score, _ = match
            minimum = 62 if len(label) <= 4 else 70
            if score >= minimum:
                label_words.append(word.model_copy(update={"text": label}))
        return self.group_words_into_lines(label_words)

    def ocr_contact_sidebar(
        self,
        original_image: Image.Image,
        preliminary_blocks: list[TextBlock],
        split_x: float | None,
        page_number: int,
        dpi: int | None,
    ) -> list[TextBlock]:
        """Re-OCR a detected Personal Info sidebar independently."""
        if split_x is None or not preliminary_blocks:
            return []

        page_right = max(
            block.bounding_box.x1 for block in preliminary_blocks
        )
        personal_info = []

        for block in preliminary_blocks:
            candidate = self.clean_text(block.text).casefold()
            match = process.extractOne(
                candidate,
                ("personal info", "contact information", "contact"),
                scorer=fuzz.ratio,
            )
            if match and match[1] >= 55:
                personal_info.append(block)

        if not personal_info:
            return []

        start_y = min(block.bounding_box.y0 for block in personal_info)
        heading_center = sum(
            (block.bounding_box.x0 + block.bounding_box.x1) / 2
            for block in personal_info
        ) / len(personal_info)
        left_panel = heading_center < split_x
        next_heading_y: float | None = None

        for block in preliminary_blocks:
            block_center = (block.bounding_box.x0 + block.bounding_box.x1) / 2
            if (block_center < split_x) != left_panel:
                continue
            if block.bounding_box.y0 <= start_y:
                continue
            candidate = self.clean_text(block.text).casefold()
            match = process.extractOne(
                candidate,
                self.SECTION_HEADINGS,
                scorer=fuzz.ratio,
            )
            if match and match[1] >= 55:
                if next_heading_y is None or block.bounding_box.y0 < next_heading_y:
                    next_heading_y = block.bounding_box.y0

        scale = dpi / 72 if dpi else 1.0
        width, height = original_image.size
        if left_panel:
            left = 0
            right = min(width, int((split_x - 8) * scale))
        else:
            left = max(0, int((split_x - 20) * scale))
            right = width
        top = 0
        bottom = height
        if next_heading_y is not None:
            bottom = min(height, int((next_heading_y - 5) * scale))

        if bottom <= top or right <= left:
            return []

        array = np.array(original_image.convert("RGB"))
        grayscale = cv2.cvtColor(array, cv2.COLOR_RGB2GRAY)
        # Keep grayscale for contact fields; thresholding can remove the
        # dot in an email address or alter narrow phone digits.
        crop = Image.fromarray(grayscale).crop((left, top, right, bottom))
        crop = crop.resize(
            (crop.width * 2, crop.height * 2),
            Image.Resampling.LANCZOS,
        )

        words = self.run_tesseract_ocr(
            crop,
            page_number=page_number,
            dpi=(dpi * 2 if dpi else 144),
            psm=4,
            x_offset=left * 2,
            y_offset=top * 2,
            column="header",
        )
        return self.group_words_into_lines(words)

    def recognize_header_name(
        self,
        original_image: Image.Image,
        preliminary_blocks: list[TextBlock],
        body_top: float | None,
        dpi: int | None,
    ) -> str | None:
        """Run a dedicated OCR pass on the large header name.

        Full-page segmentation often misreads large names when nearby
        contact text or columns are present. PSM 8 and 13 treat the crop
        as a single word/line and work better for this region.
        """
        existing = [
            block for block in preliminary_blocks
            if body_top is not None
            and block.bounding_box.y0 < body_top
            and self.looks_like_person_name(self.clean_name_candidate(block.text))
            and not re.search(
                r"(?i)\b(?:street|st\.?|road|drive|avenue|island)\b",
                block.text,
            )
        ]
        existing_name = None
        if existing:
            best = max(
                existing,
                key=lambda block: (
                    len(self.clean_name_candidate(block.text)),
                    block.confidence,
                ),
            )
            existing_name = self.clean_name_candidate(best.text)

        # Some templates place the candidate's name inside a colored contact
        # banner rather than on the largest text line. Read the banner as a
        # compact line and use the two-to-four words before the first comma.
        width, height = original_image.size
        banner_height = max(80, int(height * (0.10 if dpi else 0.20)))
        banner = original_image.crop((0, 0, width, banner_height))
        banner = banner.resize(
            (banner.width * 3, banner.height * 3),
            Image.Resampling.LANCZOS,
        )
        banner_text = pytesseract.image_to_string(
            banner,
            lang=self.OCR_LANGUAGE,
            config="--oem 3 --psm 6",
            timeout=15,
        )
        for line in banner_text.splitlines():
            line = line.strip()
            banner_match = re.search(
                r"\b([A-Z][A-Za-z.'-]+(?:\s+[A-Z][A-Za-z.'-]+){1,3})\s*,",
                line,
            )
            candidate = self.clean_name_candidate(
                banner_match.group(1) if banner_match else line
            )
            if self.looks_like_person_name(candidate):
                if existing_name and any(
                    len(word) <= 2 for word in candidate.split()
                ):
                    return existing_name
                return candidate

        if existing_name:
            return existing_name

        candidates = [
            block
            for block in preliminary_blocks
            if (body_top is None or block.bounding_box.y0 < body_top)
            and 1 <= len(block.text.split()) <= 5
            and not self.looks_like_section_heading(block.text)
            and not any(
                label in self.clean_text(block.text).casefold()
                for label in (
                    "personal info",
                    "contact",
                    "phone",
                    "email",
                    "e-mail",
                    "linkedin",
                    "twitter",
                )
            )
        ]

        # Prepare the lightweight name image before either name-crop path.
        # This also covers pages where no plausible name block survived the
        # preliminary OCR pass.
        original_array = np.array(original_image.convert("RGB"))
        grayscale = cv2.cvtColor(original_array, cv2.COLOR_RGB2GRAY)
        name_image = Image.fromarray(
            cv2.threshold(
                grayscale,
                0,
                255,
                cv2.THRESH_BINARY + cv2.THRESH_OTSU,
            )[1]
        )

        if not candidates:
            # Some single-column templates place the name directly below a
            # job-title line. The first OCR candidate then points at the
            # title, so its crop never reaches the actual name. Read a
            # narrow upper-left name band once as a cheap fallback.
            band_top = int(height * 0.04)
            band_bottom = int(height * 0.18)
            band_right = int(width * 0.72)
            band = name_image.crop((0, band_top, band_right, band_bottom))
            band = band.resize(
                (band.width * 4, band.height * 4),
                Image.Resampling.LANCZOS,
            )
            for psm in (6, 7, 11):
                text = pytesseract.image_to_string(
                    band,
                    lang=self.OCR_LANGUAGE,
                    config=f"--oem 3 --psm {psm}",
                    timeout=15,
                )
                for line in text.splitlines():
                    candidate_text = self.clean_name_candidate(line)
                    if self.looks_like_person_name(candidate_text):
                        return candidate_text

        if not candidates:
            return None

        candidate = min(
            candidates,
            key=lambda block: block.bounding_box.y0,
        )

        # Use a light, field-specific preprocessing pass.  The full-page
        # deskew/denoise pipeline can erase the small visual distinction
        # between letters in a proper name (for example K/C/Y).
        scale = dpi / 72 if dpi else 1.0
        padding_x = int(16 * scale)
        padding_y = int((20 if dpi is None else 8) * scale)
        width, height = name_image.size

        x0 = max(
            0,
            int(candidate.bounding_box.x0 * scale) - padding_x,
        )
        y0 = max(
            0,
            int(candidate.bounding_box.y0 * scale) - padding_y,
        )
        # Preliminary OCR may clip the left edge or underestimate the
        # width of a large name.  Include the upper-left header region,
        # while keeping the vertical crop limited to the name line.
        x1 = min(width, max(
            int(candidate.bounding_box.x1 * scale) + padding_x,
            int(width * 0.60),
        ))
        y1 = min(
            height,
            int(candidate.bounding_box.y1 * scale) + padding_y,
        )

        crop = name_image.crop((x0, y0, x1, y1))
        name_scale = 4 if dpi is None else 3
        crop = crop.resize(
            (crop.width * name_scale, crop.height * name_scale),
            Image.Resampling.LANCZOS,
        )

        candidates: list[str] = []

        psms = (7, 8, 13) if dpi is None else (8, 13)
        for psm in psms:
            text = pytesseract.image_to_string(
                crop,
                lang=self.OCR_LANGUAGE,
                config=f"--oem 3 --psm {psm}",
                timeout=15,
            )
            text = self.clean_name_candidate(text)

            if self.looks_like_person_name(text):
                candidates.append(text)

        if not candidates:
            return None

        # Prefer the candidate repeated by both segmentation modes.
        counts = {candidate: candidates.count(candidate) for candidate in candidates}
        return max(
            candidates,
            key=lambda candidate: (
                counts[candidate],
                len(candidate),
            ),
        )

    def replace_header_name(
        self,
        blocks: list[TextBlock],
        name: str,
        body_top: float | None,
    ) -> list[TextBlock]:
        header_candidates = [
            block
            for block in blocks
            if block.column in {"header", "preliminary"}
            and (body_top is None or block.bounding_box.y0 < body_top)
            and 1 <= len(block.text.split()) <= 5
        ]

        if not header_candidates:
            return blocks

        existing_name = [
            block
            for block in header_candidates
            if self.looks_like_person_name(block.text)
            and not self.looks_like_section_heading(block.text)
        ]

        if existing_name:
            target = min(
                existing_name,
                key=lambda block: block.bounding_box.y0,
            )
            replacement = target.model_copy(
                update={
                    "text": name,
                    "confidence": max(target.confidence, 95.0),
                }
            )

            return [
                replacement if block is target else block
                for block in blocks
            ]

        # The header crop can be dominated by a sidebar heading. Preserve
        # those blocks and insert a new, high-confidence name block instead
        # of overwriting contact information.
        template = min(
            header_candidates,
            key=lambda block: block.bounding_box.y0,
        )
        replacement = template.model_copy(
            update={
                "text": name,
                "confidence": 100.0,
                "bounding_box": Rectangle(
                    x0=0.0,
                    y0=0.0,
                    x1=max(template.bounding_box.x1, 100.0),
                    y1=max(template.bounding_box.y1, 20.0),
                ),
            }
        )

        return [replacement, *blocks]

    @staticmethod
    def clean_name_candidate(text: str) -> str:
        text = re.sub(r"[\r\n|]+", " ", text)
        text = re.split(
            r"(?i)\b(?:personal\s+info|email|phone|mobile|address|linkedin|twitter|website|websile|webste)\b",
            text,
            maxsplit=1,
        )[0]
        text = re.sub(r"[^A-Za-z .'-]", "", text)
        text = re.sub(r"\s+[a-z]\s*$", "", text)
        return re.sub(r"\s+", " ", text).strip(" .'-")

    @staticmethod
    def looks_like_person_name(text: str) -> bool:
        words = text.split()
        if words and len(words[-1]) == 1 and words[-1].islower():
            words.pop()
        lowered = text.casefold()
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
            "island",
            "marketing",
            "negotiating",
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
        }
        return (
            2 <= len(words) <= 4
            and all(word[:1].isupper() or word.isupper() for word in words)
            and not any(len(word) == 1 and not word.isupper() for word in words)
            and not any(term in lowered.split() for term in role_terms)
            and all(
                re.fullmatch(r"[A-Za-z][A-Za-z.'-]*", word)
                for word in words
            )
        )

    def ocr_regions(
        self,
        original_image: Image.Image,
        preliminary_blocks: list[TextBlock],
        page_number: int,
        dpi: int | None,
        split_x: float,
        body_top: float,
    ) -> list[TextBlock]:
        """OCR header, left column, and right column independently."""
        # Region OCR needs to preserve thin strokes and bullet glyphs.  The
        # full-page denoise/deskew image is useful for layout detection, but
        # it can turn letters such as M/n or t/f into different characters.
        # Use a lighter grayscale/Otsu pass for the actual text recognition.
        original_array = np.array(original_image.convert("RGB"))
        grayscale = cv2.cvtColor(
            original_array,
            cv2.COLOR_RGB2GRAY,
        )
        light_image = Image.fromarray(
            cv2.threshold(
                grayscale,
                0,
                255,
                cv2.THRESH_BINARY + cv2.THRESH_OTSU,
            )[1]
        )

        width, height = light_image.size
        coordinate_scale = dpi / 72 if dpi else 1.0
        split_pixel = int(split_x * coordinate_scale)
        body_pixel = max(
            0,
            min(int(body_top * coordinate_scale), height),
        )
        gutter_margin = max(
            8,
            int(6 * coordinate_scale),
        )
        left_boundary = max(
            1,
            split_pixel - gutter_margin,
        )
        right_boundary = min(
            width - 1,
            split_pixel + gutter_margin,
        )

        regions = [
            (
                "header",
                (0, 0, width, body_pixel),
                0,
                0,
            ),
            (
                "left",
                (0, body_pixel, left_boundary, height),
                0,
                body_pixel,
            ),
            (
                "right",
                (right_boundary, body_pixel, width, height),
                right_boundary,
                body_pixel,
            ),
        ]

        words: list[WordToken] = []

        for column, crop_box, x_offset, y_offset in regions:
            left, top, right, bottom = crop_box

            if right <= left or bottom <= top:
                continue

            crop = light_image.crop(crop_box)
            words.extend(
                self.run_tesseract_ocr(
                    crop,
                    page_number=page_number,
                    dpi=dpi,
                    psm=4,
                    x_offset=x_offset,
                    y_offset=y_offset,
                    column=column,
                )
            )

        if not words:
            return preliminary_blocks

        return self.group_words_into_lines(words)

    def find_body_top(
        self,
        blocks: list[TextBlock],
    ) -> float | None:
        """Find the first visible section heading below the header."""
        heading_y_values: list[float] = []
        page_right = max(
            (block.bounding_box.x1 for block in blocks),
            default=0.0,
        )

        for block in blocks:
            candidate = self.clean_heading_candidate(block.text)
            heading_prefix = next(
                (
                    heading
                    for heading in self.SECTION_HEADINGS
                    if candidate == heading
                    or candidate.startswith(heading + " ")
                ),
                candidate,
            )

            # A sidebar heading such as "Personal Info" must not define the
            # main content body's top. Prefer headings in the main column.
            if page_right and block.bounding_box.x0 > page_right * 0.65:
                continue

            if len(heading_prefix.split()) > 6:
                continue

            match = process.extractOne(
                heading_prefix,
                self.SECTION_HEADINGS,
                scorer=fuzz.ratio,
            )

            if match and match[1] >= 78:
                heading_y_values.append(
                    block.bounding_box.y0
                )

        return max(0.0, min(heading_y_values) - 2.0) if heading_y_values else None

    @staticmethod
    def looks_like_section_heading(text: str) -> bool:
        candidate = ContentExtractor.clean_heading_candidate(text)
        return candidate in {
            heading.casefold()
            for heading in ContentExtractor.SECTION_HEADINGS
        }

    @staticmethod
    def clean_heading_candidate(text: str) -> str:
        """Normalize numbered and decorated headings for layout detection."""
        candidate = ContentExtractor.clean_text(text).casefold()
        candidate = re.sub(r"^\s*\d+\s*", "", candidate)
        candidate = re.sub(r"[^a-z]+", " ", candidate)
        return candidate.strip()

    def find_column_split(
        self,
        words: list[WordToken],
        body_top: float | None,
    ) -> float | None:
        """Find a repeated row-level gap between columns."""
        if not words:
            return None

        body_words = [
            word
            for word in words
            if body_top is None
            or word.bounding_box.y0 >= body_top
        ]

        if len(body_words) < self.MIN_COLUMN_WORDS:
            return None

        whitespace_split = self.find_vertical_whitespace_split(body_words)
        if (
            whitespace_split is not None
            and self.is_column_split_consistent(
                body_words,
                whitespace_split,
            )
        ):
            return whitespace_split

        rows: list[list[WordToken]] = []
        row_tolerance = 12.0

        for word in sorted(
            body_words,
            key=lambda item: (
                item.bounding_box.y0,
                item.bounding_box.x0,
            ),
        ):
            center_y = (
                word.bounding_box.y0
                + word.bounding_box.y1
            ) / 2

            for row in rows:
                row_center_y = sum(
                    (
                        item.bounding_box.y0
                        + item.bounding_box.y1
                    ) / 2
                    for item in row
                ) / len(row)

                if abs(center_y - row_center_y) <= row_tolerance:
                    row.append(word)
                    break
            else:
                rows.append([word])

        gap_centers: list[tuple[float, float]] = []

        for row in rows:
            if len(row) < 2:
                continue

            row.sort(
                key=lambda item: item.bounding_box.x0
            )

            for left, right in zip(row, row[1:]):
                gap = (
                    right.bounding_box.x0
                    - left.bounding_box.x1
                )

                if gap >= self.MIN_COLUMN_GUTTER:
                    gap_centers.append(
                        (
                            (
                                left.bounding_box.x1
                                + right.bounding_box.x0
                            ) / 2,
                            gap,
                        )
                    )

        clusters: list[list[tuple[float, float]]] = []
        cluster_tolerance = 35.0

        for center, width in sorted(gap_centers):
            for cluster in clusters:
                cluster_center = self.weighted_gap_center(cluster)

                if abs(center - cluster_center) <= cluster_tolerance:
                    cluster.append((center, width))
                    break
            else:
                clusters.append([(center, width)])

        if not clusters:
            return None

        valid_clusters = [
            cluster
            for cluster in clusters
            if len(cluster) >= 3
        ]

        # One accidental large word gap is not sufficient evidence.
        if not valid_clusters:
            return None

        center_gap = self.find_center_gap(body_words)

        if center_gap is not None:
            closest = min(
                valid_clusters,
                key=lambda cluster: abs(
                    self.weighted_gap_center(cluster)
                    - center_gap
                ),
            )
            candidate = self.weighted_gap_center(closest)
            return (
                candidate
                if self.is_column_split_consistent(body_words, candidate)
                else None
            )

        best = max(
            valid_clusters,
            key=lambda cluster: (
                len(cluster),
                sum(width for _, width in cluster),
            ),
        )
        candidate = self.weighted_gap_center(best)
        return (
            candidate
            if self.is_column_split_consistent(body_words, candidate)
            else None
        )

    @staticmethod
    def is_column_split_consistent(
        words: list[WordToken],
        split: float,
    ) -> bool:
        """Reject false splits through long single-column text lines."""
        groups: dict[tuple[int | None, int | None, int | None], list[WordToken]] = defaultdict(list)
        for word in words:
            groups[
                (
                    word.block_number,
                    word.paragraph_number,
                    word.line_number,
                )
            ].append(word)

        if len(groups) < 6:
            return True

        crossing_groups = 0
        for group in groups.values():
            has_left = any(word.bounding_box.x1 <= split for word in group)
            has_right = any(word.bounding_box.x0 >= split for word in group)
            if has_left and has_right:
                crossing_groups += 1

        return crossing_groups / len(groups) < 0.25

    def find_vertical_whitespace_split(
        self,
        words: list[WordToken],
    ) -> float | None:
        """Find a persistent blank vertical band between content columns."""
        x_min = min(word.bounding_box.x0 for word in words)
        x_max = max(word.bounding_box.x1 for word in words)
        width = x_max - x_min

        if width <= 0:
            return None

        bin_size = 4.0
        count = int(width / bin_size) + 1
        coverage = [0] * count

        for word in words:
            start = max(
                0,
                int((word.bounding_box.x0 - x_min) / bin_size),
            )
            end = min(
                count - 1,
                int((word.bounding_box.x1 - x_min) / bin_size),
            )
            for index in range(start, end + 1):
                coverage[index] += 1

        candidates: list[tuple[float, float]] = []
        start: int | None = None

        for index, occupied in enumerate(coverage + [1]):
            if occupied == 0 and start is None:
                start = index
                continue

            if occupied != 0 and start is not None:
                end = index - 1
                gap_width = (end - start + 1) * bin_size
                split = x_min + ((start + end) / 2) * bin_size
                left_count = sum(word.bounding_box.x1 < split for word in words)
                right_count = sum(word.bounding_box.x0 > split for word in words)
                ratio = (split - x_min) / width

                if (
                    gap_width >= self.MIN_COLUMN_GUTTER
                    and 0.25 <= ratio <= 0.85
                    and left_count >= 5
                    and right_count >= 5
                ):
                    candidates.append((gap_width, split))
                start = None

        return max(candidates)[1] if candidates else None

    def find_center_gap(
        self,
        words: list[WordToken],
    ) -> float | None:
        centers = sorted(
            (
                word.bounding_box.x0
                + word.bounding_box.x1
            ) / 2
            for word in words
        )

        if len(centers) < self.MIN_COLUMN_WORDS:
            return None

        largest_gap = max(
            (
                right - left,
                (left + right) / 2,
            )
            for left, right in zip(centers, centers[1:])
        )

        gap_width, split = largest_gap
        left_count = sum(center < split for center in centers)
        right_count = len(centers) - left_count

        if (
            gap_width >= 30.0
            and left_count >= 4
            and right_count >= 4
        ):
            return split

        return None

    @staticmethod
    def weighted_gap_center(
        cluster: list[tuple[float, float]],
    ) -> float:
        total_width = sum(width for _, width in cluster)

        if total_width == 0:
            return sum(center for center, _ in cluster) / len(cluster)

        return sum(
            center * width
            for center, width in cluster
        ) / total_width

    def preprocess_image(
        self,
        image: Image.Image,
    ) -> Image.Image:
        image_array = np.array(image.convert("RGB"))
        grayscale = cv2.cvtColor(
            image_array,
            cv2.COLOR_RGB2GRAY,
        )

        deskewed = self.deskew(grayscale)
        # Non-local means is useful on small phone photos but is needlessly
        # expensive on long 300-DPI scans. A small Gaussian pass provides
        # equivalent light denoising for those pages at a fraction of the
        # cost; the final region OCR still uses the original image with Otsu
        # thresholding.
        if max(deskewed.shape) > 5000:
            denoised = cv2.GaussianBlur(deskewed, (3, 3), 0)
        else:
            denoised = cv2.fastNlMeansDenoising(
                deskewed,
                None,
                h=10,
                templateWindowSize=7,
                searchWindowSize=21,
            )

        thresholded = cv2.threshold(
            denoised,
            0,
            255,
            cv2.THRESH_BINARY + cv2.THRESH_OTSU,
        )[1]

        return Image.fromarray(thresholded)

    @staticmethod
    def deskew(image: np.ndarray) -> np.ndarray:
        coordinates = np.column_stack(
            np.where(image < 255)
        )

        if len(coordinates) < 20:
            return image

        angle = cv2.minAreaRect(
            coordinates.astype(np.float32)
        )[-1]

        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle

        height, width = image.shape[:2]
        center = (width // 2, height // 2)
        matrix = cv2.getRotationMatrix2D(
            center,
            angle,
            1.0,
        )

        return cv2.warpAffine(
            image,
            matrix,
            (width, height),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE,
        )

    def run_tesseract_ocr(
        self,
        image: Image.Image,
        page_number: int,
        dpi: int | None = None,
        psm: int = 3,
        x_offset: int = 0,
        y_offset: int = 0,
        column: str | None = None,
    ) -> list[WordToken]:
        """Return every recognized word, including low-confidence words."""
        data = pytesseract.image_to_data(
            image.convert("RGB"),
            lang=self.OCR_LANGUAGE,
            output_type=Output.DICT,
            config=f"--oem 3 --psm {psm}",
            timeout=30,
        )

        scale = 72 / dpi if dpi else 1.0
        words: list[WordToken] = []

        for index, raw_text in enumerate(data["text"]):
            text = self.clean_text(raw_text)

            if not text:
                continue

            try:
                confidence = max(
                    0.0,
                    float(data["conf"][index]),
                )
            except (TypeError, ValueError):
                confidence = 0.0

            x = int(data["left"][index]) + x_offset
            y = int(data["top"][index]) + y_offset
            width = int(data["width"][index])
            height = int(data["height"][index])

            words.append(
                WordToken(
                    text=text,
                    confidence=confidence,
                    bounding_box=Rectangle(
                        x0=x * scale,
                        y0=y * scale,
                        x1=(x + width) * scale,
                        y1=(y + height) * scale,
                    ),
                    page_number=page_number,
                    line_number=self.parse_number(
                        data["line_num"][index]
                    ),
                    block_number=self.parse_number(
                        data["block_num"][index]
                    ),
                    paragraph_number=self.parse_number(
                        data["par_num"][index]
                    ),
                    source=SourceType.OCR,
                    column=column,
                )
            )

        return words

    def group_words_into_lines(
        self,
        words: list[WordToken],
    ) -> list[TextBlock]:
        grouped: dict[
            tuple[int, str | None, int | None, int | None, int | None],
            list[WordToken],
        ] = defaultdict(list)

        for word in words:
            key = (
                word.page_number,
                word.column,
                word.block_number,
                word.paragraph_number,
                word.line_number,
            )
            grouped[key].append(word)

        blocks: list[TextBlock] = []

        for line_words in grouped.values():
            line_words.sort(
                key=lambda word: word.bounding_box.x0
            )

            text = self.clean_text(
                " ".join(word.text for word in line_words)
            )
            confidence = sum(
                word.confidence for word in line_words
            ) / len(line_words)

            blocks.append(
                TextBlock(
                    text=text,
                    confidence=confidence,
                    bounding_box=self.combine_boxes(line_words),
                    page_number=line_words[0].page_number,
                    is_heading=self.looks_like_heading(text),
                    words=line_words,
                    source=SourceType.OCR,
                    column=line_words[0].column,
                )
            )

        return sorted(
            blocks,
            key=lambda block: (
                block.page_number,
                block.bounding_box.y0,
                block.bounding_box.x0,
            ),
        )

    @staticmethod
    def combine_boxes(
        words: list[WordToken],
    ) -> Rectangle:
        return Rectangle(
            x0=min(word.bounding_box.x0 for word in words),
            y0=min(word.bounding_box.y0 for word in words),
            x1=max(word.bounding_box.x1 for word in words),
            y1=max(word.bounding_box.y1 for word in words),
        )

    @staticmethod
    def parse_number(value: str | int) -> int | None:
        try:
            number = int(value)
        except (TypeError, ValueError):
            return None
        return number if number > 0 else None

    @staticmethod
    def clean_text(text: str) -> str:
        text = text.replace("\u200b", "")
        text = text.replace("\ufeff", "")
        text = text.replace("\u00a0", " ")
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def looks_like_heading(
        text: str,
        font_size: float = 0.0,
    ) -> bool:
        alphabetic = [char for char in text if char.isalpha()]

        if not alphabetic or len(text.split()) > 8:
            return False

        uppercase_ratio = sum(
            char.isupper() for char in alphabetic
        ) / len(alphabetic)

        return (
            uppercase_ratio >= 0.70
            or font_size >= 13.0
        )
