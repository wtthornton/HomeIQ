"""add statistics_meta table

Revision ID: 007
Revises: 006
Create Date: 2025-11-28

Epic 45.1: Add statistics_meta table for tracking entities eligible for statistics aggregation
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.exc import OperationalError

# revision identifiers, used by Alembic.
revision: str = '007'
down_revision: str | None = '006'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create statistics_meta table (idempotent - 2025 pattern)"""
    
    # Use try/except for idempotent migration (2025 best practice for SQLite)
    try:
        op.create_table(
            'statistics_meta',
            sa.Column('statistic_id', sa.String(), nullable=False),  # entity_id (primary key)
            sa.Column('source', sa.String(), nullable=False, server_default='state'),
            sa.Column('unit_of_measurement', sa.String(), nullable=True),
            sa.Column('state_class', sa.String(), nullable=True),
            sa.Column('has_mean', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('has_sum', sa.Boolean(), nullable=False, server_default='0'),
            sa.Column('last_reset', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
            sa.PrimaryKeyConstraint('statistic_id')
        )
    except (OperationalError, Exception) as e:
        # Table already exists - skip creation (idempotent migration)
        # Check if error is about table existing
        if 'already exists' not in str(e).lower():
            raise  # Re-raise if it's a different error
    
    # Create indexes (idempotent - use try/except)
    for index_name, columns in [
        ('idx_statistics_meta_state_class', ['state_class']),
        ('idx_statistics_meta_has_mean', ['has_mean']),
        ('idx_statistics_meta_has_sum', ['has_sum'])
    ]:
        try:
            op.create_index(index_name, 'statistics_meta', columns)
        except Exception:
            # Index already exists - skip (idempotent)
            pass


def downgrade() -> None:
    """Remove statistics_meta table and indexes"""
    
    op.drop_index('idx_statistics_meta_has_sum', 'statistics_meta')
    op.drop_index('idx_statistics_meta_has_mean', 'statistics_meta')
    op.drop_index('idx_statistics_meta_state_class', 'statistics_meta')
    op.drop_table('statistics_meta')


