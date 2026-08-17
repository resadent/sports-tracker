"""add position and set_type to workout_sets

Revision ID: a2b3c4d5e6f2
Revises: a1b2c3d4e5f1
Create Date: 2026-08-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a2b3c4d5e6f2"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # server_default fills existing rows; it stays in place because SQLite does not
    # support ALTER COLUMN ... DROP DEFAULT.
    op.add_column(
        "workout_sets",
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "workout_sets",
        sa.Column("set_type", sa.String(length=16), nullable=False, server_default="normal"),
    )
    op.create_index(
        "ix_workout_sets_session_position", "workout_sets", ["session_id", "position"]
    )
    op.create_check_constraint(
        "ck_workout_sets_set_type",
        "workout_sets",
        "set_type IN ('normal', 'warmup', 'drop', 'failure')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_workout_sets_set_type", "workout_sets", type_="check")
    op.drop_index("ix_workout_sets_session_position", table_name="workout_sets")
    op.drop_column("workout_sets", "set_type")
    op.drop_column("workout_sets", "position")
