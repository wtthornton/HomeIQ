"""Add automation JSON columns

Revision ID: 001_add_automation_json
Revises:
Create Date: 2025-01-XX XX:XX:XX

Adds HomeIQ JSON Automation format support to suggestions and
automation_versions tables.

This migration used to interrogate SQLite's catalog directly — `SELECT name
FROM sqlite_master` and `PRAGMA table_info(...)` — neither of which exists on
PostgreSQL, so `alembic upgrade head` died with UndefinedTable: relation
"sqlite_master" does not exist. HomeIQ runs on PostgreSQL; the SQLite path is
gone, and the same questions are now asked through SQLAlchemy's inspector,
which is backend-agnostic.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001_add_automation_json"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = ("suggestions", "automation_versions")
NEW_COLUMNS: tuple[tuple[str, sa.types.TypeEngine], ...] = (
    ("automation_json", sa.JSON()),
    ("ha_version", sa.String()),
    ("json_schema_version", sa.String()),
)


def _schema() -> str:
    """The schema this migration runs against.

    The inspector resolves an unqualified get_table_names() against the
    connection's *default* schema, which is public — not the search_path the
    alembic env sets. Asking the server for current_schema() gets the one the
    tables actually live in (automation, here).
    """
    return op.get_bind().exec_driver_sql("SELECT current_schema()").scalar()


def _existing_tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names(schema=_schema()))


def _columns_of(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {col["name"] for col in inspector.get_columns(table, schema=_schema())}


def upgrade() -> None:
    # infrastructure/postgres/init-schemas.sql owns these tables; this migration
    # only adds columns to them. It deliberately does not create them: the old
    # Base.metadata.create_all() fallback tried to build every table in the
    # metadata and died on `relation "plans" already exists`.
    existing = _existing_tables()

    for table in TABLES:
        if table not in existing:
            continue
        columns = _columns_of(table)
        for name, column_type in NEW_COLUMNS:
            if name not in columns:
                op.add_column(table, sa.Column(name, column_type, nullable=True))


def downgrade() -> None:
    existing = _existing_tables()

    for table in TABLES:
        if table not in existing:
            continue
        columns = _columns_of(table)
        for name, _column_type in reversed(NEW_COLUMNS):
            if name in columns:
                op.drop_column(table, name)
