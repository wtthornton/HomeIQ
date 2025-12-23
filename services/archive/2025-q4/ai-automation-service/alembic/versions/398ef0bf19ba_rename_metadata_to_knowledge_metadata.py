"""rename_metadata_to_knowledge_metadata

Revision ID: 398ef0bf19ba
Revises: 20250120_semantic_knowledge
Create Date: 2025-11-17 08:06:50.232263

Rename 'metadata' column to 'knowledge_metadata' in semantic_knowledge table
to avoid SQLAlchemy reserved word conflict.
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '398ef0bf19ba'
down_revision = '20250120_semantic_knowledge'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Rename 'metadata' column to 'knowledge_metadata' in semantic_knowledge table.
    
    SQLite doesn't support ALTER COLUMN RENAME, so we need to:
    1. Create a new table with the renamed column
    2. Copy data from old table to new table
    3. Drop old table
    4. Rename new table to original name
    5. Recreate indexes
    """
    # Check if the column exists (in case migration runs on fresh database)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('semantic_knowledge')]

    if 'metadata' in columns and 'knowledge_metadata' not in columns:
        # Create temporary table with renamed column
        op.create_table(
            'semantic_knowledge_new',
            sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
            sa.Column('text', sa.Text(), nullable=False),
            sa.Column('embedding', sa.JSON(), nullable=False),
            sa.Column('knowledge_type', sa.String(), nullable=False),
            sa.Column('knowledge_metadata', sa.JSON(), nullable=True),  # Renamed column
            sa.Column('success_score', sa.Float(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint('id')
        )

        # Drop indexes on old table before dropping it
        op.drop_index('idx_knowledge_type', table_name='semantic_knowledge')
        op.drop_index('idx_success_score', table_name='semantic_knowledge')
        op.drop_index('idx_created_at', table_name='semantic_knowledge')

        # Copy data from old table to new table
        op.execute("""
            INSERT INTO semantic_knowledge_new (id, text, embedding, knowledge_type, knowledge_metadata, success_score, created_at, updated_at)
            SELECT id, text, embedding, knowledge_type, metadata, success_score, created_at, updated_at
            FROM semantic_knowledge
        """)

        # Drop old table
        op.drop_table('semantic_knowledge')

        # Rename new table to original name (SQLite supports this)
        op.execute("ALTER TABLE semantic_knowledge_new RENAME TO semantic_knowledge")

        # Recreate indexes
        op.create_index('idx_knowledge_type', 'semantic_knowledge', ['knowledge_type'])
        op.create_index('idx_success_score', 'semantic_knowledge', ['success_score'])
        op.create_index('idx_created_at', 'semantic_knowledge', ['created_at'])
    elif 'knowledge_metadata' in columns:
        # Column already renamed, skip migration
        pass


def downgrade() -> None:
    """
    Rename 'knowledge_metadata' column back to 'metadata'.
    """
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('semantic_knowledge')]

    if 'knowledge_metadata' in columns and 'metadata' not in columns:
        # Create temporary table with original column name
        op.create_table(
            'semantic_knowledge_new',
            sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
            sa.Column('text', sa.Text(), nullable=False),
            sa.Column('embedding', sa.JSON(), nullable=False),
            sa.Column('knowledge_type', sa.String(), nullable=False),
            sa.Column('metadata', sa.JSON(), nullable=True),  # Original column name
            sa.Column('success_score', sa.Float(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint('id')
        )

        # Drop indexes on current table before dropping it
        op.drop_index('idx_knowledge_type', table_name='semantic_knowledge')
        op.drop_index('idx_success_score', table_name='semantic_knowledge')
        op.drop_index('idx_created_at', table_name='semantic_knowledge')

        # Copy data from current table to new table
        op.execute("""
            INSERT INTO semantic_knowledge_new (id, text, embedding, knowledge_type, metadata, success_score, created_at, updated_at)
            SELECT id, text, embedding, knowledge_type, knowledge_metadata, success_score, created_at, updated_at
            FROM semantic_knowledge
        """)

        # Drop current table
        op.drop_table('semantic_knowledge')

        # Rename new table to original name (SQLite supports this)
        op.execute("ALTER TABLE semantic_knowledge_new RENAME TO semantic_knowledge")

        # Recreate indexes
        op.create_index('idx_knowledge_type', 'semantic_knowledge', ['knowledge_type'])
        op.create_index('idx_success_score', 'semantic_knowledge', ['success_score'])
        op.create_index('idx_created_at', 'semantic_knowledge', ['created_at'])

