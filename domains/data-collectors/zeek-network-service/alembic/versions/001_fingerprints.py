"""Create network_device_fingerprints table.

Revision ID: 001
Revises:
Create Date: 2026-03-16
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import INET

revision = "001"
down_revision = None
branch_labels = None
depends_on = None

SCHEMA = "devices"


def upgrade() -> None:
    op.create_table(
        "network_device_fingerprints",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("mac_address", sa.String(17), nullable=False, unique=True),
        sa.Column("ip_address", INET(), nullable=False),
        sa.Column("hostname", sa.String(255)),
        sa.Column("vendor", sa.String(255)),
        # DHCP
        sa.Column("dhcp_fingerprint", sa.String(512)),
        sa.Column("dhcp_vendor_class", sa.String(255)),
        # TLS
        sa.Column("ja3_hash", sa.String(32)),
        sa.Column("ja3s_hash", sa.String(32)),
        sa.Column("ja4_hash", sa.String(64)),
        # SSH
        sa.Column("hassh_hash", sa.String(32)),
        sa.Column("hassh_server", sa.String(32)),
        # Software
        sa.Column("user_agent", sa.Text()),
        sa.Column("server_software", sa.Text()),
        sa.Column("os_guess", sa.String(100)),
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
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        schema=SCHEMA,
    )
    op.create_index(
        "idx_fingerprints_ip",
        "network_device_fingerprints",
        ["ip_address"],
        schema=SCHEMA,
    )
    op.create_index(
        "idx_fingerprints_ja3",
        "network_device_fingerprints",
        ["ja3_hash"],
        schema=SCHEMA,
    )
    op.create_index(
        "idx_fingerprints_ja4",
        "network_device_fingerprints",
        ["ja4_hash"],
        schema=SCHEMA,
    )
    op.create_index(
        "idx_fingerprints_vendor",
        "network_device_fingerprints",
        ["vendor"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index("idx_fingerprints_vendor", "network_device_fingerprints", schema=SCHEMA)
    op.drop_index("idx_fingerprints_ja4", "network_device_fingerprints", schema=SCHEMA)
    op.drop_index("idx_fingerprints_ja3", "network_device_fingerprints", schema=SCHEMA)
    op.drop_index("idx_fingerprints_ip", "network_device_fingerprints", schema=SCHEMA)
    op.drop_table("network_device_fingerprints", schema=SCHEMA)
