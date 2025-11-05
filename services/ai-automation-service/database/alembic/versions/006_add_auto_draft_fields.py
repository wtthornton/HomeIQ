"""Add auto-draft generation fields

Revision ID: 006_auto_draft
Revises: 20251020_add_pattern_synergy_integration
Create Date: 2025-11-05 12:00:00.000000

Description:
    Adds fields to track auto-draft YAML generation for suggestions.

    New Fields:
    - yaml_generated_at: Timestamp when YAML was auto-generated
    - yaml_generation_error: Error message if generation failed
    - yaml_generation_method: How YAML was created (auto_draft, on_approval, etc.)

    Indexes:
    - ix_suggestions_yaml_generated_at: For querying auto-drafted suggestions
    - ix_suggestions_status_yaml_generated: Composite index for filtering

Story: Auto-Draft API Generation
"""

from alembic import op
import sqlalchemy as sa

# Revision identifiers
revision = '006_auto_draft'
down_revision = '20251020_add_pattern_synergy_integration'
branch_labels = None
depends_on = None


def upgrade():
    """Add fields to track auto-draft YAML generation"""

    # Add yaml_generated_at timestamp
    op.add_column('suggestions',
        sa.Column('yaml_generated_at', sa.DateTime(), nullable=True,
                  comment='Timestamp when YAML was auto-generated')
    )

    # Add yaml_generation_error for failure tracking
    op.add_column('suggestions',
        sa.Column('yaml_generation_error', sa.Text(), nullable=True,
                  comment='Error message if YAML auto-generation failed')
    )

    # Add yaml_generation_method to track how YAML was created
    # Values: 'auto_draft', 'auto_draft_async', 'on_approval', 'on_approval_regenerated', 'manual'
    op.add_column('suggestions',
        sa.Column('yaml_generation_method', sa.String(50), nullable=True,
                  comment='Method used for YAML generation')
    )

    # Add index for querying auto-drafted suggestions (sorted by generation time)
    op.create_index(
        'ix_suggestions_yaml_generated_at',
        'suggestions',
        ['yaml_generated_at'],
        unique=False
    )

    # Add composite index for status + yaml_generated_at queries
    # Useful for: "Find all deployed suggestions with auto-drafted YAML"
    op.create_index(
        'ix_suggestions_status_yaml_generated',
        'suggestions',
        ['status', 'yaml_generated_at'],
        unique=False
    )


def downgrade():
    """Remove auto-draft fields"""

    # Drop indexes first
    op.drop_index('ix_suggestions_status_yaml_generated', 'suggestions')
    op.drop_index('ix_suggestions_yaml_generated_at', 'suggestions')

    # Drop columns
    op.drop_column('suggestions', 'yaml_generation_method')
    op.drop_column('suggestions', 'yaml_generation_error')
    op.drop_column('suggestions', 'yaml_generated_at')
