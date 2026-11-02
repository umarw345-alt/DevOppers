from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    HTTPException,
    UploadFile,
)

from .auth import get_current_user_id
from .extractor import ContentExtractor
from .jobs import (
    ExtractionJob,
    JobStatus,
    JobStore,
    process_extraction_job,
)
from .normalizer import JSONNormalizer
from .orchestrator import ExtractionOrchestrator
from .repository import ResumeRepository
from .schema import Resume
from .storage import save_temporary_upload


app = FastAPI(
    title="Resume Extraction API",
    version="1.0.0",
)

extractor = ContentExtractor()
normalizer = JSONNormalizer()
orchestrator = ExtractionOrchestrator(
    content_extractor=extractor,
    json_normalizer=normalizer,
)

job_store = JobStore()
resume_repository = ResumeRepository()


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post(
    "/resume/upload",
    response_model=ExtractionJob,
    status_code=202,
    tags=["resume"],
)
async def upload_resume(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user_id: UUID = Depends(get_current_user_id),
) -> ExtractionJob:
    """Validate, temporarily store, and queue a resume upload."""
    if not file.content_type:
        raise HTTPException(
            status_code=400,
            detail="The upload did not include a MIME type",
        )

    file_bytes = await file.read()

    # Validate before creating the asynchronous job.
    orchestrator.validate_upload(
        file_bytes=file_bytes,
        mime_type=file.content_type,
    )

    job_id = uuid4()
    file_path = save_temporary_upload(
        job_id=job_id,
        file_bytes=file_bytes,
        mime_type=file.content_type,
    )

    job = job_store.create(
        ExtractionJob(
            job_id=job_id,
            user_id=user_id,
            status=JobStatus.QUEUED,
        )
    )

    background_tasks.add_task(
        process_extraction_job,
        job_id,
        user_id,
        file_path,
        file.content_type,
        job_store,
        resume_repository,
        orchestrator,
    )

    return job


@app.get(
    "/resume/jobs/{job_id}",
    response_model=ExtractionJob,
    tags=["resume"],
)
def get_extraction_job(
    job_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
) -> ExtractionJob:
    """Return the status and result of an asynchronous extraction job."""
    job = job_store.get(job_id)

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Extraction job not found",
        )

    if job.user_id != user_id:
        raise HTTPException(
            status_code=403,
            detail="You cannot access this extraction job",
        )

    return job


@app.get(
    "/resume",
    response_model=Resume,
    tags=["resume"],
)
def get_resume(
    user_id: UUID = Depends(get_current_user_id),
) -> Resume:
    """Return the user's saved resume JSON."""
    resume = resume_repository.get(user_id)

    if resume is None:
        raise HTTPException(
            status_code=404,
            detail="No saved resume was found",
        )

    return resume


@app.put(
    "/resume",
    response_model=Resume,
    tags=["resume"],
)
def save_resume(
    resume: Resume,
    user_id: UUID = Depends(get_current_user_id),
) -> Resume:
    """Save a reviewed or manually entered resume JSON."""
    return resume_repository.save(
        user_id=user_id,
        resume=resume,
    )
