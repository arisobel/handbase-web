"""Initial metadata engine.

Revision ID: 20260918_01
Revises:
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260918_01"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "workspaces",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("default_locale", sa.String(10), nullable=False, server_default="en"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "table_definitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(120), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("icon", sa.String(50)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("workspace_id", "slug", name="uq_table_workspace_slug"),
    )
    op.create_index("ix_table_definitions_workspace_id", "table_definitions", ["workspace_id"])
    op.create_table(
        "field_definitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("table_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("table_definitions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("key", sa.String(120), nullable=False),
        sa.Column("label", sa.String(200), nullable=False),
        sa.Column("field_type", sa.String(50), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("config", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.UniqueConstraint("table_id", "key", name="uq_field_table_key"),
    )
    op.create_index("ix_field_definitions_table_id", "field_definitions", ["table_id"])
    op.create_table(
        "records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("table_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("table_definitions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("data", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True)),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_records_table_id", "records", ["table_id"])
    op.create_index("ix_records_data_gin", "records", ["data"], postgresql_using="gin")
    op.create_table(
        "view_definitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("table_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("table_definitions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("view_type", sa.String(30), nullable=False, server_default="grid"),
        sa.Column("definition", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("is_shared", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_view_definitions_table_id", "view_definitions", ["table_id"])

def downgrade():
    op.drop_table("view_definitions")
    op.drop_table("records")
    op.drop_table("field_definitions")
    op.drop_table("table_definitions")
    op.drop_table("workspaces")
