"""compatibility branch for the existing normalized schema

Revision ID: 003_resume_portfolio_compat
Revises: 002_resume_portfolio_schema
"""

revision = "003_resume_portfolio_compat"
down_revision = "002_resume_portfolio_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The old combined-backend database already has resumes and portfolios.
    # The shared head migration will add resume_uploads if this table is absent.
    pass


def downgrade() -> None:
    pass
