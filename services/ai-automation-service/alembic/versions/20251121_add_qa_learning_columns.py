"""Add Q&A learning columns to system_settings

Revision ID: 20251121_qa_learning
Revises: 20251120_confidence
Create Date: 2025-11-21 07:40:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251121_qa_learning'
down_revision = '20250125_enable_answer_caching'  # Follows after enable_answer_caching migration
branch_labels = None
depends_on = None


def upgrade():
    # Add Q&A learning columns to system_settings
    with op.batch_alter_table('system_settings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('enable_qa_learning', sa.Boolean(), nullable=False, server_default='1'))
        batch_op.add_column(sa.Column('preference_consistency_threshold', sa.Float(), nullable=False, server_default='0.9'))
        batch_op.add_column(sa.Column('min_questions_for_preference', sa.Integer(), nullable=False, server_default='3'))
        batch_op.add_column(sa.Column('learning_retrain_frequency', sa.String(), nullable=False, server_default='weekly'))


def downgrade():
    # Remove Q&A learning columns
    with op.batch_alter_table('system_settings', schema=None) as batch_op:
        batch_op.drop_column('learning_retrain_frequency')
        batch_op.drop_column('min_questions_for_preference')
        batch_op.drop_column('preference_consistency_threshold')
        batch_op.drop_column('enable_qa_learning')

