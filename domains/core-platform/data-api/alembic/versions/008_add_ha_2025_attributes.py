"""Add HA 2025 Entity and Device Registry attributes

Revision ID: 008
Revises: 007
Create Date: 2025-11-15

Phase 1-3: Add missing Home Assistant 2025 API attributes to Entity and Device models
- Entity: aliases, labels, options, icon (current), original_icon
- Device: labels, serial_number, model_id
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def _schema() -> str:
    """Schema in effect; an unqualified inspector lookup would resolve to public."""
    return op.get_bind().exec_driver_sql("SELECT current_schema()").scalar()


def _columns(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {col["name"] for col in inspector.get_columns(table, schema=_schema())}


def _indexes(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {ix["name"] for ix in inspector.get_indexes(table, schema=_schema()) if ix.get("name")}


def _add_column_if_missing(table: str, column: sa.Column) -> None:
    """init-schemas.sql already defines most of these columns.

    Adding one that exists raises DuplicateColumn, and on PostgreSQL that aborts
    the surrounding transaction, so the failure takes every later statement in
    the migration with it.
    """
    if column.name not in _columns(table):
        op.add_column(table, column)


def _drop_column_if_present(table: str, name: str) -> None:
    if name in _columns(table):
        op.drop_column(table, name)


def _create_index_if_missing(name: str, table: str, columns: list[str], **kw) -> None:
    if name not in _indexes(table):
        op.create_index(name, table, columns, **kw)


def _drop_index_if_present(name: str, table: str) -> None:
    if name in _indexes(table):
        op.drop_index(name, table_name=table)


def _schema() -> str:
    """Schema in effect; an unqualified inspector lookup would resolve to public."""
    return op.get_bind().exec_driver_sql("SELECT current_schema()").scalar()


def _columns(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {col["name"] for col in inspector.get_columns(table, schema=_schema())}


def upgrade():
    """
    Add Home Assistant 2025 API attributes to Entity and Device tables.

    Phase 1 (Critical):
    - Entity.aliases (JSON array)
    - Entity.icon (current icon, separate from original_icon)
    - Entity.original_icon (original icon from integration)

    Phase 2 (Important):
    - Entity.labels (JSON array)
    - Entity.options (JSON object)
    - Device.labels (JSON array)

    Phase 3 (Nice to Have):
    - Device.serial_number (optional string)
    - Device.model_id (optional string)
    """

    # ============================================================================
    # Entity Table: Phase 1-2 Attributes
    # ============================================================================

    # Phase 1: Add aliases (JSON array of alternative names)
    _add_column_if_missing("entities", sa.Column("aliases", sa.JSON(), nullable=True))

    # Phase 1: Add original_icon (original icon from integration/platform)
    # icon already exists from migration 004; original_icon is added alongside it.
    # Ask the catalogue rather than swallowing the failure — on PostgreSQL a
    # failed statement aborts the transaction, so absorbing the error leaves the
    # connection unusable for everything after it.
    if "original_icon" not in _columns("entities"):
        _add_column_if_missing("entities", sa.Column("original_icon", sa.String(), nullable=True))

    # Phase 2: Add labels (JSON array of label IDs)
    _add_column_if_missing("entities", sa.Column("labels", sa.JSON(), nullable=True))

    # Phase 2: Add options (JSON object for entity-specific config)
    _add_column_if_missing("entities", sa.Column("options", sa.JSON(), nullable=True))

    # Phase 1: Add index for name_by_user (for user-customized name lookups)
    _create_index_if_missing("idx_entity_name_by_user", "entities", ["name_by_user"])

    # ============================================================================
    # Device Table: Phase 2-3 Attributes
    # ============================================================================

    # Phase 2: Add labels (JSON array of label IDs)
    _add_column_if_missing("devices", sa.Column("labels", sa.JSON(), nullable=True))

    # Phase 3: Add serial_number (optional)
    _add_column_if_missing("devices", sa.Column("serial_number", sa.String(), nullable=True))

    # Phase 3: Add model_id (optional)
    _add_column_if_missing("devices", sa.Column("model_id", sa.String(), nullable=True))


def downgrade():
    """
    Remove Home Assistant 2025 API attributes from Entity and Device tables.
    """

    # Remove indexes
    _drop_index_if_present("idx_entity_name_by_user", "entities")

    # Remove Entity columns
    _drop_column_if_present("entities", "options")
    _drop_column_if_present("entities", "labels")
    _drop_column_if_present("entities", "original_icon")
    _drop_column_if_present("entities", "aliases")

    # Remove Device columns
    _drop_column_if_present("devices", "model_id")
    _drop_column_if_present("devices", "serial_number")
    _drop_column_if_present("devices", "labels")
