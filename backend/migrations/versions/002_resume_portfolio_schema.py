"""recognize the existing normalized resume and portfolio schema

This marker revision represents the schema already present in the shared
PostgreSQL database. It is intentionally a no-op: the tables were created by
the earlier combined-backend migration and must not be recreated.

Revision ID: 002_resume_portfolio_schema
Revises: 001_initial_auth_schema
"""

revision = "002_resume_portfolio_schema"
down_revision = "001_initial_auth_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
