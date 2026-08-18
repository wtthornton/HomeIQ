"""The per-connection ``SET search_path`` must run outside a transaction.

Inside the adapter's implicit transaction the SET is undone by the pool's
rollback-on-return, and unqualified table names then resolve through the role
default search_path into other services' schemas.
"""

from unittest.mock import MagicMock

import pytest
from homeiq_data.database_pool import apply_search_path, create_pg_engine


def _conn(initial_autocommit=False):
    conn = MagicMock()
    conn.autocommit = initial_autocommit
    cursor = MagicMock()
    conn.cursor.return_value = cursor
    return conn, cursor


def test_search_path_is_set_with_autocommit_and_restored():
    conn, cursor = _conn(initial_autocommit=False)
    states = []
    cursor.execute.side_effect = lambda sql: states.append((sql, conn.autocommit))

    apply_search_path(conn, "devices")

    assert states == [("SET search_path TO devices, public", True)]
    assert conn.autocommit is False  # restored to the adapter's default
    cursor.close.assert_called_once()


def test_autocommit_restored_even_when_set_fails():
    conn, cursor = _conn(initial_autocommit=False)
    cursor.execute.side_effect = RuntimeError("boom")
    with pytest.raises(RuntimeError):
        apply_search_path(conn, "devices")
    assert conn.autocommit is False
    cursor.close.assert_called_once()


def test_engine_registers_connect_listener_that_applies_search_path(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "homeiq_data.database_pool.apply_search_path", lambda _conn, schema: calls.append(schema)
    )
    engine = create_pg_engine("postgresql+asyncpg://u:p@localhost/db", schema="devices")
    # Our listener sits on the pool's connect hook next to the dialect's own; fire just ours.
    ours = [
        fn for fn in engine.sync_engine.pool.dispatch.connect if fn.__name__ == "set_search_path"
    ]
    assert len(ours) == 1
    ours[0](MagicMock(), MagicMock())
    assert calls == ["devices"]


def test_schema_name_is_validated():
    with pytest.raises(ValueError):
        create_pg_engine("postgresql+asyncpg://u:p@localhost/db", schema="devices; DROP TABLE x")


def test_validate_schema_name_public_helper():
    from homeiq_data import validate_schema_name

    assert validate_schema_name("patterns") == "patterns"
    with pytest.raises(ValueError):
        validate_schema_name("patterns; drop table x")
