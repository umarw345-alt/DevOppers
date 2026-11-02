from __future__ import annotations

import os
from pathlib import Path
from uuid import UUID


TEMP_UPLOAD_DIR = Path(
    os.getenv("RESUME_TEMP_DIR", "temporary_uploads")
)
TEMP_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def save_temporary_upload(
    job_id: UUID,
    file_bytes: bytes,
    mime_type: str,
) -> Path:
    extension = (
        ".pdf"
        if mime_type == "application/pdf"
        else ".jpg"
    )

    path = TEMP_UPLOAD_DIR / f"{job_id}{extension}"
    path.write_bytes(file_bytes)
    return path


def delete_temporary_upload(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        # Cleanup failure should not hide the extraction result.
        pass
