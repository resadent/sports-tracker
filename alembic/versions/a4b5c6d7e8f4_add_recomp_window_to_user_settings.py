"""add recomp_window to user_settings

Revision ID: a4b5c6d7e8f4
Revises: a3b4c5d6e7f3
Create Date: 2026-08-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a4b5c6d7e8f4"
down_revision: Union[str, Sequence[str], None] = "a3b4c5d6e7f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user_settings",
        sa.Column("recomp_window", sa.Integer(), nullable=False, server_default="7"),
    )


def downgrade() -> None:
    op.drop_column("user_settings", "recomp_window")
