"""Add HA 2025 Entity and Device Registry attributes

Revision ID: 008
Revises: 007
Create Date: 2025-11-15

Phase 1-3: Add missing Home Assistant 2025 API attributes to Entity and Device models
- Entity: aliases, labels, options, icon (current), original_icon
- Device: labels, serial_number, model_id
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add Home Assistant 2025 API attributes to Entity and Device tables.
    
    Phase 1 (Critical):
    - Entity.aliases (JSON array)
    - Entity.icon (current icon, separate from original_icon)
    - Entity.original_icon (original icon from integration)
    
    Phase 2 (Important):
    - Entity.labels (JSON array)
    - Entity.options (JSON object)
    - Device.labels (JSON array)
    
    Phase 3 (Nice to Have):
    - Device.serial_number (optional string)
    - Device.model_id (optional string)
    """
    
    # ============================================================================
    # Entity Table: Phase 1-2 Attributes
    # ============================================================================
    
    # Phase 1: Add aliases (JSON array of alternative names)
    op.add_column('entities', sa.Column('aliases', sa.JSON(), nullable=True))
    
    # Phase 1: Add original_icon (original icon from integration/platform)
    # Note: icon column already exists from migration 004, adding original_icon for clarity
    # Check if original_icon doesn't already exist (safe migration)
    try:
        op.add_column('entities', sa.Column('original_icon', sa.String(), nullable=True))
    except Exception:
        # Column may already exist, skip
        pass
    
    # Phase 2: Add labels (JSON array of label IDs)
    op.add_column('entities', sa.Column('labels', sa.JSON(), nullable=True))
    
    # Phase 2: Add options (JSON object for entity-specific config)
    op.add_column('entities', sa.Column('options', sa.JSON(), nullable=True))
    
    # Phase 1: Add index for name_by_user (for user-customized name lookups)
    op.create_index('idx_entity_name_by_user', 'entities', ['name_by_user'])
    
    # ============================================================================
    # Device Table: Phase 2-3 Attributes
    # ============================================================================
    
    # Phase 2: Add labels (JSON array of label IDs)
    op.add_column('devices', sa.Column('labels', sa.JSON(), nullable=True))
    
    # Phase 3: Add serial_number (optional)
    op.add_column('devices', sa.Column('serial_number', sa.String(), nullable=True))
    
    # Phase 3: Add model_id (optional)
    op.add_column('devices', sa.Column('model_id', sa.String(), nullable=True))


def downgrade():
    """
    Remove Home Assistant 2025 API attributes from Entity and Device tables.
    """
    
    # Remove indexes
    op.drop_index('idx_entity_name_by_user', table_name='entities')
    
    # Remove Entity columns
    op.drop_column('entities', 'options')
    op.drop_column('entities', 'labels')
    op.drop_column('entities', 'original_icon')
    op.drop_column('entities', 'aliases')
    
    # Remove Device columns
    op.drop_column('devices', 'model_id')
    op.drop_column('devices', 'serial_number')
    op.drop_column('devices', 'labels')

