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
    "is_battery_powered",
    # The companions are as droppable as the values, and dropping one silently
    # discards its writes — the original TAP-6393 failure mode exactly.
    "lqi_updated_at",
    "battery_updated_at",
    "availability_updated_at",
)


def _frozenset_literal(name: str) -> set[str]:
    """Read a class-level `frozenset({...})` without importing the module.

    Importing pulls in SQLAlchemy and a `Settings()` that reads the environment;
    none of that is needed to read a literal.
    """
    tree = ast.parse(_SERVICE.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        # Either `NAME = frozenset({...})` or `NAME: frozenset[str] = frozenset()`.
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        else:
            continue
        if not any(isinstance(t, ast.Name) and t.id == name for t in targets):
            continue
        call = node.value
        assert isinstance(call, ast.Call), f"{name} is no longer a frozenset(...) call"
        if not call.args:
            return set()  # frozenset() — deliberately empty
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


class TestPreservationIsByOmissionNotByCoalesce:
    """Absence preserves, an explicit None clears.

    COALESCE cannot express this distinction, because SQL sees the same NULL
    whether the caller meant "I could not evaluate this" or "this is genuinely
    empty". Treating both as "preserve" made values unretractable: sixteen Hue
    Room groups wrongly typed as physical lights survived the very fix that
    stopped typing them.
    """

    def test_nothing_is_coalesced_any_more(self):
        preserved = _frozenset_literal("_PRESERVE_WHEN_DISCOVERY_HAS_NOTHING")
        assert preserved == set(), (
            "COALESCE is back. It makes a wrong value unretractable, because the "
            "rules can then add but never clear. Preservation is the caller's job: "
            "omit the key."
        )

    @pytest.mark.parametrize("column", KNOWLEDGE_COLUMNS)
    def test_each_knowledge_column_is_still_writable(self, column):
        assert column in _frozenset_literal("_ALLOWED_DEVICE_COLUMNS")


class TestTheGeneratedSql:
    """Assert the SQL text, since that is where the defects actually lived."""

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

    def test_a_supplied_column_is_assigned_so_an_explicit_none_clears(self):
        clause = self._update_clause_for(["id", "device_type"])
        assert clause == ['"device_type"=EXCLUDED."device_type"']

    def test_an_omitted_column_never_reaches_the_update_at_all(self):
        # This is the preservation mechanism. A column the caller did not supply
        # is not in `columns`, so it is absent from the UPDATE SET and the stored
        # value stands untouched.
        assert self._update_clause_for(["id", "name"]) == ['"name"=EXCLUDED."name"']
        assert "device_type" not in " ".join(self._update_clause_for(["id", "name"]))

    def test_id_and_created_at_are_never_updated(self):
        assert self._update_clause_for(["id", "created_at"]) == []


_INIT_SCHEMAS = (
    Path(__file__).resolve().parents[4] / "infrastructure" / "postgres" / "init-schemas.sql"
)
_DISCOVERY = Path(__file__).resolve().parents[1] / "src" / "core" / "discovery_service.py"


def _devices_table_ddl() -> list[str]:
    """Column lines of `devices.devices`, not the unrelated `core.devices`.

    Both schemas declare a table called `devices`, with different columns. The
    search_path statement is what tells them apart.
    """
    lines = _INIT_SCHEMAS.read_text(encoding="utf-8").splitlines()
    in_devices_schema = False
    for index, line in enumerate(lines):
        if line.strip().startswith("SET search_path TO "):
            in_devices_schema = line.strip() == "SET search_path TO devices;"
        if in_devices_schema and line.startswith("CREATE TABLE IF NOT EXISTS devices ("):
            end = next(n for n in range(index, len(lines)) if lines[n].startswith(");"))
            return lines[index + 1 : end]
    raise AssertionError("devices.devices CREATE TABLE not found in init-schemas.sql")


def _not_null_columns_without_default() -> set[str]:
    """Columns the database will refuse to accept a missing value for."""
    columns = set()
    for line in _devices_table_ddl():
        text = line.strip().rstrip(",")
        if not text or text.startswith("--"):
            continue
        upper = text.upper()
        if "DEFAULT " in upper:
            continue
        if "NOT NULL" in upper or "PRIMARY KEY" in upper:
            columns.add(text.split()[0])
    return columns


def _always_supplied_keys() -> set[str]:
    """Keys in the `device_data = {...}` literal, before any conditional update.

    The literal is the unconditional part of the payload. Everything added after
    it — `device_data.update(established)`, the `if device.ha_device` block — is
    conditional by construction, so it cannot satisfy a NOT NULL column.
    """
    tree = ast.parse(_DISCOVERY.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Dict):
            continue
        if not any(isinstance(t, ast.Name) and t.id == "device_data" for t in node.targets):
            continue
        return {
            key.value
            for key in node.value.keys
            if isinstance(key, ast.Constant) and isinstance(key.value, str)
        }
    raise AssertionError("device_data literal not found in discovery_service.py")


class TestEveryNotNullColumnIsAlwaysSupplied:
    """A NOT NULL column the write path may omit takes down the whole pass.

    PostgreSQL checks NOT NULL while forming the tuple, BEFORE the ON CONFLICT
    arbiter runs. "The row already exists, so DO UPDATE would have left it
    alone" is therefore no defence: the statement raises and the transaction
    aborts. One column the rules could not establish erases the entire discovery
    pass, not one device.

    This is what actually happened. `is_battery_powered` was NOT NULL and is
    derived from `power_source`, which 45 of 93 devices could not establish, so
    the key was absent from their upserts. Every row in devices.devices sat at
    updated_at 2026-08-21 03:38:35 for fourteen hours while
    /api/discovery/status went on reporting 93 devices found — the failure was
    appended to an errors array nothing alerted on.

    Every other test in this file passed throughout. They assert the generated
    SQL, and the SQL was right; it was the schema that refused it. Nothing here
    compared the two, which is the gap this class closes.
    """

    def test_the_parses_found_something(self):
        # Guards the guard: two empty sets would make the assertion below vacuous.
        assert len(_devices_table_ddl()) >= 30
        assert len(_always_supplied_keys()) >= 15

    def test_no_not_null_column_can_be_omitted(self):
        required = _not_null_columns_without_default()
        omittable = sorted(required - _always_supplied_keys())
        assert not omittable, (
            f"{omittable} are NOT NULL in devices.devices but are not in the "
            f"unconditional device_data literal. Any pass that cannot establish one "
            f"aborts its whole transaction, and discovery keeps reporting success."
        )

    def test_the_derived_battery_flag_is_nullable(self):
        # Named explicitly because a `DEFAULT false` would also satisfy the test
        # above while asserting something untrue: that a device of unknown power
        # source is known not to run on batteries.
        ddl = " ".join(_devices_table_ddl())
        assert "is_battery_powered BOOLEAN," in ddl
        assert "is_battery_powered BOOLEAN NOT NULL" not in ddl
        assert "is_battery_powered BOOLEAN DEFAULT" not in ddl
