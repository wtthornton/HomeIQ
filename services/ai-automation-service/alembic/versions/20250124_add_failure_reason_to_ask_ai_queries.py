"""Add failure_reason field to ask_ai_queries table

Revision ID: 20250124_add_failure_reason
Revises: 20250122_pattern_lifecycle
Create Date: 2025-01-24 12:00:00.000000

Description:
    Quick Win 4: Adds failure_reason field to track why queries fail to generate suggestions.
    
    Failure reasons:
    - clarification_needed: Clarification questions were needed
    - entity_mapping_failed: Entity mapping failed completely
    - empty_suggestions: No suggestions generated and no fallback
    - pattern_fallback_used: Pattern-based fallback was used
    - success: Successfully generated suggestions
    - success_with_clarification: Suggestions generated despite clarification needed
    
    Indexes:
    - ix_ask_ai_queries_failure_reason: For analytics queries on failure reasons
"""

import sqlalchemy as sa
from alembic import op

# Revision identifiers
revision = '20250124_add_failure_reason'
down_revision = '20250122_pattern_lifecycle'
branch_labels = None
depends_on = None


def upgrade():
    """Add failure_reason field to ask_ai_queries table"""
    
    # Add failure_reason column
    op.add_column('ask_ai_queries',
        sa.Column('failure_reason', sa.String(50), nullable=True,
                  comment='Quick Win 4: Reason why suggestions failed (clarification_needed, entity_mapping_failed, empty_suggestions, pattern_fallback_used, success, success_with_clarification)')
    )
    
    # Create index for analytics queries
    op.create_index(
        'ix_ask_ai_queries_failure_reason',
        'ask_ai_queries',
        ['failure_reason'],
        unique=False
    )


def downgrade():
    """Remove failure_reason field from ask_ai_queries table"""
    
    # Drop index first
    op.drop_index('ix_ask_ai_queries_failure_reason', 'ask_ai_queries')
    
    # Drop column
    op.drop_column('ask_ai_queries', 'failure_reason')

