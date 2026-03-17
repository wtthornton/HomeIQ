"""Create network_tls_certificates table.

Revision ID: 003
Revises: 002
Create Date: 2026-03-16
"""

from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None

SCHEMA = "devices"


def upgrade() -> None:
    op.create_table(
        "network_tls_certificates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("fingerprint", sa.String(64), nullable=False, unique=True),
        # Certificate identity
        sa.Column("subject", sa.Text()),
        sa.Column("issuer", sa.Text()),
        sa.Column("serial", sa.String(128)),
        # Validity
        sa.Column("not_valid_before", sa.DateTime(timezone=True)),
        sa.Column("not_valid_after", sa.DateTime(timezone=True)),
        # Key info
        sa.Column("key_type", sa.String(20)),
        sa.Column("key_length", sa.Integer()),
        # TLS negotiation
        sa.Column("tls_version", sa.String(20)),
        sa.Column("cipher_suite", sa.String(100)),
        sa.Column("server_name", sa.String(255)),
        # Flags
        sa.Column("self_signed", sa.Boolean(), server_default="false"),
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
        schema=SCHEMA,
    )
    op.create_index(
        "idx_tls_certs_fingerprint",
        "network_tls_certificates",
        ["fingerprint"],
        unique=True,
        schema=SCHEMA,
    )
    op.create_index(
        "idx_tls_certs_not_valid_after",
        "network_tls_certificates",
        ["not_valid_after"],
        schema=SCHEMA,
    )
    op.create_index(
        "idx_tls_certs_server_name",
        "network_tls_certificates",
        ["server_name"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index("idx_tls_certs_server_name", "network_tls_certificates", schema=SCHEMA)
    op.drop_index("idx_tls_certs_not_valid_after", "network_tls_certificates", schema=SCHEMA)
    op.drop_index("idx_tls_certs_fingerprint", "network_tls_certificates", schema=SCHEMA)
    op.drop_table("network_tls_certificates", schema=SCHEMA)
