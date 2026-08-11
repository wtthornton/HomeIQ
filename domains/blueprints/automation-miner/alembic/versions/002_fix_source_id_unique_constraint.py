"""Fix source_id unique constraint to composite (source, source_id)

Revision ID: 002
Revises: 001
Create Date: 2025-01-20 12:00:00

This used to run through op.batch_alter_table, which is SQLite's
copy-table-and-swap workaround for a backend that cannot ALTER a constraint.
HomeIQ runs on PostgreSQL, which alters constraints in place, and recreating
the table would have been a needless rewrite of the whole corpus.

It also wrapped the inspection in `except Exception: pass`, so a failure to
read the catalogue was indistinguishable from "constraint absent" and the
migration would blindly try to add a constraint that was already there.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "community_automations"
CONSTRAINT = "uq_source_source_id"


def _schema() -> str:
    return op.get_bind().exec_driver_sql("SELECT current_schema()").scalar()


def _unique_constraints() -> dict[str, set[str]]:
    inspector = sa.inspect(op.get_bind())
    return {
        c["name"]: set(c["column_names"])
        for c in inspector.get_unique_constraints(TABLE, schema=_schema())
        if c.get("name")
    }


def upgrade() -> None:
    constraints = _unique_constraints()

    # init-schemas.sql already declares this as a composite constraint
    # (infrastructure/postgres/init-schemas.sql:465), so on a normal database
    # there is nothing to do.
    if constraints.get(CONSTRAINT) == {"source", "source_id"}:
        return

    if CONSTRAINT in constraints:
        op.drop_constraint(CONSTRAINT, TABLE, type_="unique")

    op.create_unique_constraint(CONSTRAINT, TABLE, ["source", "source_id"])


def downgrade() -> None:
    constraints = _unique_constraints()

    if CONSTRAINT in constraints:
        op.drop_constraint(CONSTRAINT, TABLE, type_="unique")

    op.create_unique_constraint(CONSTRAINT, TABLE, ["source_id"])
