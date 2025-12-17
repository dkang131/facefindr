"""Initial complete schema with admin_id column

Revision ID: initial_complete
Revises: 
Create Date: 2025-12-17 17:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'initial_complete'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create admin table
    op.create_table('admin',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('email', sa.String(), nullable=True),
        sa.Column('password', sa.String(), nullable=True),
        sa.Column('role', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_admin_email'), 'admin', ['email'], unique=True)
    op.create_index(op.f('ix_admin_id'), 'admin', ['id'], unique=False)

    # Create event_names table with admin_id column
    op.create_table('event_names',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('event_name', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('admin_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['admin_id'], ['admin.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_event_names_event_name'), 'event_names', ['event_name'], unique=False)
    op.create_index(op.f('ix_event_names_id'), 'event_names', ['id'], unique=False)

    # Create photo_videos table
    op.create_table('photo_videos',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=True),
        sa.Column('file_path', sa.String(), nullable=True),
        sa.Column('is_processed', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['event_id'], ['event_names.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_photo_videos_id'), 'photo_videos', ['id'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index(op.f('ix_photo_videos_id'), table_name='photo_videos')
    op.drop_table('photo_videos')
    
    op.drop_index(op.f('ix_event_names_id'), table_name='event_names')
    op.drop_index(op.f('ix_event_names_event_name'), table_name='event_names')
    op.drop_table('event_names')
    
    op.drop_index(op.f('ix_admin_id'), table_name='admin')
    op.drop_index(op.f('ix_admin_email'), table_name='admin')
    op.drop_table('admin')