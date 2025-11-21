"""Add auto-draft generation and expert mode fields

Revision ID: 006_auto_draft_expert_mode
Revises: 20251020_add_pattern_synergy_integration
Create Date: 2025-11-05 12:00:00.000000

Description:
    Adds fields to track auto-draft YAML generation and expert mode for suggestions.

    Auto-Draft Fields:
    - yaml_generated_at: Timestamp when YAML was auto-generated
    - yaml_generation_error: Error message if generation failed
    - yaml_generation_method: How YAML was created (auto_draft, on_approval, etc.)

    Expert Mode Fields:
    - mode: Suggestion mode ('auto_draft' or 'expert')
    - yaml_edited_at: Timestamp when YAML was manually edited
    - yaml_edit_count: Number of manual YAML edits made

    Indexes:
    - ix_suggestions_yaml_generated_at: For querying auto-drafted suggestions
    - ix_suggestions_status_yaml_generated: Composite index for filtering
    - ix_suggestions_mode: For filtering by mode
    - ix_suggestions_yaml_edited_at: For querying manually edited suggestions

Story: Auto-Draft API Generation + Expert Mode
"""

import sqlalchemy as sa
from alembic import op

# Revision identifiers
revision = "006_auto_draft_expert_mode"
down_revision = "20251020_add_pattern_synergy_integration"
branch_labels = None
depends_on = None


def upgrade():
    """Add fields to track auto-draft YAML generation and expert mode"""

    # ========================================================================
    # Auto-Draft Fields
    # ========================================================================

    # Add yaml_generated_at timestamp
    op.add_column("suggestions",
        sa.Column("yaml_generated_at", sa.DateTime(), nullable=True,
                  comment="Timestamp when YAML was auto-generated"),
    )

    # Add yaml_generation_error for failure tracking
    op.add_column("suggestions",
        sa.Column("yaml_generation_error", sa.Text(), nullable=True,
                  comment="Error message if YAML auto-generation failed"),
    )

    # Add yaml_generation_method to track how YAML was created
    # Values: 'auto_draft', 'auto_draft_async', 'on_approval', 'on_approval_regenerated',
    #         'expert_manual', 'expert_manual_edited'
    op.add_column("suggestions",
        sa.Column("yaml_generation_method", sa.String(50), nullable=True,
                  comment="Method used for YAML generation"),
    )

    # ========================================================================
    # Expert Mode Fields
    # ========================================================================

    # Add mode field to track suggestion mode
    # Values: 'auto_draft' (default), 'expert'
    op.add_column("suggestions",
        sa.Column("mode", sa.String(20), nullable=True, server_default="auto_draft",
                  comment="Suggestion mode: auto_draft or expert"),
    )

    # Add yaml_edited_at timestamp for manual edits
    op.add_column("suggestions",
        sa.Column("yaml_edited_at", sa.DateTime(), nullable=True,
                  comment="Timestamp when YAML was manually edited in expert mode"),
    )

    # Add yaml_edit_count to track number of manual edits
    op.add_column("suggestions",
        sa.Column("yaml_edit_count", sa.Integer(), nullable=True, server_default="0",
                  comment="Number of manual YAML edits made in expert mode"),
    )

    # ========================================================================
    # Indexes
    # ========================================================================

    # Auto-draft indexes
    op.create_index(
        "ix_suggestions_yaml_generated_at",
        "suggestions",
        ["yaml_generated_at"],
        unique=False,
    )

    op.create_index(
        "ix_suggestions_status_yaml_generated",
        "suggestions",
        ["status", "yaml_generated_at"],
        unique=False,
    )

    # Expert mode indexes
    op.create_index(
        "ix_suggestions_mode",
        "suggestions",
        ["mode"],
        unique=False,
    )

    op.create_index(
        "ix_suggestions_yaml_edited_at",
        "suggestions",
        ["yaml_edited_at"],
        unique=False,
    )


def downgrade():
    """Remove auto-draft and expert mode fields"""

    # Drop indexes first
    op.drop_index("ix_suggestions_yaml_edited_at", "suggestions")
    op.drop_index("ix_suggestions_mode", "suggestions")
    op.drop_index("ix_suggestions_status_yaml_generated", "suggestions")
    op.drop_index("ix_suggestions_yaml_generated_at", "suggestions")

    # Drop expert mode columns
    op.drop_column("suggestions", "yaml_edit_count")
    op.drop_column("suggestions", "yaml_edited_at")
    op.drop_column("suggestions", "mode")

    # Drop auto-draft columns
    op.drop_column("suggestions", "yaml_generation_method")
    op.drop_column("suggestions", "yaml_generation_error")
    op.drop_column("suggestions", "yaml_generated_at")
