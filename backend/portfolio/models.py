"""Database tables for resumes and the portfolios published from them."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class ResumeRecord(Base):
    """A normalized resume owned by an application user."""

    __tablename__ = "resumes"

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    resume_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    portfolios: Mapped[list["Portfolio"]] = relationship(back_populates="resume_record")


class Portfolio(Base):
    """A published portfolio linked to a normalized resume."""

    __tablename__ = "portfolios"

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    resume_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("resumes.id", ondelete="SET NULL"),
        index=True,
    )
    template_id: Mapped[str] = mapped_column(String(20), nullable=False)
    theme_json: Mapped[dict | None] = mapped_column(JSONB)
    # Unused: always "published". Kept until a later migration drops these three columns.
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    public_slug: Mapped[str | None] = mapped_column(String(40), unique=True)
    artifact_key: Mapped[str | None] = mapped_column(Text)
    artifact_version: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resume_record: Mapped[ResumeRecord | None] = relationship(back_populates="portfolios")
