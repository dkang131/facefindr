"""drop event_name and photo_video

Revision ID: 4f921aaa1892
Revises: fe8b1051ec7f
Create Date: 2025-12-11 10:55:20.928663

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4f921aaa1892'
down_revision: Union[str, Sequence[str], None] = 'fe8b1051ec7f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_table('photo_video')
    op.drop_table('event_name')


def downgrade() -> None:
    """Downgrade schema."""
    pass
