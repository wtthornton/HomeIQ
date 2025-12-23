"""Add quality improvement fields to patterns

Revision ID: 20251119_quality_improvements
Revises: 20251114_add_discovered_synergies
Create Date: 2025-11-19 17:40:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '20251119_quality_improvements'
down_revision = '398ef0bf19ba'  # Current head revision
branch_labels = None
depends_on = None


def upgrade():
    # Add quality improvement fields to patterns table
    # Check if columns already exist (in case they were added manually)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('patterns')]

    if 'raw_confidence' not in columns:
        op.add_column('patterns', sa.Column('raw_confidence', sa.Float(), nullable=True))

    if 'calibrated' not in columns:
        op.add_column('patterns', sa.Column('calibrated', sa.Boolean(), nullable=False, server_default='0'))


def downgrade():
    # Remove quality improvement fields
    op.drop_column('patterns', 'calibrated')
    op.drop_column('patterns', 'raw_confidence')

