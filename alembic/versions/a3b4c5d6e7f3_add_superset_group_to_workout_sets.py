"""add superset_group to workout_sets

Revision ID: a3b4c5d6e7f3
Revises: a2b3c4d5e6f2
Create Date: 2026-08-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a3b4c5d6e7f3"
down_revision: Union[str, Sequence[str], None] = "a2b3c4d5e6f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "workout_sets",
        sa.Column("superset_group", sa.String(length=36), nullable=True),
    )
    op.create_index(
        "ix_workout_sets_superset_group", "workout_sets", ["superset_group"]
    )


def downgrade() -> None:
    op.drop_index("ix_workout_sets_superset_group", table_name="workout_sets")
    op.drop_column("workout_sets", "superset_group")
