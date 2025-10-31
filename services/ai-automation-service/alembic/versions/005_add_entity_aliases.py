"""Add entity_aliases table for user-defined nicknames

Revision ID: 005_entity_aliases
Revises: 20251019_nlevel
Create Date: 2025-10-29 12:00:00.000000

Epic: Entity Resolution Enhancements
Priority 3: User-Defined Aliases
"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = '005_entity_aliases'
down_revision = '20251019_nlevel'  # Previous migration
branch_labels = None
depends_on = None


def upgrade():
    """
    Add entity_aliases table for user-defined nicknames/aliases.
    
    Allows users to create personalized names for entities (e.g., "sleepy light" → light.bedroom_1).
    Supports multi-user alias management with fast indexed lookups.
    """
    
    # Create entity_aliases table
    op.create_table(
        'entity_aliases',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False, primary_key=True),
        sa.Column('entity_id', sa.String(), nullable=False),
        sa.Column('alias', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False, index=True, default='anonymous'),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow),
        sa.UniqueConstraint('alias', 'user_id', name='uq_alias_user'),
        comment='User-defined aliases/nicknames for entities (priority: fast indexed lookups)'
    )
    
    # Create indexes for fast lookups
    op.create_index('idx_alias_lookup', 'entity_aliases', ['alias', 'user_id'])
    op.create_index('ix_entity_aliases_entity_id', 'entity_aliases', ['entity_id'])
    op.create_index('ix_entity_aliases_user_id', 'entity_aliases', ['user_id'])
    
    logger.info("Created entity_aliases table with indexes")


def downgrade():
    """Remove entity_aliases table"""
    op.drop_index('ix_entity_aliases_user_id', table_name='entity_aliases')
    op.drop_index('ix_entity_aliases_entity_id', table_name='entity_aliases')
    op.drop_index('idx_alias_lookup', table_name='entity_aliases')
    op.drop_table('entity_aliases')

