"""Fix memory_type CHECK constraint to match application enums.

Revision ID: 002_fix_memory_type_enum
Revises: 001_create_memory_schema
Create Date: 2026-03-09

The original migration (001) defined memory_type values as:
    fact, preference, pattern, context, correction

But the application's MemoryType enum uses:
    behavioral, preference, boundary, outcome, routine

This migration updates both CHECK constraints to match the application code,
preventing INSERT failures on deployment.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "002_fix_memory_type_enum"
down_revision: str | None = "001_create_memory_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Old values from 001 migration
OLD_VALUES = "'fact', 'preference', 'pattern', 'context', 'correction'"

# New values matching MemoryType enum in models.py
NEW_VALUES = "'behavioral', 'preference', 'boundary', 'outcome', 'routine'"


def upgrade() -> None:
    """Update memory_type CHECK constraints to match application enums."""
    # Drop old constraints
    op.execute(
        "ALTER TABLE memory.memories DROP CONSTRAINT IF EXISTS chk_memory_type"
    )
    op.execute(
        "ALTER TABLE memory.memory_archive "
        "DROP CONSTRAINT IF EXISTS chk_archive_memory_type"
    )

    # Migrate any existing rows with old enum values
    op.execute("""
        UPDATE memory.memories SET memory_type = CASE
            WHEN memory_type = 'fact' THEN 'behavioral'
            WHEN memory_type = 'pattern' THEN 'routine'
            WHEN memory_type = 'context' THEN 'outcome'
            WHEN memory_type = 'correction' THEN 'boundary'
            ELSE memory_type
        END
        WHERE memory_type IN ('fact', 'pattern', 'context', 'correction')
    """)
    op.execute("""
        UPDATE memory.memory_archive SET memory_type = CASE
            WHEN memory_type = 'fact' THEN 'behavioral'
            WHEN memory_type = 'pattern' THEN 'routine'
            WHEN memory_type = 'context' THEN 'outcome'
            WHEN memory_type = 'correction' THEN 'boundary'
            ELSE memory_type
        END
        WHERE memory_type IN ('fact', 'pattern', 'context', 'correction')
    """)

    # Add new constraints with correct enum values
    op.execute(f"""
        ALTER TABLE memory.memories ADD CONSTRAINT chk_memory_type
        CHECK (memory_type IN ({NEW_VALUES}))
    """)
    op.execute(f"""
        ALTER TABLE memory.memory_archive ADD CONSTRAINT chk_archive_memory_type
        CHECK (memory_type IN ({NEW_VALUES}))
    """)


def downgrade() -> None:
    """Revert memory_type CHECK constraints to original values."""
    op.execute(
        "ALTER TABLE memory.memories DROP CONSTRAINT IF EXISTS chk_memory_type"
    )
    op.execute(
        "ALTER TABLE memory.memory_archive "
        "DROP CONSTRAINT IF EXISTS chk_archive_memory_type"
    )

    # Revert data
    op.execute("""
        UPDATE memory.memories SET memory_type = CASE
            WHEN memory_type = 'behavioral' THEN 'fact'
            WHEN memory_type = 'routine' THEN 'pattern'
            WHEN memory_type = 'outcome' THEN 'context'
            WHEN memory_type = 'boundary' THEN 'correction'
            ELSE memory_type
        END
        WHERE memory_type IN ('behavioral', 'routine', 'outcome', 'boundary')
    """)
    op.execute("""
        UPDATE memory.memory_archive SET memory_type = CASE
            WHEN memory_type = 'behavioral' THEN 'fact'
            WHEN memory_type = 'routine' THEN 'pattern'
            WHEN memory_type = 'outcome' THEN 'context'
            WHEN memory_type = 'boundary' THEN 'correction'
            ELSE memory_type
        END
        WHERE memory_type IN ('behavioral', 'routine', 'outcome', 'boundary')
    """)

    op.execute(f"""
        ALTER TABLE memory.memories ADD CONSTRAINT chk_memory_type
        CHECK (memory_type IN ({OLD_VALUES}))
    """)
    op.execute(f"""
        ALTER TABLE memory.memory_archive ADD CONSTRAINT chk_archive_memory_type
        CHECK (memory_type IN ({OLD_VALUES}))
    """)
