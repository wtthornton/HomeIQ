"""The database-management allowlist must not drift from the models.

`KNOWN_TABLES` is the SQL-injection guard for the database-management routes: a
table name from a request is only interpolated if it appears there. Drift breaks
it in both directions, and neither direction is loud.

* An entry with no table behind it is a name the guard admits and the database
  then rejects — a request-time `relation does not exist` in production rather
  than an error at build time. This is what dropping `zigbee_device_metadata`
  would have caused had its entry been left behind (TAP-6401).
* A real table missing from the list is unmanageable through the API. That fails
  safe, so it is not asserted here — the list is deliberately allowed to be a
  subset. Adding a table widens what a destructive endpoint can touch, and that
  should be a decision, not a side effect of a test.

The check is static: it parses `__tablename__` assignments out of the model
modules rather than importing them, so it needs no database, no environment and
no settings object, and it runs anywhere.
"""

import ast
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
_MODELS_DIR = _SRC / "models"


def _declared_tablenames() -> set[str]:
    """Every `__tablename__ = "..."` across the models package."""
    names: set[str] = set()
    for module in _MODELS_DIR.glob("*.py"):
        tree = ast.parse(module.read_text(encoding="utf-8"), filename=str(module))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            for target in node.targets:
                if (
                    isinstance(target, ast.Name)
                    and target.id == "__tablename__"
                    and isinstance(node.value, ast.Constant)
                    and isinstance(node.value.value, str)
                ):
                    names.add(node.value.value)
    return names


def _known_tables() -> set[str]:
    """`KNOWN_TABLES` from the API module, read without importing it.

    Importing would pull in FastAPI, SQLAlchemy and a `Settings()` that reads the
    environment; none of that is needed to read a literal set.
    """
    source = (_SRC / "api" / "database_management.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "KNOWN_TABLES" for t in node.targets
        ):
            # frozenset({...})
            call = node.value
            assert isinstance(call, ast.Call), "KNOWN_TABLES is no longer a frozenset(...) call"
            return {
                elt.value
                for elt in call.args[0].elts
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
            }
    raise AssertionError("KNOWN_TABLES not found in database_management.py")


def test_the_models_actually_declare_some_tables():
    # Guards the guard: if the AST walk silently found nothing, every assertion
    # below would pass vacuously over an empty set.
    declared = _declared_tablenames()
    assert len(declared) >= 10, f"only found {len(declared)} tablenames — the parse is wrong"


def test_the_allowlist_is_not_empty():
    assert _known_tables(), "KNOWN_TABLES parsed as empty — the parse is wrong"


def test_every_allowlisted_table_is_declared_by_a_model():
    declared = _declared_tablenames()
    phantoms = sorted(_known_tables() - declared)
    assert not phantoms, (
        f"KNOWN_TABLES names {phantoms}, which no model declares. An allowlist "
        f"entry with no table behind it fails at request time in production "
        f"instead of at build time. Remove the entry, or add the model."
    )


def test_the_dropped_zigbee_table_is_gone_from_both():
    # The specific drift this test was written after.
    assert "zigbee_device_metadata" not in _known_tables()
    assert "zigbee_device_metadata" not in _declared_tablenames()
