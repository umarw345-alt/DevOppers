"""baseline: the whole schema as of November 2026

This replaces the earlier migrations (001-005), which came from two parallel
histories. It creates the schema those migrations ended with.

The revision ID is the old head on purpose: databases that already ran the old
migrations are recorded at 005_portfolio_schema_compat, so they skip this file
and only run the migrations after it. New databases run it to create everything.

Revision ID: 005_portfolio_schema_compat
Revises:
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "005_portfolio_schema_compat"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.Text()),  # null for accounts that only sign in with Google
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    op.create_table(
        "sessions",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("refresh_token_hash", sa.Text(), nullable=False),
        sa.Column("token_family_id", sa.UUID(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("used_at", sa.DateTime(timezone=True)),
        sa.Column("last_activity_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("refresh_token_hash", name="uq_sessions_refresh_token_hash"),
    )
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])
    op.create_index("ix_sessions_token_family_id", "sessions", ["token_family_id"])

    op.create_table(
        "external_identities",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("provider_subject", sa.String(255), nullable=False),
        sa.Column("email_at_link_time", sa.String(320)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_external_identities_user_id_users", ondelete="CASCADE"),
        sa.CheckConstraint("provider IN ('google')", name="ck_external_identities_provider"),
        sa.UniqueConstraint("provider", "provider_subject", name="uq_external_identities_provider_subject"),
        sa.UniqueConstraint("user_id", "provider", name="uq_external_identities_user_provider"),
    )
    op.create_index("ix_external_identities_user_id", "external_identities", ["user_id"])

    op.create_table(
        "resumes",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resume_json", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_resumes_user_id", "resumes", ["user_id"])

    # status, artifact_key and artifact_version are unused; the next migration drops them.
    op.create_table(
        "portfolios",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resume_id", sa.UUID(), sa.ForeignKey("resumes.id", ondelete="SET NULL")),
        sa.Column("template_id", sa.String(20), nullable=False),
        sa.Column("theme_json", JSONB()),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("public_slug", sa.String(40)),
        sa.Column("artifact_key", sa.Text()),
        sa.Column("artifact_version", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("public_slug", name="portfolios_public_slug_key"),
    )
    op.create_index("ix_portfolios_user_id", "portfolios", ["user_id"])
    op.create_index("ix_portfolios_resume_id", "portfolios", ["resume_id"])

    # One row per resume sent to Claude, for the site-wide daily cap.
    op.create_table(
        "resume_uploads",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_resume_uploads_created_at", "resume_uploads", ["created_at"])


def downgrade() -> None:
    for table in ("resume_uploads", "portfolios", "resumes", "external_identities", "sessions", "users"):
        op.drop_table(table)
