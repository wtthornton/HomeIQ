"""Add automation versions table for rollback

Revision ID: 20251016_120000
Revises: 20251016_095206
Create Date: 2025-10-16
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '20251016_120000'
down_revision = '20251016_095206'
branch_labels = None
depends_on = None


def upgrade():
    """Create automation_versions table"""
    op.create_table(
        'automation_versions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('automation_id', sa.String(100), nullable=False),
        sa.Column('yaml_content', sa.Text(), nullable=False),
        sa.Column('deployed_at', sa.DateTime(), nullable=False),
        sa.Column('safety_score', sa.Integer(), nullable=False)
    )

    # Create index for fast lookups
    op.create_index('ix_automation_versions_automation_id', 'automation_versions', ['automation_id'])


def downgrade():
    """Drop automation_versions table"""
    op.drop_index('ix_automation_versions_automation_id', table_name='automation_versions')
    op.drop_table('automation_versions')

