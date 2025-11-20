"""Add model comparison metrics table and parallel testing settings

Revision ID: 20250121_model_comparison
Revises: 20251119_quality_improvements
Create Date: 2025-01-21 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite


# revision identifiers, used by Alembic.
revision = '20250121_model_comparison'
down_revision = '20251119_quality_improvements'
branch_labels = None
depends_on = None


def upgrade():
    # Create model_comparison_metrics table
    op.create_table(
        'model_comparison_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('task_type', sa.String(), nullable=False),
        sa.Column('query_id', sa.String(), nullable=True),
        sa.Column('suggestion_id', sa.String(), nullable=True),
        
        # Model 1 (Primary)
        sa.Column('model1_name', sa.String(), nullable=False),
        sa.Column('model1_tokens_input', sa.Integer(), nullable=False),
        sa.Column('model1_tokens_output', sa.Integer(), nullable=False),
        sa.Column('model1_cost_usd', sa.Float(), nullable=False),
        sa.Column('model1_latency_ms', sa.Integer(), nullable=False),
        sa.Column('model1_result', sa.JSON(), nullable=True),
        sa.Column('model1_error', sa.String(), nullable=True),
        
        # Model 2 (Comparison)
        sa.Column('model2_name', sa.String(), nullable=False),
        sa.Column('model2_tokens_input', sa.Integer(), nullable=False),
        sa.Column('model2_tokens_output', sa.Integer(), nullable=False),
        sa.Column('model2_cost_usd', sa.Float(), nullable=False),
        sa.Column('model2_latency_ms', sa.Integer(), nullable=False),
        sa.Column('model2_result', sa.JSON(), nullable=True),
        sa.Column('model2_error', sa.String(), nullable=True),
        
        # Quality Metrics
        sa.Column('model1_approved', sa.Boolean(), nullable=True),
        sa.Column('model2_approved', sa.Boolean(), nullable=True),
        sa.Column('model1_yaml_valid', sa.Boolean(), nullable=True),
        sa.Column('model2_yaml_valid', sa.Boolean(), nullable=True),
        
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('idx_model_comp_task_type', 'model_comparison_metrics', ['task_type'])
    op.create_index('idx_model_comp_created_at', 'model_comparison_metrics', ['created_at'])
    op.create_index('idx_model_comp_query_id', 'model_comparison_metrics', ['query_id'])
    op.create_index('idx_model_comp_suggestion_id', 'model_comparison_metrics', ['suggestion_id'])
    
    # Add parallel testing fields to system_settings
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('system_settings')]
    
    if 'enable_parallel_model_testing' not in columns:
        op.add_column('system_settings', sa.Column('enable_parallel_model_testing', sa.Boolean(), nullable=False, server_default='0'))
    
    if 'parallel_testing_models' not in columns:
        # Add column as nullable (SQLite JSON handling - defaults handled in application code)
        op.add_column('system_settings', sa.Column('parallel_testing_models', sa.JSON(), nullable=True))


def downgrade():
    # Remove parallel testing fields from system_settings
    op.drop_column('system_settings', 'parallel_testing_models')
    op.drop_column('system_settings', 'enable_parallel_model_testing')
    
    # Drop indexes
    op.drop_index('idx_model_comp_suggestion_id', table_name='model_comparison_metrics')
    op.drop_index('idx_model_comp_query_id', table_name='model_comparison_metrics')
    op.drop_index('idx_model_comp_created_at', table_name='model_comparison_metrics')
    op.drop_index('idx_model_comp_task_type', table_name='model_comparison_metrics')
    
    # Drop table
    op.drop_table('model_comparison_metrics')

