from __future__ import annotations

from uuid import UUID

from fastapi import Header, HTTPException


def get_current_user_id(
    x_user_id: str | None = Header(default=None),
) -> UUID:
    """Temporary authentication dependency for local development.

    Replace this with JWT/session authentication before production.
    """
    if not x_user_id:
        raise HTTPException(
            status_code=401,
            detail="Authentication is required",
        )

    try:
        return UUID(x_user_id)
    except ValueError as error:
        raise HTTPException(
            status_code=401,
            detail="X-User-ID must contain a valid UUID",
        ) from error
