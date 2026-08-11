"""add devices and entities tables

Revision ID: 002
Revises: 001
Create Date: 2025-01-14

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _schema() -> str:
    """Schema in effect; an unqualified inspector lookup would resolve to public."""
    return op.get_bind().exec_driver_sql("SELECT current_schema()").scalar()


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names(schema=_schema()))


def upgrade() -> None:
    """Create devices and entities tables"""

    # infrastructure/postgres/init-schemas.sql owns both tables, so on a normal
    # database they already exist and op.create_table raised
    # DuplicateTable: relation "devices" already exists. Create only what is
    # missing; indexes go with the table that owns them.
    existing = _tables()

    if "devices" not in existing:
        op.create_table(
            "devices",
            sa.Column("device_id", sa.String(), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("manufacturer", sa.String(), nullable=True),
            sa.Column("model", sa.String(), nullable=True),
            sa.Column("sw_version", sa.String(), nullable=True),
            sa.Column("area_id", sa.String(), nullable=True),
            sa.Column("integration", sa.String(), nullable=True),
            sa.Column("last_seen", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("device_id"),
        )

        op.create_index("idx_device_area", "devices", ["area_id"])
        op.create_index("idx_device_integration", "devices", ["integration"])
        op.create_index("idx_device_manufacturer", "devices", ["manufacturer"])

    if "entities" not in existing:
        op.create_table(
            "entities",
            sa.Column("entity_id", sa.String(), nullable=False),
            sa.Column("device_id", sa.String(), nullable=True),
            sa.Column("domain", sa.String(), nullable=False),
            sa.Column("platform", sa.String(), nullable=True),
            sa.Column("unique_id", sa.String(), nullable=True),
            sa.Column("area_id", sa.String(), nullable=True),
            sa.Column("disabled", sa.Boolean(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["device_id"], ["devices.device_id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("entity_id"),
        )

        op.create_index("idx_entity_device", "entities", ["device_id"])
        op.create_index("idx_entity_domain", "entities", ["domain"])
        op.create_index("idx_entity_area", "entities", ["area_id"])


def downgrade() -> None:
    """Drop devices and entities tables"""

    existing = _tables()
    for table in ("entities", "devices"):
        if table in existing:
            op.drop_table(table)
