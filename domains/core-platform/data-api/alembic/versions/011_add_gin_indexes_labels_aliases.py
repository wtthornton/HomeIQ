"""Add GIN indexes on entity labels and aliases JSONB columns

Revision ID: 011
Revises: 010
Create Date: 2026-03-14

Story 62.2-62.3: GIN indexes for efficient JSONB containment queries
on labels (@> operator) and aliases (jsonb_array_elements_text).
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = '011'
down_revision = '010'
branch_labels = None
depends_on = None


def upgrade():
    """Add GIN indexes for labels and aliases JSONB columns."""
    op.create_index(
        'idx_entity_labels_gin',
        'entities',
        ['labels'],
        postgresql_using='gin',
    )
    op.create_index(
        'idx_entity_aliases_gin',
        'entities',
        ['aliases'],
        postgresql_using='gin',
    )


def downgrade():
    """Remove GIN indexes."""
    op.drop_index('idx_entity_aliases_gin', table_name='entities')
    op.drop_index('idx_entity_labels_gin', table_name='entities')
