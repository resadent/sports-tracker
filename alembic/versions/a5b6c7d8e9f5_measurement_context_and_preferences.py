"""Add measurement context, reversible deletion and display preferences.

Existing measurements and settings are left untouched.
"""
from alembic import op
import sqlalchemy as sa

revision = "a5b6c7d8e9f5"
down_revision = "a4b5c6d7e8f4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("measurements", sa.Column("notes", sa.String(1000), nullable=True))
    op.add_column("measurements", sa.Column("waist_readings", sa.JSON(), nullable=True))
    op.add_column("measurements", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("user_settings", sa.Column("weight_unit", sa.String(2), nullable=False, server_default="kg"))
    op.add_column("user_settings", sa.Column("waist_unit", sa.String(2), nullable=False, server_default="cm"))
    op.add_column("user_settings", sa.Column("weight_reminder_days", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("user_settings", sa.Column("waist_reminder_days", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    for column in ("waist_reminder_days", "weight_reminder_days", "waist_unit", "weight_unit"):
        op.drop_column("user_settings", column)
    for column in ("deleted_at", "waist_readings", "notes"):
        op.drop_column("measurements", column)
