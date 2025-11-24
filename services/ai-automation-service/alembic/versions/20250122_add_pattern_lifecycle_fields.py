"""Add pattern lifecycle management fields

Revision ID: 20250122_pattern_lifecycle
Revises: 20251121_qa_learning
Create Date: 2025-01-22

Adds lifecycle management fields to patterns table:
- deprecated: Boolean flag for stale patterns
- deprecated_at: Timestamp when pattern was deprecated
- needs_review: Boolean flag for patterns needing manual review
"""

import logging
import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision = '20250122_pattern_lifecycle'
down_revision = '20251121_qa_learning'  # Follows after qa_learning migration
branch_labels = None
depends_on = None


def upgrade():
    """
    Add pattern lifecycle management fields.
    """
    connection = op.get_bind()
    
    # Check and add deprecated field
    result = connection.execute(text("""
        SELECT COUNT(*) FROM pragma_table_info('patterns') 
        WHERE name = 'deprecated'
    """))
    if result.scalar() == 0:
        op.add_column('patterns', sa.Column('deprecated', sa.Boolean(), nullable=False, server_default='0'))
        logger.info("Added 'deprecated' column to patterns table")
    
    # Check and add deprecated_at field
    result = connection.execute(text("""
        SELECT COUNT(*) FROM pragma_table_info('patterns') 
        WHERE name = 'deprecated_at'
    """))
    if result.scalar() == 0:
        op.add_column('patterns', sa.Column('deprecated_at', sa.DateTime(), nullable=True))
        logger.info("Added 'deprecated_at' column to patterns table")
    
    # Check and add needs_review field
    result = connection.execute(text("""
        SELECT COUNT(*) FROM pragma_table_info('patterns') 
        WHERE name = 'needs_review'
    """))
    if result.scalar() == 0:
        op.add_column('patterns', sa.Column('needs_review', sa.Boolean(), nullable=False, server_default='0'))
        logger.info("Added 'needs_review' column to patterns table")
    
    # Create index on deprecated for faster queries
    try:
        op.create_index('idx_patterns_deprecated', 'patterns', ['deprecated'])
        logger.info("Created index on patterns.deprecated")
    except Exception:
        # Index might already exist
        pass
    
    # Create index on needs_review for faster queries
    try:
        op.create_index('idx_patterns_needs_review', 'patterns', ['needs_review'])
        logger.info("Created index on patterns.needs_review")
    except Exception:
        # Index might already exist
        pass


def downgrade():
    """
    Remove pattern lifecycle management fields.
    """
    # Drop indexes
    try:
        op.drop_index('idx_patterns_needs_review', table_name='patterns')
    except Exception:
        pass
    
    try:
        op.drop_index('idx_patterns_deprecated', table_name='patterns')
    except Exception:
        pass
    
    # Drop columns
    try:
        op.drop_column('patterns', 'needs_review')
    except Exception:
        pass
    
    try:
        op.drop_column('patterns', 'deprecated_at')
    except Exception:
        pass
    
    try:
        op.drop_column('patterns', 'deprecated')
    except Exception:
        pass

