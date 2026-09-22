"""Add invitation PINs and forced first-login password changes."""
from alembic import op
import sqlalchemy as sa

revision = "20260922_07"
down_revision = "20260922_06"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("users", sa.Column("must_change_password", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("users", sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("workspace_invitations", sa.Column("verification_mode", sa.String(length=20), nullable=False, server_default="LINK_ONLY"))
    op.add_column("workspace_invitations", sa.Column("pin_digest", sa.String(length=64), nullable=True))
    op.add_column("workspace_invitations", sa.Column("pin_attempt_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("workspace_invitations", sa.Column("pin_verified_at", sa.DateTime(timezone=True), nullable=True))

def downgrade() -> None:
    op.drop_column("workspace_invitations", "pin_verified_at")
    op.drop_column("workspace_invitations", "pin_attempt_count")
    op.drop_column("workspace_invitations", "pin_digest")
    op.drop_column("workspace_invitations", "verification_mode")
    op.drop_column("users", "password_changed_at")
    op.drop_column("users", "must_change_password")
