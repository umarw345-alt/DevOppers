"""converge database histories and add external identity links

Revision ID: 004_external_identities
Revises: 003_resume_uploads, 003_resume_portfolio_compat
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "004_external_identities"
down_revision = ("003_resume_uploads", "003_resume_portfolio_compat")
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(inspect(bind).get_table_names())

    if "resume_uploads" not in tables:
        op.create_table(
            "resume_uploads",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.UUID(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(
                ["user_id"],
                ["users.id"],
                name="fk_resume_uploads_user_id_users",
                ondelete="CASCADE",
            ),
        )
        op.create_index("ix_resume_uploads_created_at", "resume_uploads", ["created_at"])

    op.alter_column(
        "users",
        "password_hash",
        existing_type=sa.Text(),
        nullable=True,
    )
    if "external_identities" not in tables:
        op.create_table(
            "external_identities",
            sa.Column("id", sa.UUID(), primary_key=True),
            sa.Column("user_id", sa.UUID(), nullable=False),
            sa.Column("provider", sa.String(32), nullable=False),
            sa.Column("provider_subject", sa.String(255), nullable=False),
            sa.Column("email_at_link_time", sa.String(320)),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(
                ["user_id"],
                ["users.id"],
                name="fk_external_identities_user_id_users",
                ondelete="CASCADE",
            ),
            sa.CheckConstraint(
                "provider IN ('google')",
                name="ck_external_identities_provider",
            ),
            sa.UniqueConstraint(
                "provider",
                "provider_subject",
                name="uq_external_identities_provider_subject",
            ),
            sa.UniqueConstraint(
                "user_id",
                "provider",
                name="uq_external_identities_user_provider",
            ),
        )
        op.create_index(
            "ix_external_identities_user_id",
            "external_identities",
            ["user_id"],
        )


def downgrade() -> None:
    op.drop_index("ix_external_identities_user_id", table_name="external_identities")
    op.drop_table("external_identities")
    op.alter_column(
        "users",
        "password_hash",
        existing_type=sa.Text(),
        nullable=False,
    )
