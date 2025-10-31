"""add missing device columns

Revision ID: 003
Revises: 002
Create Date: 2025-10-31

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add missing columns to devices table"""
    
    # Add missing columns to devices table
    op.add_column('devices', sa.Column('name_by_user', sa.String(), nullable=True))
    op.add_column('devices', sa.Column('entry_type', sa.String(), nullable=True))
    op.add_column('devices', sa.Column('configuration_url', sa.String(), nullable=True))
    op.add_column('devices', sa.Column('suggested_area', sa.String(), nullable=True))


def downgrade() -> None:
    """Remove added columns from devices table"""
    
    # Remove columns in reverse order
    op.drop_column('devices', 'suggested_area')
    op.drop_column('devices', 'configuration_url')
    op.drop_column('devices', 'entry_type')
    op.drop_column('devices', 'name_by_user')

