"""Add table-level record display identity.

Revision ID: 20260922_06
Revises: 20260920_05
"""
from alembic import op
import sqlalchemy as sa


revision = "20260922_06"
down_revision = "20260920_05"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("table_definitions", sa.Column("display_field_key", sa.String(length=120), nullable=True))


def downgrade() -> None:
    op.drop_column("table_definitions", "display_field_key")
