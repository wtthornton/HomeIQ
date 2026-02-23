"""add config_entry_id and via_device

Revision ID: 005
Revises: 004
Create Date: 2025-01-20

Enhanced Entity Registry: Add config_entry_id to entities and devices, add via_device to devices
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '005'
down_revision: str | None = '004'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add config_entry_id to entities and devices, add via_device to devices"""

    # Add config_entry_id to entities
    op.add_column('entities', sa.Column('config_entry_id', sa.String(), nullable=True))
    op.create_index('idx_entity_config_entry', 'entities', ['config_entry_id'])

    # Add config_entry_id to devices
    op.add_column('devices', sa.Column('config_entry_id', sa.String(), nullable=True))
    op.create_index('idx_device_config_entry', 'devices', ['config_entry_id'])

    # Add via_device to devices (self-referential foreign key)
    op.add_column('devices', sa.Column('via_device', sa.String(), nullable=True))
    op.create_foreign_key(
        'fk_devices_via_device',
        'devices', 'devices',
        ['via_device'], ['device_id']
    )
    op.create_index('idx_device_via_device', 'devices', ['via_device'])


def downgrade() -> None:
    """Remove added columns and indexes"""

    # Remove indexes and columns from devices
    op.drop_index('idx_device_via_device', 'devices')
    op.drop_constraint('fk_devices_via_device', 'devices', type_='foreignkey')
    op.drop_column('devices', 'via_device')
    op.drop_index('idx_device_config_entry', 'devices')
    op.drop_column('devices', 'config_entry_id')

    # Remove indexes and columns from entities
    op.drop_index('idx_entity_config_entry', 'entities')
    op.drop_column('entities', 'config_entry_id')

