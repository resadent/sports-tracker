"""empty message

Revision ID: 8c0d6ceb3a86
Revises: 0001_create_users
Create Date: 2026-05-21 18:03:25.857453

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8c0d6ceb3a86'
down_revision: Union[str, Sequence[str], None] = '0001_create_users'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
