"""drop portfolio columns nothing uses

Revision ID: 006_drop_unused_columns
Revises: 005_portfolio_schema_compat
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "006_drop_unused_columns"
down_revision = "005_portfolio_schema_compat"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("portfolios", "status")
    op.drop_column("portfolios", "artifact_key")
    op.drop_column("portfolios", "artifact_version")
    # Databases from the old migration history named this after a temporary table.
    if inspect(op.get_bind()).get_pk_constraint("portfolios")["name"] == "portfolios_new_pkey":
        op.execute("ALTER TABLE portfolios RENAME CONSTRAINT portfolios_new_pkey TO portfolios_pkey")


def downgrade() -> None:
    op.add_column("portfolios", sa.Column("artifact_version", sa.Integer()))
    op.add_column("portfolios", sa.Column("artifact_key", sa.Text()))
    op.add_column("portfolios", sa.Column("status", sa.String(32), nullable=False, server_default="published"))
