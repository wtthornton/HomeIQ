"""add device intelligence fields

Revision ID: 006
Revises: 005
Create Date: 2025-01-20

Phase 1.1: Add device intelligence fields for Device Database enhancements
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '006'
down_revision: str | None = '005'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add device intelligence fields to devices table"""

    # Add device classification fields
    op.add_column('devices', sa.Column('device_type', sa.String(), nullable=True))
    op.add_column('devices', sa.Column('device_category', sa.String(), nullable=True))
    
    # Add power consumption fields
    op.add_column('devices', sa.Column('power_consumption_idle_w', sa.Float(), nullable=True))
    op.add_column('devices', sa.Column('power_consumption_active_w', sa.Float(), nullable=True))
    op.add_column('devices', sa.Column('power_consumption_max_w', sa.Float(), nullable=True))
    
    # Add Device Database fields
    op.add_column('devices', sa.Column('infrared_codes_json', sa.Text(), nullable=True))
    op.add_column('devices', sa.Column('setup_instructions_url', sa.String(), nullable=True))
    op.add_column('devices', sa.Column('troubleshooting_notes', sa.Text(), nullable=True))
    op.add_column('devices', sa.Column('device_features_json', sa.Text(), nullable=True))
    op.add_column('devices', sa.Column('community_rating', sa.Float(), nullable=True))
    op.add_column('devices', sa.Column('last_capability_sync', sa.DateTime(), nullable=True))
    
    # Create indexes for filtering
    op.create_index('idx_device_type', 'devices', ['device_type'])
    op.create_index('idx_device_category', 'devices', ['device_category'])


def downgrade() -> None:
    """Remove device intelligence fields and indexes"""

    # Remove indexes
    op.drop_index('idx_device_category', 'devices')
    op.drop_index('idx_device_type', 'devices')
    
    # Remove columns
    op.drop_column('devices', 'last_capability_sync')
    op.drop_column('devices', 'community_rating')
    op.drop_column('devices', 'device_features_json')
    op.drop_column('devices', 'troubleshooting_notes')
    op.drop_column('devices', 'setup_instructions_url')
    op.drop_column('devices', 'infrared_codes_json')
    op.drop_column('devices', 'power_consumption_max_w')
    op.drop_column('devices', 'power_consumption_active_w')
    op.drop_column('devices', 'power_consumption_idle_w')
    op.drop_column('devices', 'device_category')
    op.drop_column('devices', 'device_type')

