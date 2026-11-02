from __future__ import annotations

from enum import Enum
from pathlib import Path
from threading import Lock
from uuid import UUID

from pydantic import BaseModel

from .extractor import ContentExtractor
from .normalizer import JSONNormalizer
from .orchestrator import ExtractionOrchestrator
from .repository import ResumeRepository
from .schema import Resume
from .storage import delete_temporary_upload
import logging

logger = logging.getLogger(__name__)

class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    AWAITING_REVIEW = "AWAITING_REVIEW"
    FAILED = "FAILED"


class ExtractionJob(BaseModel):
    job_id: UUID
    user_id: UUID
    status: JobStatus
    resume: Resume | None = None
    error: str | None = None


class JobStore:
    """In-memory job store for local development."""

    def __init__(self) -> None:
        self._jobs: dict[UUID, ExtractionJob] = {}
        self._lock = Lock()

    def create(self, job: ExtractionJob) -> ExtractionJob:
        with self._lock:
            self._jobs[job.job_id] = job
        return job

    def get(self, job_id: UUID) -> ExtractionJob | None:
        with self._lock:
            return self._jobs.get(job_id)

    def update(self, job: ExtractionJob) -> ExtractionJob:
        with self._lock:
            self._jobs[job.job_id] = job
        return job


def process_extraction_job(
    job_id: UUID,
    user_id: UUID,
    file_path: Path,
    mime_type: str,
    job_store: JobStore,
    repository: ResumeRepository,
    orchestrator: ExtractionOrchestrator,
) -> None:
    """Process one queued extraction job.

    FastAPI BackgroundTasks is adequate for local development. Use a
    durable worker queue for production deployments.
    """
    job = job_store.get(job_id)

    if job is None:
        return

    job.status = JobStatus.PROCESSING
    job_store.update(job)

    try:
        file_bytes = file_path.read_bytes()

        resume = orchestrator.extract_content(
            file_bytes=file_bytes,
            mime_type=mime_type,
            user_id=user_id,
        )

        repository.save(
            user_id=user_id,
            resume=resume,
        )

        job.resume = resume
        job.status = JobStatus.AWAITING_REVIEW
        job.error = None
        job_store.update(job)
        
    except Exception as error:
        logger.exception(
            "Resume extraction job %s failed",
            job_id,
        )

        job.status = JobStatus.FAILED
        job.error = str(error)
        job_store.update(job)

    finally:
        delete_temporary_upload(file_path)
