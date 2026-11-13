"""add wallet pass issuance records

Revision ID: 002_wallet_passes
Revises: 001_initial_auth_schema
"""

from alembic import op
import sqlalchemy as sa


revision = "002_wallet_passes"
down_revision = "001_initial_auth_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wallet_passes",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "user_id",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("portfolio_id", sa.UUID(), nullable=False),
        sa.Column("platform", sa.String(length=16), nullable=False),
        sa.Column("provider_object_id", sa.String(length=255), nullable=False),
        sa.Column("artifact_version", sa.String(length=128), nullable=False),
        sa.Column("public_url", sa.Text(), nullable=False),
        sa.Column("qr_value_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="issued"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "platform IN ('apple', 'google')",
            name="ck_wallet_passes_platform",
        ),
        sa.CheckConstraint(
            "status IN ('issued', 'revoked', 'failed')",
            name="ck_wallet_passes_status",
        ),
        sa.UniqueConstraint(
            "platform",
            "provider_object_id",
            name="uq_wallet_passes_platform_provider_object",
        ),
    )
    op.create_index("ix_wallet_passes_user_id", "wallet_passes", ["user_id"])
    op.create_index("ix_wallet_passes_portfolio_id", "wallet_passes", ["portfolio_id"])


def downgrade() -> None:
    op.drop_index("ix_wallet_passes_portfolio_id", table_name="wallet_passes")
    op.drop_index("ix_wallet_passes_user_id", table_name="wallet_passes")
    op.drop_table("wallet_passes")
