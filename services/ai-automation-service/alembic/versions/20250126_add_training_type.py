"""Add training_type to training_runs

Revision ID: 20250126_training_type
Revises: 20251121_qa_learning
Create Date: 2025-01-26 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20250126_training_type'
down_revision = '20250124_add_failure_reason'
branch_labels = None
depends_on = None


def upgrade():
    # Add training_type column to training_runs table
    with op.batch_alter_table('training_runs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('training_type', sa.String(20), nullable=False, server_default='soft_prompt'))


def downgrade():
    # Remove training_type column
    with op.batch_alter_table('training_runs', schema=None) as batch_op:
        batch_op.drop_column('training_type')

