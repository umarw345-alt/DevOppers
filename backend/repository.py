from __future__ import annotations

from threading import Lock
from uuid import UUID

from .schema import Resume


class ResumeRepository:
    """In-memory repository for local development.

    Replace this class with a database-backed repository in production.
    """

    def __init__(self) -> None:
        self._resumes: dict[UUID, Resume] = {}
        self._lock = Lock()

    def get(self, user_id: UUID) -> Resume | None:
        with self._lock:
            return self._resumes.get(user_id)

    def save(
        self,
        user_id: UUID,
        resume: Resume,
    ) -> Resume:
        with self._lock:
            self._resumes[user_id] = resume
        return resume
