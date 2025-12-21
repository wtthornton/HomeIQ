"""merge_multiple_heads

Revision ID: d0fcfd3fbe80
Revises: 20250126_training_type, 20250127_suggestion_metadata, 20251201_bge_m3_upgrade
Create Date: 2025-12-21 15:15:36.622576

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd0fcfd3fbe80'
down_revision = ('20250126_training_type', '20250127_suggestion_metadata', '20251201_bge_m3_upgrade')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

