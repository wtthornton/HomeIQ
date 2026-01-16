"""Add hybrid flow tables

Revision ID: 002_add_hybrid_flow_tables
Revises: 001_add_automation_json
Create Date: 2026-01-16 21:00:00

Hybrid Flow Implementation: Adds tables for template-based automation flow.

Tables:
- plans: Structured automation plans (template_id + parameters from LLM)
- compiled_artifacts: Compiled YAML artifacts (deterministic compilation)
- deployments: Deployment records with full audit trail

This migration enables the hybrid flow where:
1. LLM outputs structured plan (template_id + parameters), never YAML
2. YAML is compiled deterministically from templates
3. All automations deployed with full audit trail
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '002_add_hybrid_flow_tables'
down_revision: str | None = '001_add_automation_json'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    
    # Create plans table
    op.create_table(
        'plans',
        sa.Column('plan_id', sa.String(), nullable=False),
        sa.Column('conversation_id', sa.String(), nullable=True),
        sa.Column('template_id', sa.String(), nullable=False),
        sa.Column('template_version', sa.Integer(), nullable=False),
        sa.Column('parameters', sa.JSON(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('clarifications_needed', sa.JSON(), nullable=True),
        sa.Column('safety_class', sa.String(), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.PrimaryKeyConstraint('plan_id')
    )
    op.create_index(op.f('ix_plans_plan_id'), 'plans', ['plan_id'], unique=False)
    op.create_index(op.f('ix_plans_conversation_id'), 'plans', ['conversation_id'], unique=False)
    op.create_index(op.f('ix_plans_template_id'), 'plans', ['template_id'], unique=False)
    op.create_index(op.f('ix_plans_created_at'), 'plans', ['created_at'], unique=False)
    
    # Create compiled_artifacts table
    op.create_table(
        'compiled_artifacts',
        sa.Column('compiled_id', sa.String(), nullable=False),
        sa.Column('plan_id', sa.String(), nullable=False),
        sa.Column('yaml', sa.Text(), nullable=False),
        sa.Column('human_summary', sa.Text(), nullable=False),
        sa.Column('diff_summary', sa.JSON(), nullable=True),
        sa.Column('risk_notes', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.ForeignKeyConstraint(['plan_id'], ['plans.plan_id'], ),
        sa.PrimaryKeyConstraint('compiled_id')
    )
    op.create_index(op.f('ix_compiled_artifacts_compiled_id'), 'compiled_artifacts', ['compiled_id'], unique=False)
    op.create_index(op.f('ix_compiled_artifacts_plan_id'), 'compiled_artifacts', ['plan_id'], unique=False)
    op.create_index(op.f('ix_compiled_artifacts_created_at'), 'compiled_artifacts', ['created_at'], unique=False)
    
    # Create deployments table
    op.create_table(
        'deployments',
        sa.Column('deployment_id', sa.String(), nullable=False),
        sa.Column('compiled_id', sa.String(), nullable=False),
        sa.Column('ha_automation_id', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('approved_by', sa.String(), nullable=True),
        sa.Column('ui_source', sa.String(), nullable=True),
        sa.Column('deployed_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('audit_data', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['compiled_id'], ['compiled_artifacts.compiled_id'], ),
        sa.PrimaryKeyConstraint('deployment_id')
    )
    op.create_index(op.f('ix_deployments_deployment_id'), 'deployments', ['deployment_id'], unique=False)
    op.create_index(op.f('ix_deployments_compiled_id'), 'deployments', ['compiled_id'], unique=False)
    op.create_index(op.f('ix_deployments_ha_automation_id'), 'deployments', ['ha_automation_id'], unique=False)
    op.create_index(op.f('ix_deployments_status'), 'deployments', ['status'], unique=False)
    op.create_index(op.f('ix_deployments_deployed_at'), 'deployments', ['deployed_at'], unique=False)
    
    # Add foreign key columns to suggestions table (optional, for linking)
    # Check if columns exist first
    result = conn.execute(sa.text("PRAGMA table_info(suggestions)"))
    suggestions_columns = [row[1] for row in result]
    
    if 'plan_id' not in suggestions_columns:
        op.add_column('suggestions', sa.Column('plan_id', sa.String(), nullable=True))
        op.create_index(op.f('ix_suggestions_plan_id'), 'suggestions', ['plan_id'], unique=False)
    
    if 'compiled_id' not in suggestions_columns:
        op.add_column('suggestions', sa.Column('compiled_id', sa.String(), nullable=True))
        op.create_index(op.f('ix_suggestions_compiled_id'), 'suggestions', ['compiled_id'], unique=False)
    
    if 'deployment_id' not in suggestions_columns:
        op.add_column('suggestions', sa.Column('deployment_id', sa.String(), nullable=True))
        op.create_index(op.f('ix_suggestions_deployment_id'), 'suggestions', ['deployment_id'], unique=False)


def downgrade() -> None:
    # Remove indexes and columns from suggestions
    op.drop_index(op.f('ix_suggestions_deployment_id'), table_name='suggestions')
    op.drop_index(op.f('ix_suggestions_compiled_id'), table_name='suggestions')
    op.drop_index(op.f('ix_suggestions_plan_id'), table_name='suggestions')
    op.drop_column('suggestions', 'deployment_id')
    op.drop_column('suggestions', 'compiled_id')
    op.drop_column('suggestions', 'plan_id')
    
    # Drop tables
    op.drop_index(op.f('ix_deployments_deployed_at'), table_name='deployments')
    op.drop_index(op.f('ix_deployments_status'), table_name='deployments')
    op.drop_index(op.f('ix_deployments_ha_automation_id'), table_name='deployments')
    op.drop_index(op.f('ix_deployments_compiled_id'), table_name='deployments')
    op.drop_index(op.f('ix_deployments_deployment_id'), table_name='deployments')
    op.drop_table('deployments')
    
    op.drop_index(op.f('ix_compiled_artifacts_created_at'), table_name='compiled_artifacts')
    op.drop_index(op.f('ix_compiled_artifacts_plan_id'), table_name='compiled_artifacts')
    op.drop_index(op.f('ix_compiled_artifacts_compiled_id'), table_name='compiled_artifacts')
    op.drop_table('compiled_artifacts')
    
    op.drop_index(op.f('ix_plans_created_at'), table_name='plans')
    op.drop_index(op.f('ix_plans_template_id'), table_name='plans')
    op.drop_index(op.f('ix_plans_conversation_id'), table_name='plans')
    op.drop_index(op.f('ix_plans_plan_id'), table_name='plans')
    op.drop_table('plans')
