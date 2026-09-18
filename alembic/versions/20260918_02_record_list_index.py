"""Composite index for the record list endpoint.

``GET /api/v1/records?table_id=...`` filters by ``table_id`` and orders by
``created_at``. The single-column ``ix_records_table_id`` is a prefix of the new
composite index, so it is dropped rather than kept alongside it.

Revision ID: 20260918_02
Revises: 20260918_01
"""
from alembic import op

revision = "20260918_02"
down_revision = "20260918_01"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index("ix_records_table_created", "records", ["table_id", "created_at"])
    op.drop_index("ix_records_table_id", table_name="records")


def downgrade():
    op.create_index("ix_records_table_id", "records", ["table_id"])
    op.drop_index("ix_records_table_created", table_name="records")
