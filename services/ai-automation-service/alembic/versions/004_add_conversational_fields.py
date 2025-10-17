"""add_conversational_fields

Revision ID: 004
Revises: 20251016_120000
Create Date: 2025-10-17 18:50:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '004'
down_revision = '20251016_120000'
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to suggestions table (only if they don't exist)
    try:
        op.add_column('suggestions', sa.Column('description_only', sa.Text(), nullable=False, server_default=''))
    except:
        pass
    
    try:
        op.add_column('suggestions', sa.Column('conversation_history', sa.JSON(), nullable=True))
    except:
        pass
    
    try:
        op.add_column('suggestions', sa.Column('device_capabilities', sa.JSON(), nullable=True))
    except:
        pass
    
    try:
        op.add_column('suggestions', sa.Column('refinement_count', sa.Integer(), nullable=True, server_default='0'))
    except:
        pass
    
    try:
        op.add_column('suggestions', sa.Column('yaml_generated_at', sa.DateTime(), nullable=True))
    except:
        pass
    
    try:
        op.add_column('suggestions', sa.Column('approved_at', sa.DateTime(), nullable=True))
    except:
        pass
    
    # Make automation_yaml nullable (only if not already nullable)
    try:
        op.alter_column('suggestions', 'automation_yaml', nullable=True)
    except:
        pass


def downgrade():
    # Remove new columns
    op.drop_column('suggestions', 'approved_at')
    op.drop_column('suggestions', 'yaml_generated_at')
    op.drop_column('suggestions', 'refinement_count')
    op.drop_column('suggestions', 'device_capabilities')
    op.drop_column('suggestions', 'conversation_history')
    op.drop_column('suggestions', 'description_only')
    
    # Make automation_yaml not nullable again
    op.alter_column('suggestions', 'automation_yaml', nullable=False)
