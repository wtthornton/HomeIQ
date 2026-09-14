"""add areas table

Revision ID: 012
Revises: 011
Create Date: 2026-09-14

TAP-7584: Areas as first-class rows instead of a SELECT DISTINCT over
entities. Backfills from the distinct area_id values currently on
core.entities so existing data keeps working with the new table.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "012"
down_revision: str | None = "011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _schema() -> str:
    """Schema in effect; an unqualified inspector lookup would resolve to public."""
    return op.get_bind().exec_driver_sql("SELECT current_schema()").scalar()


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names(schema=_schema()))


def upgrade() -> None:
    """Create areas table and backfill from distinct entities.area_id."""

    if "areas" not in _tables():
        op.create_table(
            "areas",
            sa.Column("area_id", sa.String(), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("floor_id", sa.String(), nullable=True),
            sa.Column("floor_name", sa.String(), nullable=True),
            sa.Column("source", sa.String(), nullable=False, server_default="inferred"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=True,
                server_default=sa.func.now(),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=True,
                server_default=sa.func.now(),
            ),
            sa.PrimaryKeyConstraint("area_id"),
        )
        op.create_index("idx_areas_floor_id", "areas", ["floor_id"])

    # Backfill: one row per distinct non-empty area_id already referenced by an
    # entity. Name is title-cased from the id — the same display transform the
    # /api/areas endpoint applied inline before this table existed — and source
    # is "inferred" because it comes from usage, not the HA area registry.
    op.execute(
        """
        INSERT INTO areas (area_id, name, source)
        SELECT DISTINCT
            entities.area_id,
            initcap(replace(entities.area_id, '_', ' ')),
            'inferred'
        FROM entities
        WHERE entities.area_id IS NOT NULL AND entities.area_id != ''
        ON CONFLICT (area_id) DO NOTHING
        """
    )


def downgrade() -> None:
    """Remove areas table."""

    op.drop_index("idx_areas_floor_id", table_name="areas")
    op.drop_table("areas")
