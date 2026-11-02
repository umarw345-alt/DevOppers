from __future__ import annotations

from uuid import UUID

import pymupdf
from fastapi import HTTPException

from .extractor import ContentExtractor
from .normalizer import JSONNormalizer
from .schema import Resume


MAX_FILE_SIZE = 10 * 1024 * 1024
MAX_PAGES = 5

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
}


class ExtractionOrchestrator:
    """Coordinate validation, extraction, and normalization."""

    def __init__(
        self,
        content_extractor: ContentExtractor | None = None,
        json_normalizer: JSONNormalizer | None = None,
    ):
        self.content_extractor = (
            content_extractor or ContentExtractor()
        )
        self.json_normalizer = (
            json_normalizer or JSONNormalizer()
        )

    def extract_content(
        self,
        file_bytes: bytes,
        mime_type: str,
        user_id: UUID,
    ) -> Resume:
        """
        Execute the complete synchronous portion of a job.

        The web endpoint should call this method from a background
        worker and return a job ID to the client immediately.
        """
        self.validate_upload(
            file_bytes=file_bytes,
            mime_type=mime_type,
        )

        blocks = self.content_extractor.extract(
            file_bytes=file_bytes,
            mime_type=mime_type,
        )

        if not blocks:
            raise ValueError(
                "No readable text was found in the uploaded file"
            )

        resume = self.json_normalizer.normalize_with_retry(
            blocks
        )

        return resume

    @staticmethod
    def validate_upload(
        file_bytes: bytes,
        mime_type: str,
    ) -> None:
        if not file_bytes:
            raise HTTPException(
                status_code=400,
                detail="The uploaded file is empty",
            )

        if len(file_bytes) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail="The uploaded file exceeds 10 MB",
            )

        if mime_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=415,
                detail="Only PDF and JPEG files are supported",
            )

        if mime_type == "application/pdf":
            ExtractionOrchestrator.validate_pdf(file_bytes)
        else:
            ExtractionOrchestrator.validate_jpeg(file_bytes)

    @staticmethod
    def validate_pdf(file_bytes: bytes) -> None:
        if not file_bytes.startswith(b"%PDF"):
            raise HTTPException(
                status_code=400,
                detail="Invalid PDF signature",
            )

        try:
            document = pymupdf.open(
                stream=file_bytes,
                filetype="pdf",
            )

            try:
                if document.is_encrypted:
                    raise HTTPException(
                        status_code=422,
                        detail="Encrypted PDFs are not supported",
                    )

                if document.page_count > MAX_PAGES:
                    raise HTTPException(
                        status_code=422,
                        detail="PDF must contain five pages or fewer",
                    )
            finally:
                document.close()

        except HTTPException:
            raise
        except Exception as error:
            raise HTTPException(
                status_code=400,
                detail="Could not open the PDF",
            ) from error

    @staticmethod
    def validate_jpeg(file_bytes: bytes) -> None:
        if not file_bytes.startswith(b"\xff\xd8\xff"):
            raise HTTPException(
                status_code=400,
                detail="Invalid JPEG signature",
            )
