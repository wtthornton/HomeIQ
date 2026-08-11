"""add statistics_meta table

Revision ID: 007
Revises: 006
Create Date: 2025-11-28

Epic 45.1: Add statistics_meta table for tracking entities eligible for statistics aggregation
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "007"
down_revision: str | None = "006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _schema() -> str:
    """Schema in effect; an unqualified inspector lookup would resolve to public."""
    return op.get_bind().exec_driver_sql("SELECT current_schema()").scalar()


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names(schema=_schema()))


def _indexes(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if table not in _tables():
        return set()
    return {ix["name"] for ix in inspector.get_indexes(table, schema=_schema()) if ix.get("name")}


def upgrade() -> None:
    """Create statistics_meta table (idempotent - 2025 pattern)"""

    # infrastructure/postgres/init-schemas.sql owns statistics_meta, so this is
    # normally a no-op. It used to be written as try/except with a substring
    # match on "already exists", which both hides real errors and depends on the
    # backend's wording.
    if "statistics_meta" not in _tables():
        op.create_table(
            "statistics_meta",
            sa.Column("statistic_id", sa.String(), nullable=False),  # entity_id (primary key)
            sa.Column("source", sa.String(), nullable=False, server_default="state"),
            sa.Column("unit_of_measurement", sa.String(), nullable=True),
            sa.Column("state_class", sa.String(), nullable=True),
            sa.Column("has_mean", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("has_sum", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("last_reset", sa.DateTime(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.current_timestamp(),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.current_timestamp(),
            ),
            sa.PrimaryKeyConstraint("statistic_id"),
        )
    existing_indexes = _indexes("statistics_meta")
    for index_name, columns in [
        ("idx_statistics_meta_state_class", ["state_class"]),
        ("idx_statistics_meta_has_mean", ["has_mean"]),
        ("idx_statistics_meta_has_sum", ["has_sum"]),
    ]:
        if index_name not in existing_indexes:
            op.create_index(index_name, "statistics_meta", columns)


def downgrade() -> None:
    """Remove statistics_meta table and indexes"""

    op.drop_index("idx_statistics_meta_has_sum", "statistics_meta")
    op.drop_index("idx_statistics_meta_has_mean", "statistics_meta")
    op.drop_index("idx_statistics_meta_state_class", "statistics_meta")
    op.drop_table("statistics_meta")
