"""Add automation JSON columns

Revision ID: 001_add_automation_json
Revises: 
Create Date: 2025-01-XX XX:XX:XX

Adds HomeIQ JSON Automation format support to suggestions and automation_versions tables.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '001_add_automation_json'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    
    # Check if tables exist using raw SQL
    result = conn.execute(sa.text("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('suggestions', 'automation_versions')"))
    existing_tables = [row[0] for row in result]
    
    # If tables don't exist, create them using Base.metadata
    if 'suggestions' not in existing_tables or 'automation_versions' not in existing_tables:
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        from src.database.models import Base
        Base.metadata.create_all(conn)
        # Re-check existing tables after creation
        result = conn.execute(sa.text("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('suggestions', 'automation_versions')"))
        existing_tables = [row[0] for row in result]
    
    # Check if columns exist before adding (SQLite-specific)
    if 'suggestions' in existing_tables:
        result = conn.execute(sa.text("PRAGMA table_info(suggestions)"))
        suggestions_columns = [row[1] for row in result]
        
        if 'automation_json' not in suggestions_columns:
            op.add_column('suggestions', sa.Column('automation_json', sa.JSON(), nullable=True))
        if 'ha_version' not in suggestions_columns:
            op.add_column('suggestions', sa.Column('ha_version', sa.String(), nullable=True))
        if 'json_schema_version' not in suggestions_columns:
            op.add_column('suggestions', sa.Column('json_schema_version', sa.String(), nullable=True))
    
    if 'automation_versions' in existing_tables:
        result = conn.execute(sa.text("PRAGMA table_info(automation_versions)"))
        automation_versions_columns = [row[1] for row in result]
        
        if 'automation_json' not in automation_versions_columns:
            op.add_column('automation_versions', sa.Column('automation_json', sa.JSON(), nullable=True))
        if 'ha_version' not in automation_versions_columns:
            op.add_column('automation_versions', sa.Column('ha_version', sa.String(), nullable=True))
        if 'json_schema_version' not in automation_versions_columns:
            op.add_column('automation_versions', sa.Column('json_schema_version', sa.String(), nullable=True))


def downgrade() -> None:
    # Remove columns from automation_versions table
    op.drop_column('automation_versions', 'json_schema_version')
    op.drop_column('automation_versions', 'ha_version')
    op.drop_column('automation_versions', 'automation_json')
    
    # Remove columns from suggestions table
    op.drop_column('suggestions', 'json_schema_version')
    op.drop_column('suggestions', 'ha_version')
    op.drop_column('suggestions', 'automation_json')

