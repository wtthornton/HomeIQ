"""Add semantic_knowledge table for RAG (Retrieval-Augmented Generation)

Revision ID: 20250120_semantic_knowledge
Revises: 20251114_discovered_synergies
Create Date: 2025-01-20

Epic: Semantic Understanding Growth
Purpose: Store semantic knowledge with embeddings for similarity search
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite


# revision identifiers, used by Alembic.
revision = '20250120_semantic_knowledge'
down_revision = '20251114_discovered_synergies'  # Follows after discovered_synergies migration
branch_labels = None
depends_on = None


def upgrade():
    """
    Create semantic_knowledge table for RAG system.
    
    Stores text with embeddings for semantic similarity search.
    Used for query clarification, pattern matching, and other semantic tasks.
    """
    op.create_table(
        'semantic_knowledge',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('embedding', sa.JSON(), nullable=False),  # 384-dim array stored as JSON
        sa.Column('knowledge_type', sa.String(), nullable=False),  # 'query', 'pattern', 'blueprint', etc.
        sa.Column('metadata', sa.JSON(), nullable=True),  # Flexible metadata
        sa.Column('success_score', sa.Float(), nullable=False, server_default='0.5'),  # 0.0-1.0
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for performance
    op.create_index('idx_knowledge_type', 'semantic_knowledge', ['knowledge_type'])
    op.create_index('idx_success_score', 'semantic_knowledge', ['success_score'])
    op.create_index('idx_created_at', 'semantic_knowledge', ['created_at'])


def downgrade():
    """Drop semantic_knowledge table"""
    op.drop_index('idx_created_at', table_name='semantic_knowledge')
    op.drop_index('idx_success_score', table_name='semantic_knowledge')
    op.drop_index('idx_knowledge_type', table_name='semantic_knowledge')
    op.drop_table('semantic_knowledge')

