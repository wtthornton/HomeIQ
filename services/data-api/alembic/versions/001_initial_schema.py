"""Initial schema

Revision ID: 001
Revises:
Create Date: 2025-01-14

"""
from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Initial empty migration - tables will be added in Story 22.2"""


def downgrade() -> None:
    """Rollback initial migration"""

