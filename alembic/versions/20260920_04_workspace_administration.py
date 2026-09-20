"""Allow an unset personal locale for workspace fallback resolution.

Existing values are preserved.  The column becomes nullable so accounts
without a personal preference can inherit the active workspace default.

Revision ID: 20260920_04
Revises: 20260918_03
"""
import sqlalchemy as sa
from alembic import op

revision = "20260920_04"
down_revision = "20260918_03"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "users",
        "preferred_locale",
        existing_type=sa.String(length=10),
        nullable=True,
        existing_server_default="en",
    )


def downgrade():
    op.execute("UPDATE users SET preferred_locale = 'en' WHERE preferred_locale IS NULL")
    op.alter_column(
        "users",
        "preferred_locale",
        existing_type=sa.String(length=10),
        nullable=False,
        existing_server_default="en",
    )
