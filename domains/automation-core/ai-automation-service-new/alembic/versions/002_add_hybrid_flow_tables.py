"""Add hybrid flow tables

Revision ID: 002_add_hybrid_flow_tables
Revises: 001_add_automation_json
Create Date: 2026-01-16 21:00:00

Hybrid Flow Implementation: Adds tables for template-based automation flow.

Tables:
- plans: Structured automation plans (template_id + parameters from LLM)
- compiled_artifacts: Compiled YAML artifacts (deterministic compilation)
- deployments: Deployment records with full audit trail

This migration enables the hybrid flow where:
1. LLM outputs structured plan (template_id + parameters), never YAML
2. YAML is compiled deterministically from templates
3. All automations deployed with full audit trail
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002_add_hybrid_flow_tables"
down_revision: str | None = "001_add_automation_json"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _schema() -> str:
    """Schema this migration targets.

    The inspector resolves unqualified lookups against the connection's default
    schema (public), not the search_path the alembic env sets, so ask the server.
    """
    return op.get_bind().exec_driver_sql("SELECT current_schema()").scalar()


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names(schema=_schema()))


def _columns(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {col["name"] for col in inspector.get_columns(table, schema=_schema())}


def upgrade() -> None:
    # infrastructure/postgres/init-schemas.sql owns all three of these tables, so
    # on any database initialised from it they already exist and op.create_table
    # raised DuplicateTable. Create only what is genuinely missing.
    existing = _tables()

    if "plans" not in existing:
        op.create_table(
            "plans",
            sa.Column("plan_id", sa.String(), nullable=False),
            sa.Column("conversation_id", sa.String(), nullable=True),
            sa.Column("template_id", sa.String(), nullable=False),
            sa.Column("template_version", sa.Integer(), nullable=False),
            sa.Column("parameters", sa.JSON(), nullable=False),
            sa.Column("confidence", sa.Float(), nullable=False),
            sa.Column("clarifications_needed", sa.JSON(), nullable=True),
            sa.Column("safety_class", sa.String(), nullable=False),
            sa.Column("explanation", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("(CURRENT_TIMESTAMP)"),
                nullable=True,
            ),
            sa.PrimaryKeyConstraint("plan_id"),
        )
        op.create_index(op.f("ix_plans_plan_id"), "plans", ["plan_id"], unique=False)
        op.create_index(
            op.f("ix_plans_conversation_id"), "plans", ["conversation_id"], unique=False
        )
        op.create_index(op.f("ix_plans_template_id"), "plans", ["template_id"], unique=False)
        op.create_index(op.f("ix_plans_created_at"), "plans", ["created_at"], unique=False)

    # Create compiled_artifacts table
    if "compiled_artifacts" not in existing:
        op.create_table(
            "compiled_artifacts",
            sa.Column("compiled_id", sa.String(), nullable=False),
            sa.Column("plan_id", sa.String(), nullable=False),
            sa.Column("yaml", sa.Text(), nullable=False),
            sa.Column("human_summary", sa.Text(), nullable=False),
            sa.Column("diff_summary", sa.JSON(), nullable=True),
            sa.Column("risk_notes", sa.JSON(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("(CURRENT_TIMESTAMP)"),
                nullable=True,
            ),
            sa.ForeignKeyConstraint(
                ["plan_id"],
                ["plans.plan_id"],
            ),
            sa.PrimaryKeyConstraint("compiled_id"),
        )
        op.create_index(
            op.f("ix_compiled_artifacts_compiled_id"),
            "compiled_artifacts",
            ["compiled_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_compiled_artifacts_plan_id"), "compiled_artifacts", ["plan_id"], unique=False
        )
        op.create_index(
            op.f("ix_compiled_artifacts_created_at"),
            "compiled_artifacts",
            ["created_at"],
            unique=False,
        )

    # Create deployments table
    if "deployments" not in existing:
        op.create_table(
            "deployments",
            sa.Column("deployment_id", sa.String(), nullable=False),
            sa.Column("compiled_id", sa.String(), nullable=False),
            sa.Column("ha_automation_id", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("approved_by", sa.String(), nullable=True),
            sa.Column("ui_source", sa.String(), nullable=True),
            sa.Column(
                "deployed_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("(CURRENT_TIMESTAMP)"),
                nullable=True,
            ),
            sa.Column("audit_data", sa.JSON(), nullable=True),
            sa.ForeignKeyConstraint(
                ["compiled_id"],
                ["compiled_artifacts.compiled_id"],
            ),
            sa.PrimaryKeyConstraint("deployment_id"),
        )
        op.create_index(
            op.f("ix_deployments_deployment_id"), "deployments", ["deployment_id"], unique=False
        )
        op.create_index(
            op.f("ix_deployments_compiled_id"), "deployments", ["compiled_id"], unique=False
        )
        op.create_index(
            op.f("ix_deployments_ha_automation_id"),
            "deployments",
            ["ha_automation_id"],
            unique=False,
        )
        op.create_index(op.f("ix_deployments_status"), "deployments", ["status"], unique=False)
        op.create_index(
            op.f("ix_deployments_deployed_at"), "deployments", ["deployed_at"], unique=False
        )

    # Add foreign key columns to suggestions table (optional, for linking)
    # Check if columns exist first
    suggestions_columns = _columns("suggestions")

    if "plan_id" not in suggestions_columns:
        op.add_column("suggestions", sa.Column("plan_id", sa.String(), nullable=True))
        op.create_index(op.f("ix_suggestions_plan_id"), "suggestions", ["plan_id"], unique=False)

    if "compiled_id" not in suggestions_columns:
        op.add_column("suggestions", sa.Column("compiled_id", sa.String(), nullable=True))
        op.create_index(
            op.f("ix_suggestions_compiled_id"), "suggestions", ["compiled_id"], unique=False
        )

    if "deployment_id" not in suggestions_columns:
        op.add_column("suggestions", sa.Column("deployment_id", sa.String(), nullable=True))
        op.create_index(
            op.f("ix_suggestions_deployment_id"), "suggestions", ["deployment_id"], unique=False
        )


def downgrade() -> None:
    # Mirror of upgrade: touch only what is actually there. The explicit
    # drop_index calls that used to precede each drop_table are gone — dropping
    # a table takes its indexes with it, and naming them explicitly fails on a
    # database where init-schemas.sql created the table under its own index
    # names. Likewise for the columns: dropping one drops its index.
    existing = _tables()
    suggestions_columns = _columns("suggestions") if "suggestions" in existing else set()

    for column in ("deployment_id", "compiled_id", "plan_id"):
        if column in suggestions_columns:
            op.drop_column("suggestions", column)

    for table in ("deployments", "compiled_artifacts", "plans"):
        if table in existing:
            op.drop_table(table)
