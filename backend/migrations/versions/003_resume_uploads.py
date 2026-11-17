"""count resume uploads for the site-wide daily cap

Revision ID: 003_resume_uploads
Revises: 002_portfolios
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "003_resume_uploads"
down_revision = "002_portfolios"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if "resume_uploads" in inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "resume_uploads",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_resume_uploads_created_at", "resume_uploads", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_resume_uploads_created_at", table_name="resume_uploads")
    op.drop_table("resume_uploads")
