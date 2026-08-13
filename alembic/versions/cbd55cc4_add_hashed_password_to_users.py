from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "cbd55cc4"
down_revision = "33e61260c370"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # server_default fills existing rows; it stays in place because SQLite does not
    # support ALTER COLUMN ... DROP DEFAULT (the app always sets the password anyway).
    op.add_column(
        "users",
        sa.Column("hashed_password", sa.String(length=255), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("users", "hashed_password")
