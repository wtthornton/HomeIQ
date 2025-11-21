"""Add confidence algorithm improvements

Revision ID: 20251120_confidence_improvements
Revises: 20250121_model_comparison
Create Date: 2025-11-20 13:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20251120_confidence_improvements"
down_revision = "20250121_model_comparison"  # Current head revision
branch_labels = None
depends_on = None


def upgrade():
    # Add risk_tolerance to system_settings
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # Check if system_settings table exists and get its columns
    if inspector.has_table("system_settings"):
        columns = [col["name"] for col in inspector.get_columns("system_settings")]

        if "risk_tolerance" not in columns:
            op.add_column("system_settings", sa.Column("risk_tolerance", sa.String(), nullable=False, server_default="medium"))

    # Create clarification_confidence_feedback table
    if not inspector.has_table("clarification_confidence_feedback"):
        op.create_table(
            "clarification_confidence_feedback",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("session_id", sa.String(), nullable=False),
            sa.Column("raw_confidence", sa.Float(), nullable=False),
            sa.Column("proceeded", sa.Boolean(), nullable=False),
            sa.Column("suggestion_approved", sa.Boolean(), nullable=True),
            sa.Column("ambiguity_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("critical_ambiguity_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("rounds", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("answer_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["session_id"], ["clarification_sessions.session_id"] ),
        )
        op.create_index("idx_clarification_feedback_session", "clarification_confidence_feedback", ["session_id", "created_at"])
        op.create_index("idx_clarification_feedback_confidence", "clarification_confidence_feedback", ["raw_confidence"])

    # Create clarification_outcomes table
    if not inspector.has_table("clarification_outcomes"):
        op.create_table(
            "clarification_outcomes",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("session_id", sa.String(), nullable=False),
            sa.Column("original_query_id", sa.String(), nullable=True),
            sa.Column("user_id", sa.String(), nullable=False, server_default="anonymous"),
            sa.Column("final_confidence", sa.Float(), nullable=False),
            sa.Column("proceeded", sa.Boolean(), nullable=False),
            sa.Column("suggestion_approved", sa.Boolean(), nullable=True),
            sa.Column("rounds_completed", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("ambiguity_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("critical_ambiguity_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("answer_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("session_id"),
            sa.ForeignKeyConstraint(["session_id"], ["clarification_sessions.session_id"] ),
            sa.ForeignKeyConstraint(["original_query_id"], ["ask_ai_queries.query_id"] ),
        )
        op.create_index("idx_clarification_outcome_query", "clarification_outcomes", ["original_query_id"])
        op.create_index("idx_clarification_outcome_user", "clarification_outcomes", ["user_id"])


def downgrade():
    # Remove tables and columns
    op.drop_index("idx_clarification_outcome_user", table_name="clarification_outcomes")
    op.drop_index("idx_clarification_outcome_query", table_name="clarification_outcomes")
    op.drop_table("clarification_outcomes")

    op.drop_index("idx_clarification_feedback_confidence", table_name="clarification_confidence_feedback")
    op.drop_index("idx_clarification_feedback_session", table_name="clarification_confidence_feedback")
    op.drop_table("clarification_confidence_feedback")

    # Remove risk_tolerance from system_settings
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if inspector.has_table("system_settings"):
        columns = [col["name"] for col in inspector.get_columns("system_settings")]
        if "risk_tolerance" in columns:
            op.drop_column("system_settings", "risk_tolerance")

