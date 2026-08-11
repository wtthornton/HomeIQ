"""
Tests for alembic_helpers schema-name handling.

These exist because every schema name in this module reaches PostgreSQL by
string interpolation, and it is not optional that it does: ``SET search_path``
and ``CREATE SCHEMA`` are utility statements, which PostgreSQL parses before
bind parameters are substituted. Passing the schema as a bound value makes the
server reject the statement with ``syntax error at or near "$1"`` before a
single migration runs — which is exactly how 12 of the 13 alembic services in
this repo were failing.

Interpolation is therefore the fix, and the validator is what keeps it safe.
"""

import pytest
from homeiq_data.alembic_helpers import _SCHEMA_NAME_RE, _validate_schema_name

# The nine schemas infrastructure/postgres/init-schemas.sql creates.
KNOWN_SCHEMAS = [
    "core",
    "automation",
    "agent",
    "blueprints",
    "energy",
    "devices",
    "memory",
    "patterns",
    "rag",
]


@pytest.mark.parametrize("schema", KNOWN_SCHEMAS)
def test_accepts_every_schema_the_repo_actually_uses(schema):
    assert _validate_schema_name(schema) == schema


@pytest.mark.parametrize(
    "schema",
    [
        "core; DROP SCHEMA public CASCADE",
        'core" ; --',
        "core, public; SELECT 1",
        "core public",
        "Core",  # uppercase would need quoting to round-trip
        "1core",  # identifiers cannot start with a digit
        "core-schema",
        "",
        "core'",
    ],
)
def test_rejects_anything_that_could_change_the_statement(schema):
    with pytest.raises(ValueError, match="Unsafe schema name"):
        _validate_schema_name(schema)


def test_accepted_names_cannot_carry_sql_metacharacters():
    """The property the interpolation sites depend on."""
    for schema in KNOWN_SCHEMAS:
        validated = _validate_schema_name(schema)
        assert not set(validated) & set("'\"; \t\n\\-()")
        assert _SCHEMA_NAME_RE.match(validated)
