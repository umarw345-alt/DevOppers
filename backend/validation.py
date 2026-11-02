import pymupdf
from fastapi import HTTPException

# max file size is 10MB, reject larger files
MAX_FILE_SIZE = 10 * 1024 * 1024

# only up to 5 pages allowed for PDFs
MAX_PAGES = 5

# only allow .PDF and .JPEG
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
}

# raise exception to invalid file uploads:
def validate_upload(
    file_bytes: bytes,
    mime_type: str,
) -> None:
    # empty file
    if not file_bytes:
        raise HTTPException(
            status_code = 400,
            detail = "The upload file is empty",
        )

    # file size > 10MB
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code = 413,
            detail = "The uploaded file must be less than 10MB",
        )

    # uploaded file type is not PDF or JPEG
    if mime_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code = 415,
            detail = "Only PDF and JPEG files are supported",
        )

    # check PDF signature, encryption, and page count
    if mime_type == "application/pdf":
        if not file_bytes.startswith(b"%PDF"):
            raise HTTPException(
                status_code = 400,
                detail = "Invalid PDF signature",
            )

        try:
            document = pymupdf.open(
                stream = file_bytes,
                filetype = "pdf",
            )

            try:
                if document.is_encrypted:
                    raise HTTPException(
                        status_code = 422,
                        detail = "Encrypted PDFs are not supported",
                    )

                if document.page_count > MAX_PAGES:
                    raise HTTPException(
                        status_code = 422,
                        detail = "PDF must contain five pages or fewer",
                    )
            finally:
                document.close()

        except HTTPException:
            raise
        except Exception as error:
            raise HTTPException(
                status_code = 400,
                detail = "Could not read the PDF",
            ) from error

    # check JPEG signature
    elif mime_type == "image/jpeg":
        if not file_bytes.startswith(b"\xff\xd8\xff"):
            raise HTTPException(
                status_code=400,
                detail="Invalid JPEG signature",
            )