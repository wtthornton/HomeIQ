"""Create the ha-setup-service tables and retire missing_env_vars.

Revision ID: 001
Revises:
Create Date: 2026-08-24

This is the first migration this service has ever had. Its five tables were
previously defined only as SQLAlchemy models — nothing created them. Not
``create_all``, which appears nowhere in the service; not
``infrastructure/postgres/init-schemas.sql``; not a migration. They exist on
long-lived instances because someone made them by hand, so a fresh install had
none of them and every write went to a table that was not there.

Every step is therefore conditional. The migration has to bring a brand-new
database up *and* adopt a database whose tables predate it, without failing on
either. ``CREATE TABLE`` on an existing table and ``DROP COLUMN`` on an absent
one are both errors, so each is guarded by an inspector check rather than
assumed.

``missing_env_vars`` is dropped here rather than in a later revision. It is
``NOT NULL`` with no server default, and Postgres checks NOT NULL *before* the
ON CONFLICT arbiter, so leaving it while the model no longer supplies it would
abort every upsert in the blocker refresh (TAP-6462).
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSON

revision = "001"
down_revision = None
branch_labels = None
depends_on = None

SCHEMA = "devices"


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(name: str) -> bool:
    return name in _inspector().get_table_names(schema=SCHEMA)


def _has_column(table: str, column: str) -> bool:
    if not _has_table(table):
        return False
    return column in {c["name"] for c in _inspector().get_columns(table, schema=SCHEMA)}


def _timestamp(name: str, *, nullable: bool = True) -> sa.Column:
    """A `now()`-defaulted timestamp column.

    ``nullable`` mirrors the model exactly. Most of these columns are nullable
    there; ``integration_blockers.first_seen`` and ``last_seen`` are not, and a
    migration that quietly created them nullable would reintroduce the
    model-versus-schema drift this revision exists to end.
    """
    return sa.Column(
        name, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=nullable
    )


def upgrade() -> None:
    if not _has_table("environment_health"):
        op.create_table(
            "environment_health",
            sa.Column("id", sa.Integer(), primary_key=True),
            _timestamp("timestamp"),
            sa.Column("health_score", sa.Integer(), nullable=False),
            sa.Column("ha_status", sa.String(), nullable=False),
            sa.Column("ha_version", sa.String()),
            sa.Column("integrations_status", JSON(), nullable=False),
            sa.Column("performance_metrics", JSON(), nullable=False),
            sa.Column("issues_detected", JSON()),
            schema=SCHEMA,
        )
        op.create_index(
            "ix_environment_health_timestamp", "environment_health", ["timestamp"], schema=SCHEMA
        )

    if not _has_table("integration_health"):
        op.create_table(
            "integration_health",
            sa.Column("id", sa.Integer(), primary_key=True),
            _timestamp("timestamp"),
            sa.Column("integration_name", sa.String(), nullable=False),
            sa.Column("integration_type", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("is_configured", sa.Boolean(), server_default=sa.false()),
            sa.Column("is_connected", sa.Boolean(), server_default=sa.false()),
            sa.Column("error_message", sa.String()),
            sa.Column("last_check", sa.DateTime(timezone=True)),
            sa.Column("check_details", JSON()),
            schema=SCHEMA,
        )
        op.create_index(
            "ix_integration_health_timestamp", "integration_health", ["timestamp"], schema=SCHEMA
        )
        op.create_index(
            "ix_integration_health_integration_name",
            "integration_health",
            ["integration_name"],
            schema=SCHEMA,
        )

    if not _has_table("performance_metrics"):
        op.create_table(
            "performance_metrics",
            sa.Column("id", sa.Integer(), primary_key=True),
            _timestamp("timestamp"),
            sa.Column("metric_type", sa.String(), nullable=False),
            sa.Column("metric_value", sa.Float(), nullable=False),
            sa.Column("component", sa.String()),
            # Named metric_metadata because `metadata` is reserved on the
            # SQLAlchemy declarative base.
            sa.Column("metric_metadata", JSON()),
            schema=SCHEMA,
        )
        op.create_index(
            "ix_performance_metrics_timestamp", "performance_metrics", ["timestamp"], schema=SCHEMA
        )
        op.create_index(
            "ix_performance_metrics_metric_type",
            "performance_metrics",
            ["metric_type"],
            schema=SCHEMA,
        )

    if not _has_table("setup_wizard_sessions"):
        op.create_table(
            "setup_wizard_sessions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("session_id", sa.String(), nullable=False, unique=True),
            sa.Column("integration_type", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("steps_completed", sa.Integer(), server_default="0"),
            sa.Column("total_steps", sa.Integer(), nullable=False),
            sa.Column("current_step", sa.String()),
            sa.Column("configuration", JSON()),
            sa.Column("error_log", JSON()),
            _timestamp("created_at"),
            sa.Column("updated_at", sa.DateTime(timezone=True)),
            sa.Column("completed_at", sa.DateTime(timezone=True)),
            schema=SCHEMA,
        )
        op.create_index(
            "ix_setup_wizard_sessions_session_id",
            "setup_wizard_sessions",
            ["session_id"],
            unique=True,
            schema=SCHEMA,
        )

    if not _has_table("integration_blockers"):
        op.create_table(
            "integration_blockers",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("domain", sa.String(), nullable=False, unique=True),
            sa.Column("title", sa.String(), nullable=False),
            # Null means nothing is blocking it — the flow is fillable now.
            sa.Column("blocker_kind", sa.String()),
            sa.Column("evidence", sa.String(), nullable=False),
            sa.Column("flow_step", sa.String(), nullable=False),
            sa.Column("required_fields", JSON(), nullable=False),
            sa.Column("devices", JSON(), nullable=False),
            _timestamp("first_seen", nullable=False),
            _timestamp("last_seen", nullable=False),
            schema=SCHEMA,
        )
        op.create_index(
            "ix_integration_blockers_domain",
            "integration_blockers",
            ["domain"],
            unique=True,
            schema=SCHEMA,
        )
        op.create_index(
            "ix_integration_blockers_blocker_kind",
            "integration_blockers",
            ["blocker_kind"],
            schema=SCHEMA,
        )

    # Retired by TAP-6462. Only present on instances created before this
    # migration existed; a table created above never had it.
    if _has_column("integration_blockers", "missing_env_vars"):
        op.drop_column("integration_blockers", "missing_env_vars", schema=SCHEMA)


def downgrade() -> None:
    """Restore the retired column; the tables themselves are not dropped.

    Dropping five tables on a downgrade would discard an instance's entire
    setup history to undo a schema change. The column is restored with a
    server default so existing rows satisfy NOT NULL.
    """
    if _has_table("integration_blockers") and not _has_column(
        "integration_blockers", "missing_env_vars"
    ):
        op.add_column(
            "integration_blockers",
            sa.Column("missing_env_vars", JSON(), nullable=False, server_default="[]"),
            schema=SCHEMA,
        )
