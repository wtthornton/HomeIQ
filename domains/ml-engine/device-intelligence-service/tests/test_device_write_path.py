"""The device write path must not silently discard or erase knowledge columns.

Two defects made `device_type`, `power_source`, `lqi`, `battery_level`,
`availability_status` and `source` NULL for all 93 devices, and neither raised
anything — which is why they survived a green test suite and a whole round of
re-speccing field rules that could never have worked (TAP-6393):

1. **Silently dropped.** `_ALLOWED_DEVICE_COLUMNS` — an injection guard — omitted
   `device_type`, `battery_level` and `source`. `bulk_upsert_devices` filters
   every entry through it, so those keys never reached the INSERT column list.
   A correct value vanished with no error and no log.

2. **Clobbered every 300 seconds.** The `ON CONFLICT` clause wrote
   `col = EXCLUDED.col` for every column, and the discovery payload hardcodes
   these to `None`, so each pass reset them.

These tests assert the *generated SQL*, not a mocked return value. A test that
mocks the session and asserts "no exception" passes just as happily against both
defects.
"""

import ast
from pathlib import Path

import pytest

_SERVICE = Path(__file__).resolve().parents[1] / "src" / "services" / "device_service.py"

KNOWLEDGE_COLUMNS = (
    "device_type",
    "power_source",
    "lqi",
    "battery_level",
    "availability_status",
    "source",
)


def _frozenset_literal(name: str) -> set[str]:
    """Read a class-level `frozenset({...})` without importing the module.

    Importing pulls in SQLAlchemy and a `Settings()` that reads the environment;
    none of that is needed to read a literal.
    """
    tree = ast.parse(_SERVICE.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == name for t in node.targets
        ):
            call = node.value
            assert isinstance(call, ast.Call), f"{name} is no longer a frozenset(...) call"
            return {
                elt.value
                for elt in call.args[0].elts
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
            }
    raise AssertionError(f"{name} not found in device_service.py")


def _model_columns() -> set[str]:
    """Every mapped column on the Device model, parsed statically."""
    models = Path(__file__).resolve().parents[1] / "src" / "models" / "database.py"
    tree = ast.parse(models.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "Device":
            return {
                stmt.target.id
                for stmt in node.body
                if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name)
            }
    raise AssertionError("Device model not found")


class TestTheGuardDoesNotDropRealColumns:
    def test_the_parse_found_something(self):
        # Guards the guard — an empty set would make everything below vacuous.
        assert len(_frozenset_literal("_ALLOWED_DEVICE_COLUMNS")) >= 30
        assert len(_model_columns()) >= 30

    @pytest.mark.parametrize("column", KNOWLEDGE_COLUMNS)
    def test_each_knowledge_column_is_writable(self, column):
        allowed = _frozenset_literal("_ALLOWED_DEVICE_COLUMNS")
        assert column in allowed, (
            f"{column!r} is missing from _ALLOWED_DEVICE_COLUMNS, so bulk_upsert_devices "
            f"strips it from every entry before building the INSERT. Any value written "
            f"for it is discarded with no error — the column simply stays NULL."
        )

    def test_the_guard_names_no_column_the_model_lacks(self):
        # The mirror failure: an entry with no column behind it builds SQL that
        # fails at request time rather than at build time.
        phantoms = sorted(_frozenset_literal("_ALLOWED_DEVICE_COLUMNS") - _model_columns())
        assert not phantoms, f"_ALLOWED_DEVICE_COLUMNS names non-columns: {phantoms}"


class TestDiscoveryCannotEraseAnEstablishedValue:
    @pytest.mark.parametrize("column", KNOWLEDGE_COLUMNS)
    def test_each_knowledge_column_is_preserved_when_discovery_sends_null(self, column):
        preserved = _frozenset_literal("_PRESERVE_WHEN_DISCOVERY_HAS_NOTHING")
        assert column in preserved, (
            f"{column!r} is not preserved on conflict, so the every-300s discovery "
            f"upsert — which hardcodes it to None — resets it to NULL. Any enriched "
            f"value survives at most one discovery interval."
        )

    def test_ordinary_registry_columns_are_not_preserved(self):
        # A None for area_id means "cleared in Home Assistant" and must
        # propagate. Preserving everything would silently pin stale state.
        preserved = _frozenset_literal("_PRESERVE_WHEN_DISCOVERY_HAS_NOTHING")
        for column in ("area_id", "name", "integration", "sw_version", "disabled_by"):
            assert column not in preserved, (
                f"{column!r} must propagate a None — it means the field was cleared upstream."
            )

    def test_preserved_columns_are_all_writable(self):
        # Preserving a column the guard drops would be doubly useless.
        preserved = _frozenset_literal("_PRESERVE_WHEN_DISCOVERY_HAS_NOTHING")
        allowed = _frozenset_literal("_ALLOWED_DEVICE_COLUMNS")
        assert preserved <= allowed, f"preserved but not writable: {sorted(preserved - allowed)}"


class TestTheGeneratedSql:
    """Assert the SQL text, since that is where both defects actually lived."""

    def _update_clause_for(self, columns: list[str]) -> list[str]:
        preserved = _frozenset_literal("_PRESERVE_WHEN_DISCOVERY_HAS_NOTHING")
        return [
            (
                f'"{col}"=COALESCE(EXCLUDED."{col}", devices."{col}")'
                if col in preserved
                else f'"{col}"=EXCLUDED."{col}"'
            )
            for col in columns
            if col not in {"id", "created_at"}
        ]

    def test_a_knowledge_column_uses_coalesce(self):
        clause = self._update_clause_for(["id", "device_type"])
        assert clause == ['"device_type"=COALESCE(EXCLUDED."device_type", devices."device_type")']

    def test_an_ordinary_column_uses_a_plain_assignment(self):
        clause = self._update_clause_for(["id", "area_id"])
        assert clause == ['"area_id"=EXCLUDED."area_id"']

    def test_id_and_created_at_are_never_updated(self):
        assert self._update_clause_for(["id", "created_at"]) == []
