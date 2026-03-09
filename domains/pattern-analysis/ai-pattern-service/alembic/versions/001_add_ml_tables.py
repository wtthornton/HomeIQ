"""Add ML training data and model registry tables.

Story 40.1 + 40.7: ML Training Data Pipeline and Model Registry.

Revision ID: 001_add_ml_tables
Revises:
Create Date: 2026-03-09
"""
from alembic import op
import sqlalchemy as sa

revision = "001_add_ml_tables"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
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
        schema="automation",
    )

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
        schema="automation",
    )


def downgrade() -> None:
    op.drop_table("ml_models", schema="automation")
    op.drop_table("pattern_training_data", schema="automation")
