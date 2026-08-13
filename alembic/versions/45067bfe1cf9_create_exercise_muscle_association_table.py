"""create exercise_muscle association table

Revision ID: 45067bfe1cf9
Revises: cbd55cc4
Create Date: 2026-08-12 01:42:08.528828

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '45067bfe1cf9'
down_revision: Union[str, Sequence[str], None] = 'cbd55cc4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the many-to-many table linking exercises to muscles."""
    op.create_table(
        "exercise_muscle",
        sa.Column("exercise_id", sa.Integer(), nullable=False),
        sa.Column("muscle_id", sa.Integer(), nullable=False),
        sa.Column("lengthened_partial", sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(["exercise_id"], ["exercises.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["muscle_id"], ["muscles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("exercise_id", "muscle_id"),
    )


def downgrade() -> None:
    """Drop the exercise_muscle table."""
    op.drop_table("exercise_muscle")
