"""Add device intelligence tables for Epic AI-2

Revision ID: 20251016_095206
Revises: 
Create Date: 2025-10-16 09:52:06

Story AI2.2: Capability Database Schema & Storage
Epic AI-2: Device Intelligence System

Tables Added:
- device_capabilities: Device capability definitions (one per model)
- device_feature_usage: Feature usage tracking (one per device+feature)

Indexes Added:
- idx_capabilities_manufacturer
- idx_capabilities_integration
- idx_feature_usage_device
- idx_feature_usage_configured
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '20251016_095206'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Add device_capabilities and device_feature_usage tables.
    
    Story AI2.2: Capability Database Schema & Storage
    """
    # ========================================================================
    # Create device_capabilities table
    # ========================================================================
    op.create_table(
        'device_capabilities',
        sa.Column('device_model', sa.String(), nullable=False),
        sa.Column('manufacturer', sa.String(), nullable=False),
        sa.Column('integration_type', sa.String(), nullable=False, server_default='zigbee2mqtt'),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('capabilities', sa.JSON(), nullable=False),
        sa.Column('mqtt_exposes', sa.JSON(), nullable=True),
        sa.Column('last_updated', sa.DateTime(), nullable=False),
        sa.Column('source', sa.String(), nullable=False, server_default='zigbee2mqtt_bridge'),
        sa.PrimaryKeyConstraint('device_model', name='pk_device_capabilities')
    )

    # Create indexes for device_capabilities
    op.create_index(
        'idx_capabilities_manufacturer',
        'device_capabilities',
        ['manufacturer'],
        unique=False
    )
    op.create_index(
        'idx_capabilities_integration',
        'device_capabilities',
        ['integration_type'],
        unique=False
    )

    # ========================================================================
    # Create device_feature_usage table
    # ========================================================================
    op.create_table(
        'device_feature_usage',
        sa.Column('device_id', sa.String(), nullable=False),
        sa.Column('feature_name', sa.String(), nullable=False),
        sa.Column('configured', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('discovered_date', sa.DateTime(), nullable=False),
        sa.Column('last_checked', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('device_id', 'feature_name', name='pk_device_feature_usage')
    )

    # Create indexes for device_feature_usage
    op.create_index(
        'idx_feature_usage_device',
        'device_feature_usage',
        ['device_id'],
        unique=False
    )
    op.create_index(
        'idx_feature_usage_configured',
        'device_feature_usage',
        ['configured'],
        unique=False
    )


def downgrade() -> None:
    """
    Remove device intelligence tables.
    
    Allows rollback to Epic AI-1 only if needed.
    Drops Device Intelligence tables while preserving Epic AI-1 tables
    (patterns, suggestions, user_feedback).
    """
    # Drop indexes first (must drop before tables)
    op.drop_index('idx_feature_usage_configured', table_name='device_feature_usage')
    op.drop_index('idx_feature_usage_device', table_name='device_feature_usage')
    op.drop_index('idx_capabilities_integration', table_name='device_capabilities')
    op.drop_index('idx_capabilities_manufacturer', table_name='device_capabilities')

    # Drop tables
    op.drop_table('device_feature_usage')
    op.drop_table('device_capabilities')

