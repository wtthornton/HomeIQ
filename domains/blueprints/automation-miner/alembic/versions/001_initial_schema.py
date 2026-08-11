"""Initial schema for community automations

Revision ID: 001
Revises:
Create Date: 2025-10-18 20:00:00

infrastructure/postgres/init-schemas.sql owns both of these tables, so on any
database initialised from it they already exist and op.create_table raised
DuplicateTable: relation "community_automations" already exists. This migration
creates only what is genuinely missing, which keeps it useful for a database
brought up without init-schemas while staying a no-op on a normal one.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _schema() -> str:
    """The schema this migration targets.

    The inspector resolves unqualified lookups against the connection's default
    schema (public) rather than the search_path the alembic env sets, so ask the
    server which schema is actually in effect.
    """
    return op.get_bind().exec_driver_sql("SELECT current_schema()").scalar()


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names(schema=_schema()))


def upgrade() -> None:
    existing = _tables()

    if "community_automations" not in existing:
        op.create_table(
            "community_automations",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("source", sa.String(length=20), nullable=False),
            sa.Column("source_id", sa.String(length=200), nullable=False),
            sa.Column("title", sa.String(length=200), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("devices", sa.JSON(), nullable=False),
            sa.Column("integrations", sa.JSON(), nullable=False),
            sa.Column("triggers", sa.JSON(), nullable=False),
            sa.Column("conditions", sa.JSON(), nullable=True),
            sa.Column("actions", sa.JSON(), nullable=False),
            sa.Column("use_case", sa.String(length=20), nullable=False),
            sa.Column("complexity", sa.String(length=10), nullable=False),
            sa.Column("quality_score", sa.Float(), nullable=False),
            sa.Column("vote_count", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("last_crawled", sa.DateTime(), nullable=False),
            sa.Column("extra_metadata", sa.JSON(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("source", "source_id", name="uq_source_source_id"),
        )
        op.create_index("ix_source", "community_automations", ["source"])
        op.create_index("ix_use_case", "community_automations", ["use_case"])
        op.create_index("ix_quality_score", "community_automations", ["quality_score"])

    if "miner_state" not in existing:
        op.create_table(
            "miner_state",
            sa.Column("key", sa.String(length=100), nullable=False),
            sa.Column("value", sa.Text(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("key"),
        )


def downgrade() -> None:
    # Dropping a table takes its indexes with it, so they are not named here —
    # an init-schemas-built database does not necessarily have ix_source and
    # friends, and naming them would fail.
    existing = _tables()

    for table in ("miner_state", "community_automations"):
        if table in existing:
            op.drop_table(table)
