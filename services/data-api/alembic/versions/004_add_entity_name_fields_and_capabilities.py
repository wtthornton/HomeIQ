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


def upgrade() -> None:
    """Add entity name fields, capabilities, and create services table"""

    # Add Entity Registry Name Fields
    op.add_column("entities", sa.Column("name", sa.String(), nullable=True))
    op.add_column("entities", sa.Column("name_by_user", sa.String(), nullable=True))
    op.add_column("entities", sa.Column("original_name", sa.String(), nullable=True))
    op.add_column("entities", sa.Column("friendly_name", sa.String(), nullable=True))

    # Add Entity Capabilities
    op.add_column("entities", sa.Column("supported_features", sa.Integer(), nullable=True))
    op.add_column("entities", sa.Column("capabilities", sa.JSON(), nullable=True))
    op.add_column("entities", sa.Column("available_services", sa.JSON(), nullable=True))

    # Add Entity Attributes
    op.add_column("entities", sa.Column("icon", sa.String(), nullable=True))
    op.add_column("entities", sa.Column("device_class", sa.String(), nullable=True))
    op.add_column("entities", sa.Column("unit_of_measurement", sa.String(), nullable=True))

    # Add updated_at timestamp
    op.add_column("entities", sa.Column("updated_at", sa.DateTime(), nullable=True))

    # Create indexes
    op.create_index("idx_entity_friendly_name", "entities", ["friendly_name"])
    op.create_index("idx_entity_supported_features", "entities", ["supported_features"])
    op.create_index("idx_entity_device_class", "entities", ["device_class"])

    # Create services table
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

    # Create index on services.domain
    op.create_index("idx_services_domain", "services", ["domain"])


def downgrade() -> None:
    """Remove added columns and drop services table"""

    # Drop indexes
    op.drop_index("idx_entity_device_class", "entities")
    op.drop_index("idx_entity_supported_features", "entities")
    op.drop_index("idx_entity_friendly_name", "entities")

    # Drop services table
    op.drop_index("idx_services_domain", "services")
    op.drop_table("services")

    # Remove columns from entities
    op.drop_column("entities", "updated_at")
    op.drop_column("entities", "unit_of_measurement")
    op.drop_column("entities", "device_class")
    op.drop_column("entities", "icon")
    op.drop_column("entities", "available_services")
    op.drop_column("entities", "capabilities")
    op.drop_column("entities", "supported_features")
    op.drop_column("entities", "friendly_name")
    op.drop_column("entities", "original_name")
    op.drop_column("entities", "name_by_user")
    op.drop_column("entities", "name")

