"""add entity name fields and capabilities

Revision ID: 004
Revises: 003
Create Date: 2025-11-17

Epic 2025: Add Entity Registry name fields, capabilities, and services table
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "004"
down_revision: str | None = "003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _schema() -> str:
    """Schema in effect; an unqualified inspector lookup would resolve to public."""
    return op.get_bind().exec_driver_sql("SELECT current_schema()").scalar()


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names(schema=_schema()))


def _columns(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {col["name"] for col in inspector.get_columns(table, schema=_schema())}


def _indexes(table: str) -> set[str]:
    if table not in _tables():
        return set()
    inspector = sa.inspect(op.get_bind())
    return {ix["name"] for ix in inspector.get_indexes(table, schema=_schema()) if ix.get("name")}


# Columns this revision adds to entities, in order.
ENTITY_COLUMNS: tuple[tuple[str, sa.types.TypeEngine], ...] = (
    ("name", sa.String()),
    ("name_by_user", sa.String()),
    ("original_name", sa.String()),
    ("friendly_name", sa.String()),
    ("supported_features", sa.Integer()),
    ("capabilities", sa.JSON()),
    ("available_services", sa.JSON()),
    ("icon", sa.String()),
    ("device_class", sa.String()),
    ("unit_of_measurement", sa.String()),
    ("updated_at", sa.DateTime()),
)

ENTITY_INDEXES: tuple[tuple[str, list[str]], ...] = (
    ("idx_entity_friendly_name", ["friendly_name"]),
    ("idx_entity_supported_features", ["supported_features"]),
    ("idx_entity_device_class", ["device_class"]),
)


def upgrade() -> None:
    """Add entity name fields, capabilities, and create services table"""

    # init-schemas.sql already defines these columns and the services table, so
    # on a normal database this revision is a no-op. Adding them unconditionally
    # raised DuplicateColumn, and on PostgreSQL that aborts the transaction and
    # takes every following statement with it.
    existing_columns = _columns("entities")
    for name, column_type in ENTITY_COLUMNS:
        if name not in existing_columns:
            op.add_column("entities", sa.Column(name, column_type, nullable=True))

    existing_indexes = _indexes("entities")
    for index_name, columns in ENTITY_INDEXES:
        if index_name not in existing_indexes:
            op.create_index(index_name, "entities", columns)

    if "services" not in _tables():
        op.create_table(
            "services",
            sa.Column("domain", sa.String(), nullable=False),
            sa.Column("service_name", sa.String(), nullable=False),
            sa.Column("name", sa.String(), nullable=True),
            sa.Column("description", sa.String(), nullable=True),
            sa.Column("fields", sa.JSON(), nullable=True),
            sa.Column("target", sa.JSON(), nullable=True),
            sa.Column("last_updated", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("domain", "service_name"),
        )
        op.create_index("idx_services_domain", "services", ["domain"])


def downgrade() -> None:
    """Remove added columns and drop services table"""

    # Dropping a table or column takes its indexes with it.
    if "services" in _tables():
        op.drop_table("services")

    existing_columns = _columns("entities")
    for name, _column_type in reversed(ENTITY_COLUMNS):
        if name in existing_columns:
            op.drop_column("entities", name)
