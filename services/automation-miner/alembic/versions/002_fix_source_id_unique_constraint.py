"""Fix source_id unique constraint to composite (source, source_id)

Revision ID: 002
Revises: 001
Create Date: 2025-01-20 12:00:00

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # SQLite doesn't support ALTER TABLE for constraints directly
    # Check if constraint already has correct definition
    from alembic import context
    from sqlalchemy import inspect

    bind = context.get_bind()
    inspector = inspect(bind)

    # Check existing constraints
    try:
        constraints = inspector.get_unique_constraints("community_automations")
        has_composite = any(
            c.get("name") == "uq_source_source_id" and
            set(c.get("column_names", [])) == {"source", "source_id"}
            for c in constraints
        )

        if has_composite:
            # Constraint already correct, skip migration
            return
    except Exception:
        # If we can't inspect, proceed with migration
        pass

    # Use batch mode to recreate table with new constraint
    # Note: This will recreate the table, so data will be preserved
    with op.batch_alter_table("community_automations", schema=None) as batch_op:
        # Just create the new constraint - batch mode will handle dropping old one if needed
        batch_op.create_unique_constraint(
            "uq_source_source_id",
            ["source", "source_id"],
        )


def downgrade() -> None:
    # Use batch mode for SQLite
    with op.batch_alter_table("community_automations", schema=None) as batch_op:
        # Drop composite constraint
        batch_op.drop_constraint("uq_source_source_id", type_="unique")

        # Restore old unique constraint on source_id alone
        batch_op.create_unique_constraint(
            "uq_source_source_id",
            ["source_id"],
        )

