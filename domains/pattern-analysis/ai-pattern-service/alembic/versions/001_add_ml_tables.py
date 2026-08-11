"""Add ML training data and model registry tables.

Story 40.1 + 40.7: ML Training Data Pipeline and Model Registry.

Revision ID: 001_add_ml_tables
Revises:
Create Date: 2026-03-09
"""

import sqlalchemy as sa
from alembic import op

revision = "001_add_ml_tables"
down_revision = None
branch_labels = None
depends_on = None


SCHEMA = "automation"


def _tables() -> set[str]:
    """Tables in SCHEMA. This migration pins the schema explicitly rather than
    relying on search_path, so the lookup has to be pinned the same way."""
    return set(sa.inspect(op.get_bind()).get_table_names(schema=SCHEMA))


def upgrade() -> None:
    # infrastructure/postgres/init-schemas.sql owns both tables, so on a normal
    # database they exist already and op.create_table raised DuplicateTable.
    existing = _tables()

    if "pattern_training_data" not in existing:
        op.create_table(
            "pattern_training_data",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("run_id", sa.String(36), nullable=False, index=True),
            sa.Column("pattern_type", sa.String(50), nullable=False, index=True),
            sa.Column("device_id", sa.String(255), nullable=True),
            sa.Column("raw_events_summary", sa.JSON(), nullable=False),
            sa.Column("detected_pattern", sa.JSON(), nullable=False),
            sa.Column("user_action", sa.String(20), nullable=True, index=True),
            sa.Column("user_feedback_at", sa.DateTime(), nullable=True),
            sa.Column("confidence", sa.Float(), nullable=False),
            sa.Column("ml_model_version", sa.String(50), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.now(),
                index=True,
            ),
            schema=SCHEMA,
        )

    if "ml_models" not in existing:
        op.create_table(
            "ml_models",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("model_name", sa.String(100), nullable=False, index=True),
            sa.Column("version", sa.String(50), nullable=False),
            sa.Column("file_path", sa.String(500), nullable=False),
            sa.Column("metrics", sa.JSON(), server_default="{}"),
            sa.Column("metadata", sa.JSON(), server_default="{}"),
            sa.Column(
                "trained_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default="true",
                index=True,
            ),
            schema=SCHEMA,
        )


def downgrade() -> None:
    existing = _tables()
    for table in ("ml_models", "pattern_training_data"):
        if table in existing:
            op.drop_table(table, schema=SCHEMA)
