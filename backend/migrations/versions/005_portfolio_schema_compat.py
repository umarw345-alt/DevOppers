"""normalize legacy inline portfolios without losing their contents

Revision ID: 005_portfolio_schema_compat
Revises: 004_external_identities
"""
from uuid import uuid4

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import JSONB


revision = "005_portfolio_schema_compat"
down_revision = "004_external_identities"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())
    if "portfolios" not in tables:
        return

    portfolio_columns = {column["name"] for column in inspector.get_columns("portfolios")}
    if "id" in portfolio_columns and "resume_id" in portfolio_columns:
        return
    if not {"slug", "resume", "theme"}.issubset(portfolio_columns):
        raise RuntimeError("Unsupported portfolios schema; refusing an unsafe compatibility migration")

    if "resumes" not in tables:
        op.create_table(
            "resumes",
            sa.Column("id", sa.UUID(), primary_key=True),
            sa.Column("user_id", sa.UUID(), nullable=False),
            sa.Column("resume_json", JSONB(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(
                ["user_id"],
                ["users.id"],
                name="resumes_user_id_fkey",
                ondelete="CASCADE",
            ),
        )
        op.create_index("ix_resumes_user_id", "resumes", ["user_id"])

    op.create_table(
        "portfolios_new",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("resume_id", sa.UUID()),
        sa.Column("template_id", sa.String(20), nullable=False),
        sa.Column("theme_json", JSONB()),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("public_slug", sa.String(40)),
        sa.Column("artifact_key", sa.Text()),
        sa.Column("artifact_version", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="portfolios_user_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["resume_id"],
            ["resumes.id"],
            name="portfolios_resume_id_fkey",
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint("public_slug", name="portfolios_public_slug_key"),
    )

    legacy_rows = bind.execute(
        sa.text("SELECT slug, user_id, resume, template_id, theme, updated_at FROM portfolios")
    ).mappings()
    for row in legacy_rows:
        resume_id = uuid4()
        portfolio_id = uuid4()
        bind.execute(
            sa.text(
                "INSERT INTO resumes (id, user_id, resume_json, created_at, updated_at) "
                "VALUES (:id, :user_id, :resume_json, :created_at, :updated_at)"
            ),
            {
                "id": resume_id,
                "user_id": row["user_id"],
                "resume_json": row["resume"],
                "created_at": row["updated_at"],
                "updated_at": row["updated_at"],
            },
        )
        bind.execute(
            sa.text(
                "INSERT INTO portfolios_new "
                "(id, user_id, resume_id, template_id, theme_json, status, public_slug, created_at, updated_at) "
                "VALUES (:id, :user_id, :resume_id, :template_id, :theme_json, 'published', :public_slug, :created_at, :updated_at)"
            ),
            {
                "id": portfolio_id,
                "user_id": row["user_id"],
                "resume_id": resume_id,
                "template_id": row["template_id"],
                "theme_json": row["theme"],
                "public_slug": row["slug"],
                "created_at": row["updated_at"],
                "updated_at": row["updated_at"],
            },
        )

    existing_indexes = {index["name"] for index in inspector.get_indexes("portfolios")}
    if "ix_portfolios_user_id" in existing_indexes:
        op.drop_index("ix_portfolios_user_id", table_name="portfolios")
    op.drop_table("portfolios")
    op.rename_table("portfolios_new", "portfolios")
    op.create_index("ix_portfolios_user_id", "portfolios", ["user_id"])
    op.create_index("ix_portfolios_resume_id", "portfolios", ["resume_id"])


def downgrade() -> None:
    raise RuntimeError(
        "Downgrading portfolio_schema_compat is intentionally blocked because it would discard normalized resume and artifact metadata."
    )
