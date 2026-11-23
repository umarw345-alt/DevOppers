"""create portfolios table

Revision ID: 002_portfolios
Revises: 001_initial_auth_schema
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import inspect

revision = "002_portfolios"
down_revision = "001_initial_auth_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if "portfolios" in inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "portfolios",
        sa.Column("slug", sa.String(40), primary_key=True),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resume", JSONB(), nullable=False),
        sa.Column("template_id", sa.String(20), nullable=False),
        sa.Column("theme", JSONB(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_portfolios_user_id", "portfolios", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_portfolios_user_id", table_name="portfolios")
    op.drop_table("portfolios")
