"""Add pattern-synergy integration (Phases 1-3)

Revision ID: 20251020_pattern_synergy
Revises: 005_entity_aliases
Create Date: 2025-10-20

Phases 1-3: Patterns & Synergies Integration
- Phase 1: Pattern history tracking
- Phase 2: Pattern-synergy cross-validation
- Phase 3: Real-time synergy detection (API only, no schema changes)
"""
import builtins
import contextlib

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = "20251020_pattern_synergy"
down_revision = "005_entity_aliases"
branch_labels = None
depends_on = None


def upgrade():
    """
    Add pattern history tracking and pattern-synergy validation support.

    Phase 1: Pattern history tracking
    - Add history fields to patterns table
    - Create pattern_history table for time-series snapshots

    Phase 2: Pattern-synergy cross-validation
    - Add pattern validation fields to synergy_opportunities table
    """

    # ========================================================================
    # Phase 1: Pattern History Tracking
    # ========================================================================

    # Add history tracking fields to patterns table
    # Note: For existing rows, we set defaults that will be updated on next detection
    # Check if columns exist first to avoid errors
    connection = op.get_bind()

    # Check and add first_seen
    result = connection.execute(text("""
        SELECT COUNT(*) FROM pragma_table_info('patterns')
        WHERE name = 'first_seen'
    """))
    if result.scalar() == 0:
        op.add_column("patterns", sa.Column("first_seen", sa.DateTime(), nullable=True))

    # Check and add last_seen
    result = connection.execute(text("""
        SELECT COUNT(*) FROM pragma_table_info('patterns')
        WHERE name = 'last_seen'
    """))
    if result.scalar() == 0:
        op.add_column("patterns", sa.Column("last_seen", sa.DateTime(), nullable=True))

    # Check and add confidence_history_count
    result = connection.execute(text("""
        SELECT COUNT(*) FROM pragma_table_info('patterns')
        WHERE name = 'confidence_history_count'
    """))
    if result.scalar() == 0:
        op.add_column("patterns", sa.Column("confidence_history_count", sa.Integer(), nullable=True, server_default="1"))

    # Check and add trend_direction
    result = connection.execute(text("""
        SELECT COUNT(*) FROM pragma_table_info('patterns')
        WHERE name = 'trend_direction'
    """))
    if result.scalar() == 0:
        op.add_column("patterns", sa.Column("trend_direction", sa.String(20), nullable=True))

    # Check and add trend_strength
    result = connection.execute(text("""
        SELECT COUNT(*) FROM pragma_table_info('patterns')
        WHERE name = 'trend_strength'
    """))
    if result.scalar() == 0:
        op.add_column("patterns", sa.Column("trend_strength", sa.Float(), nullable=True, server_default="0.0"))

    # Update existing rows to have default values
    # Set first_seen and last_seen to created_at if it exists, otherwise current time
    # Note: SQLite doesn't support ALTER COLUMN, so we'll update NULLs but can't enforce NOT NULL
    # The application code should handle NULL values gracefully
    op.execute(text("""
        UPDATE patterns
        SET first_seen = COALESCE(first_seen, created_at, datetime('now')),
            last_seen = COALESCE(last_seen, created_at, datetime('now')),
            confidence_history_count = COALESCE(confidence_history_count, 1),
            trend_strength = COALESCE(trend_strength, 0.0)
        WHERE first_seen IS NULL OR last_seen IS NULL OR confidence_history_count IS NULL OR trend_strength IS NULL
    """))

    # Create pattern_history table for time-series snapshots
    op.create_table(
        "pattern_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pattern_id", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("occurrences", sa.Integer(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["pattern_id"], ["patterns.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for pattern_history
    op.create_index(
        "idx_pattern_history_pattern",
        "pattern_history",
        ["pattern_id", "recorded_at"],
        unique=False,
    )
    op.create_index(
        "idx_pattern_history_recorded",
        "pattern_history",
        ["recorded_at"],
        unique=False,
    )

    # Create indexes for patterns table (if they don't exist)
    # Note: These might already exist, but Alembic will handle that gracefully
    try:
        op.create_index("idx_patterns_device", "patterns", ["device_id"], unique=False)
    except:
        pass  # Index may already exist

    try:
        op.create_index("idx_patterns_type", "patterns", ["pattern_type"], unique=False)
    except:
        pass  # Index may already exist

    try:
        op.create_index("idx_patterns_confidence", "patterns", ["confidence"], unique=False)
    except:
        pass  # Index may already exist

    # ========================================================================
    # Phase 2: Pattern-Synergy Cross-Validation
    # ========================================================================

    # Add pattern validation fields to synergy_opportunities table
    # Check if columns exist first to avoid errors
    connection = op.get_bind()

    # Check if pattern_support_score exists
    result = connection.execute(text("""
        SELECT COUNT(*) FROM pragma_table_info('synergy_opportunities')
        WHERE name = 'pattern_support_score'
    """))
    if result.scalar() == 0:
        op.add_column("synergy_opportunities", sa.Column("pattern_support_score", sa.Float(), nullable=True, server_default="0.0"))

    # Check if validated_by_patterns exists
    result = connection.execute(text("""
        SELECT COUNT(*) FROM pragma_table_info('synergy_opportunities')
        WHERE name = 'validated_by_patterns'
    """))
    if result.scalar() == 0:
        op.add_column("synergy_opportunities", sa.Column("validated_by_patterns", sa.Boolean(), nullable=True, server_default="0"))  # SQLite uses 0/1

    # Check if supporting_pattern_ids exists
    result = connection.execute(text("""
        SELECT COUNT(*) FROM pragma_table_info('synergy_opportunities')
        WHERE name = 'supporting_pattern_ids'
    """))
    if result.scalar() == 0:
        op.add_column("synergy_opportunities", sa.Column("supporting_pattern_ids", sa.Text(), nullable=True))

    # Update existing rows to have default values
    op.execute(text("""
        UPDATE synergy_opportunities
        SET pattern_support_score = 0.0,
            validated_by_patterns = 0
        WHERE pattern_support_score IS NULL OR validated_by_patterns IS NULL
    """))

    # Make columns NOT NULL after updating existing rows (only if they were just added)
    try:
        op.alter_column("synergy_opportunities", "pattern_support_score", nullable=False)
    except:
        pass  # Column might already be NOT NULL

    try:
        op.alter_column("synergy_opportunities", "validated_by_patterns", nullable=False)
    except:
        pass  # Column might already be NOT NULL

    # Create indexes for synergy pattern validation
    try:
        op.create_index(
            "idx_synergy_validated",
            "synergy_opportunities",
            ["validated_by_patterns"],
            unique=False,
        )
    except:
        pass  # Index may already exist

    try:
        op.create_index(
            "idx_synergy_pattern_support",
            "synergy_opportunities",
            ["pattern_support_score"],
            unique=False,
        )
    except:
        pass  # Index may already exist


def downgrade():
    """
    Remove pattern history tracking and pattern-synergy validation support.
    """

    # Phase 2: Remove pattern validation from synergy_opportunities
    with contextlib.suppress(builtins.BaseException):
        op.drop_index("idx_synergy_pattern_support", table_name="synergy_opportunities")

    with contextlib.suppress(builtins.BaseException):
        op.drop_index("idx_synergy_validated", table_name="synergy_opportunities")

    op.drop_column("synergy_opportunities", "supporting_pattern_ids")
    op.drop_column("synergy_opportunities", "validated_by_patterns")
    op.drop_column("synergy_opportunities", "pattern_support_score")

    # Phase 1: Remove pattern history
    with contextlib.suppress(builtins.BaseException):
        op.drop_index("idx_patterns_confidence", table_name="patterns")

    with contextlib.suppress(builtins.BaseException):
        op.drop_index("idx_patterns_type", table_name="patterns")

    with contextlib.suppress(builtins.BaseException):
        op.drop_index("idx_patterns_device", table_name="patterns")

    with contextlib.suppress(builtins.BaseException):
        op.drop_index("idx_pattern_history_recorded", table_name="pattern_history")

    with contextlib.suppress(builtins.BaseException):
        op.drop_index("idx_pattern_history_pattern", table_name="pattern_history")

    op.drop_table("pattern_history")

    op.drop_column("patterns", "trend_strength")
    op.drop_column("patterns", "trend_direction")
    op.drop_column("patterns", "confidence_history_count")
    op.drop_column("patterns", "last_seen")
    op.drop_column("patterns", "first_seen")
