"""Create network_baseline_hosts table.

Revision ID: 004
Revises: 003
Create Date: 2026-03-16
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import INET, JSONB

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None

SCHEMA = "devices"


def upgrade() -> None:
    op.create_table(
        "network_baseline_hosts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ip_address", INET, nullable=False, unique=True),
        sa.Column("mac_address", sa.String(17)),
        sa.Column("hostname", sa.String(255)),
        # Services JSONB — e.g. [{"port": 80, "proto": "tcp", "service": "http"}]
        sa.Column("services", JSONB),
        # Baseline approval
        sa.Column("is_baseline", sa.Boolean(), server_default="false"),
        sa.Column("approved_by", sa.String(100)),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        # Metadata
        sa.Column(
            "first_seen",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "last_seen",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("times_seen", sa.Integer(), server_default="1"),
        sa.Column("notes", sa.Text()),
        schema=SCHEMA,
    )
    op.create_index(
        "idx_baseline_ip",
        "network_baseline_hosts",
        ["ip_address"],
        unique=True,
        schema=SCHEMA,
    )
    op.create_index(
        "idx_baseline_mac",
        "network_baseline_hosts",
        ["mac_address"],
        schema=SCHEMA,
    )
    op.create_index(
        "idx_baseline_is_baseline",
        "network_baseline_hosts",
        ["is_baseline"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index("idx_baseline_is_baseline", "network_baseline_hosts", schema=SCHEMA)
    op.drop_index("idx_baseline_mac", "network_baseline_hosts", schema=SCHEMA)
    op.drop_index("idx_baseline_ip", "network_baseline_hosts", schema=SCHEMA)
    op.drop_table("network_baseline_hosts", schema=SCHEMA)
