"""Create network_device_dns_profiles table.

Revision ID: 002
Revises: 001
Create Date: 2026-03-16
"""

from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None

SCHEMA = "devices"


def upgrade() -> None:
    op.create_table(
        "network_device_dns_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("device_ip", sa.String(45), nullable=False),
        sa.Column("domain_suffix", sa.String(255), nullable=False),
        sa.Column("category", sa.String(50), nullable=False, server_default="unknown"),
        sa.Column("query_count_7d", sa.Integer(), server_default="0"),
        sa.Column(
            "last_query_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "first_seen",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "last_updated",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("device_ip", "domain_suffix", name="uq_dns_profile_device_domain"),
        schema=SCHEMA,
    )
    op.create_index(
        "idx_dns_profiles_device_ip",
        "network_device_dns_profiles",
        ["device_ip"],
        schema=SCHEMA,
    )
    op.create_index(
        "idx_dns_profiles_domain",
        "network_device_dns_profiles",
        ["domain_suffix"],
        schema=SCHEMA,
    )
    op.create_index(
        "idx_dns_profiles_category",
        "network_device_dns_profiles",
        ["category"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index("idx_dns_profiles_category", "network_device_dns_profiles", schema=SCHEMA)
    op.drop_index("idx_dns_profiles_domain", "network_device_dns_profiles", schema=SCHEMA)
    op.drop_index("idx_dns_profiles_device_ip", "network_device_dns_profiles", schema=SCHEMA)
    op.drop_table("network_device_dns_profiles", schema=SCHEMA)
