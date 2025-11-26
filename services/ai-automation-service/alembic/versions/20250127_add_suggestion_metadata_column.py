"""Add suggestion_metadata column to suggestions table

Revision ID: 20250127_suggestion_metadata
Revises: 20251121_qa_learning
Create Date: 2025-01-27 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20250127_suggestion_metadata'
down_revision = '20251121_qa_learning'  # Follows after Q&A learning migration
branch_labels = None
depends_on = None


def upgrade():
    # Add suggestion_metadata column to suggestions table
    # This column stores flexible metadata (source_type, pattern_type, etc.)
    # Check if column exists first to avoid errors on re-run
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = [col['name'] for col in inspector.get_columns('suggestions')]
    
    if 'suggestion_metadata' not in columns:
        with op.batch_alter_table('suggestions', schema=None) as batch_op:
            batch_op.add_column(sa.Column('suggestion_metadata', sa.JSON(), nullable=True))


def downgrade():
    # Remove suggestion_metadata column
    with op.batch_alter_table('suggestions', schema=None) as batch_op:
        batch_op.drop_column('suggestion_metadata')

