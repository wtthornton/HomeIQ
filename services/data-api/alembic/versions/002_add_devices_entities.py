"""add devices and entities tables

Revision ID: 002
Revises: 001
Create Date: 2025-01-14

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: str | None = '001'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create devices and entities tables"""

    # Create devices table
    op.create_table(
        'devices',
        sa.Column('device_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('manufacturer', sa.String(), nullable=True),
        sa.Column('model', sa.String(), nullable=True),
        sa.Column('sw_version', sa.String(), nullable=True),
        sa.Column('area_id', sa.String(), nullable=True),
        sa.Column('integration', sa.String(), nullable=True),
        sa.Column('last_seen', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('device_id')
    )

    # Create indexes for devices
    op.create_index('idx_device_area', 'devices', ['area_id'])
    op.create_index('idx_device_integration', 'devices', ['integration'])
    op.create_index('idx_device_manufacturer', 'devices', ['manufacturer'])

    # Create entities table
    op.create_table(
        'entities',
        sa.Column('entity_id', sa.String(), nullable=False),
        sa.Column('device_id', sa.String(), nullable=True),
        sa.Column('domain', sa.String(), nullable=False),
        sa.Column('platform', sa.String(), nullable=True),
        sa.Column('unique_id', sa.String(), nullable=True),
        sa.Column('area_id', sa.String(), nullable=True),
        sa.Column('disabled', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['device_id'], ['devices.device_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('entity_id')
    )

    # Create indexes for entities
    op.create_index('idx_entity_device', 'entities', ['device_id'])
    op.create_index('idx_entity_domain', 'entities', ['domain'])
    op.create_index('idx_entity_area', 'entities', ['area_id'])


def downgrade() -> None:
    """Drop devices and entities tables"""

    # Drop indexes first
    op.drop_index('idx_entity_area', table_name='entities')
    op.drop_index('idx_entity_domain', table_name='entities')
    op.drop_index('idx_entity_device', table_name='entities')

    # Drop entities table
    op.drop_table('entities')

    # Drop device indexes
    op.drop_index('idx_device_manufacturer', table_name='devices')
    op.drop_index('idx_device_integration', table_name='devices')
    op.drop_index('idx_device_area', table_name='devices')

    # Drop devices table
    op.drop_table('devices')

