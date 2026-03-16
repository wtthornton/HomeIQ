"""Convert DateTime columns to TIMESTAMP WITH TIME ZONE

Revision ID: 010
Revises: 009
Create Date: 2026-03-13

Fixes: asyncpg DataError when mixing offset-aware Python datetimes
(datetime.now(UTC)) with TIMESTAMP WITHOUT TIME ZONE columns.
The websocket-ingestion service sends timezone-aware datetimes but
the columns were defined as naive, causing all device/entity bulk
upserts to fail with: "can't subtract offset-naive and offset-aware datetimes"
"""

from alembic import op
import sqlalchemy as sa

revision = '010'
down_revision = '009'
branch_labels = None
depends_on = None


def upgrade():
    # Alter device timestamp columns to be timezone-aware
    op.alter_column('devices', 'last_seen',
                    type_=sa.DateTime(timezone=True),
                    existing_type=sa.DateTime(),
                    schema='core',
                    postgresql_using='last_seen AT TIME ZONE \'UTC\'')
    op.alter_column('devices', 'created_at',
                    type_=sa.DateTime(timezone=True),
                    existing_type=sa.DateTime(),
                    schema='core',
                    postgresql_using='created_at AT TIME ZONE \'UTC\'')
    op.alter_column('devices', 'last_capability_sync',
                    type_=sa.DateTime(timezone=True),
                    existing_type=sa.DateTime(),
                    schema='core',
                    postgresql_using='last_capability_sync AT TIME ZONE \'UTC\'')

    # Alter entity timestamp columns to be timezone-aware
    op.alter_column('entities', 'created_at',
                    type_=sa.DateTime(timezone=True),
                    existing_type=sa.DateTime(),
                    schema='core',
                    postgresql_using='created_at AT TIME ZONE \'UTC\'')
    op.alter_column('entities', 'updated_at',
                    type_=sa.DateTime(timezone=True),
                    existing_type=sa.DateTime(),
                    schema='core',
                    postgresql_using='updated_at AT TIME ZONE \'UTC\'')


def downgrade():
    op.alter_column('entities', 'updated_at',
                    type_=sa.DateTime(),
                    existing_type=sa.DateTime(timezone=True),
                    schema='core')
    op.alter_column('entities', 'created_at',
                    type_=sa.DateTime(),
                    existing_type=sa.DateTime(timezone=True),
                    schema='core')
    op.alter_column('devices', 'last_capability_sync',
                    type_=sa.DateTime(),
                    existing_type=sa.DateTime(timezone=True),
                    schema='core')
    op.alter_column('devices', 'created_at',
                    type_=sa.DateTime(),
                    existing_type=sa.DateTime(timezone=True),
                    schema='core')
    op.alter_column('devices', 'last_seen',
                    type_=sa.DateTime(),
                    existing_type=sa.DateTime(timezone=True),
                    schema='core')
