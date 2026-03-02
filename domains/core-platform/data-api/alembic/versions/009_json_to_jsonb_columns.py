"""Convert JSON columns to JSONB for PostgreSQL compatibility

Revision ID: 009
Revises: 008
Create Date: 2026-03-01

PostgreSQL's json type does not support equality operators, which breaks
GROUP BY and DISTINCT queries. JSONB supports full comparison operators
and is also more efficient for indexing and querying. Since this project
is PostgreSQL-only, all JSON columns should use JSONB.

Fixes: "could not identify an equality operator for type json" error
on the Devices page when GROUP BY includes the labels column.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade():
    """Convert all JSON columns to JSONB in devices and entities tables."""

    # Device table: labels
    op.execute(
        "ALTER TABLE core.devices "
        "ALTER COLUMN labels TYPE jsonb USING labels::jsonb"
    )

    # Entity table: capabilities, available_services, aliases, labels, options
    op.execute(
        "ALTER TABLE core.entities "
        "ALTER COLUMN capabilities TYPE jsonb USING capabilities::jsonb"
    )
    op.execute(
        "ALTER TABLE core.entities "
        "ALTER COLUMN available_services TYPE jsonb USING available_services::jsonb"
    )
    op.execute(
        "ALTER TABLE core.entities "
        "ALTER COLUMN aliases TYPE jsonb USING aliases::jsonb"
    )
    op.execute(
        "ALTER TABLE core.entities "
        "ALTER COLUMN labels TYPE jsonb USING labels::jsonb"
    )
    op.execute(
        "ALTER TABLE core.entities "
        "ALTER COLUMN options TYPE jsonb USING options::jsonb"
    )


def downgrade():
    """Revert JSONB columns back to JSON."""

    op.execute(
        "ALTER TABLE core.devices "
        "ALTER COLUMN labels TYPE json USING labels::json"
    )
    op.execute(
        "ALTER TABLE core.entities "
        "ALTER COLUMN capabilities TYPE json USING capabilities::json"
    )
    op.execute(
        "ALTER TABLE core.entities "
        "ALTER COLUMN available_services TYPE json USING available_services::json"
    )
    op.execute(
        "ALTER TABLE core.entities "
        "ALTER COLUMN aliases TYPE json USING aliases::json"
    )
    op.execute(
        "ALTER TABLE core.entities "
        "ALTER COLUMN labels TYPE json USING labels::json"
    )
    op.execute(
        "ALTER TABLE core.entities "
        "ALTER COLUMN options TYPE json USING options::json"
    )
