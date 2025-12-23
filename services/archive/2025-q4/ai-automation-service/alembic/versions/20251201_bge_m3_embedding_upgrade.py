"""BGE-M3 Embedding Upgrade - Epic 47

Revision ID: 20251201_bge_m3_upgrade
Revises: 20250120_semantic_knowledge
Create Date: 2025-12-01

Epic 47: BGE-M3 Embedding Model Upgrade (Phase 1)
Purpose: Document upgrade from all-MiniLM-L6-v2 (384-dim) to BGE-M3-base (1024-dim)

Note: No schema changes required - JSON column already supports variable dimensions.
This migration documents the upgrade and provides optional embedding regeneration guidance.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '20251201_bge_m3_upgrade'
down_revision = '20250120_semantic_knowledge'  # Follows after semantic_knowledge migration
branch_labels = None
depends_on = None


def upgrade():
    """
    Document BGE-M3 embedding upgrade.
    
    The semantic_knowledge.embedding column (JSON) already supports variable dimensions.
    No schema changes needed - embeddings can be 384-dim (all-MiniLM-L6-v2) or 1024-dim (BGE-M3-base).
    
    Existing embeddings will continue to work but may have lower accuracy.
    To regenerate embeddings with BGE-M3:
    1. Update OpenVINO service to use BGE-M3 (OPENVINO_EMBEDDING_MODEL=BAAI/bge-m3-base)
    2. Run embedding regeneration script (optional):
       python scripts/regenerate_embeddings.py --model bge-m3
    """
    # No schema changes - JSON column is flexible
    # This migration serves as documentation of the upgrade
    pass


def downgrade():
    """
    Revert to all-MiniLM-L6-v2 embeddings.
    
    To downgrade:
    1. Set OPENVINO_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
    2. Regenerate embeddings if needed (optional)
    """
    # No schema changes to revert
    pass

