"""Add discovered_synergies table for ML-based dynamic synergy discovery

Revision ID: 20251114_discovered_synergies
Revises: 20251020_add_pattern_synergy_integration
Create Date: 2025-11-14

Epic: Dynamic Synergy Discovery (#3)
Improvement: Expand from 16 hardcoded patterns to 50-100+ discovered patterns
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251114_discovered_synergies'
down_revision = '20251020_pattern_synergy'  # Fixed: use actual revision ID
branch_labels = None
depends_on = None


def upgrade():
    """
    Create discovered_synergies table.

    Stores dynamically discovered device relationships from ML mining,
    separate from predefined COMPATIBLE_RELATIONSHIPS in synergy_detector.py.
    """
    op.create_table(
        'discovered_synergies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('synergy_id', sa.String(36), nullable=False),
        sa.Column('trigger_entity', sa.String(255), nullable=False),
        sa.Column('action_entity', sa.String(255), nullable=False),
        sa.Column('source', sa.String(20), nullable=False, default='mined'),  # 'mined' or 'predefined'

        # Association rule metrics
        sa.Column('support', sa.Float(), nullable=False),  # P(X ∪ Y) - How often pattern appears
        sa.Column('confidence', sa.Float(), nullable=False),  # P(Y|X) - Reliability of rule
        sa.Column('lift', sa.Float(), nullable=False),  # P(Y|X) / P(Y) - Strength of association

        # Temporal analysis
        sa.Column('frequency', sa.Integer(), nullable=False),  # Number of occurrences
        sa.Column('consistency', sa.Float(), nullable=False),  # Temporal consistency (0.0-1.0)
        sa.Column('time_window_seconds', sa.Integer(), nullable=False),  # Time window for co-occurrence

        # Discovery metadata
        sa.Column('discovered_at', sa.DateTime(), nullable=False),
        sa.Column('last_validated', sa.DateTime(), nullable=True),
        sa.Column('validation_count', sa.Integer(), nullable=False, default=0),
        sa.Column('validation_passed', sa.Boolean(), nullable=True),

        # Analysis metadata (JSON) - renamed from 'metadata' to avoid SQLAlchemy reserved name
        sa.Column('synergy_metadata', sa.JSON(), nullable=True),
        # Example metadata:
        # {
        #   'analysis_period': {'start': '2025-10-14', 'end': '2025-11-14'},
        #   'total_transactions': 1234,
        #   'mining_duration_seconds': 12.3,
        #   'area': 'living_room',
        #   'device_classes': ['binary_sensor', 'light']
        # }

        # Status
        sa.Column('status', sa.String(20), nullable=False, default='discovered'),  # discovered, validated, rejected
        sa.Column('rejection_reason', sa.Text(), nullable=True),

        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for fast lookups
    op.create_index('ix_discovered_synergies_synergy_id', 'discovered_synergies', ['synergy_id'], unique=True)
    op.create_index('ix_discovered_synergies_trigger', 'discovered_synergies', ['trigger_entity'], unique=False)
    op.create_index('ix_discovered_synergies_action', 'discovered_synergies', ['action_entity'], unique=False)
    op.create_index('ix_discovered_synergies_source', 'discovered_synergies', ['source'], unique=False)
    op.create_index('ix_discovered_synergies_status', 'discovered_synergies', ['status'], unique=False)
    op.create_index('ix_discovered_synergies_confidence', 'discovered_synergies', ['confidence'], unique=False)

    # Composite index for finding specific synergies
    op.create_index(
        'ix_discovered_synergies_trigger_action',
        'discovered_synergies',
        ['trigger_entity', 'action_entity'],
        unique=False
    )


def downgrade():
    """Drop discovered_synergies table and indexes."""
    op.drop_index('ix_discovered_synergies_trigger_action', table_name='discovered_synergies')
    op.drop_index('ix_discovered_synergies_confidence', table_name='discovered_synergies')
    op.drop_index('ix_discovered_synergies_status', table_name='discovered_synergies')
    op.drop_index('ix_discovered_synergies_source', table_name='discovered_synergies')
    op.drop_index('ix_discovered_synergies_action', table_name='discovered_synergies')
    op.drop_index('ix_discovered_synergies_trigger', table_name='discovered_synergies')
    op.drop_index('ix_discovered_synergies_synergy_id', table_name='discovered_synergies')
    op.drop_table('discovered_synergies')
