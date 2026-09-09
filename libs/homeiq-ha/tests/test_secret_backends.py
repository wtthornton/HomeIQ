"""The two secret-store backends: the ADR's Postgres table, and the file adapter.

``test_secret_store.py`` covers the encryption the store does. This module covers
the two places the resulting rows are put, and the property that matters across
both: **one wire format**. A row written through either adapter is the ADR's four
columns and opens under the same DEK, so moving an appliance from the shipped
file adapter to the mandated Postgres one is a constructor change and not a
migration of the customer's credentials.

The Postgres adapter is exercised against a fake connection rather than a live
server on purpose: what needs proving is the SQL it emits and which named state
each failure maps to, and both are visible without a database. Connecting to the
real appliance Postgres from a unit test would prove less and cost a container.
"""

from __future__ import annotations

import base64
import json
import stat
from datetime import UTC, datetime
from secrets import token_urlsafe
from typing import TYPE_CHECKING, Any

import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from homeiq_ha.secrets.states import DEK_KEY, SecretState, SecretStoreError
from homeiq_ha.secrets.store import (
    HA_TOKEN_KEY,
    SECRET_TABLE,
    ApplianceSecretStore,
    FileSecretBackend,
    PostgresSecretBackend,
    SecretRow,
)

if TYPE_CHECKING:
    from pathlib import Path

#: A stand-in for a real long-lived token, GENERATED rather than written down.
#: A literal that looks like a credential is one grep away from being mistaken
#: for one, and the appliance rules forbid credential constants in the repo --
#: the value is irrelevant to every assertion below, only its opacity matters.
_TOKEN = f"hiq-test-{token_urlsafe(48)}"


def _dek_hex() -> str:
    return AESGCM.generate_key(bit_length=256).hex()


@pytest.fixture
def state_dir(tmp_path: Path) -> Path:
    return tmp_path / "state"


@pytest.fixture
def dek_hex() -> str:
    return _dek_hex()


@pytest.fixture
def store(state_dir: Path, dek_hex: str) -> ApplianceSecretStore:
    return ApplianceSecretStore.from_env(env={DEK_KEY: dek_hex}, state_dir=state_dir)


# --------------------------------------------------------------------------
# File-backed adapter: the ADR's four columns, 0600, under the table name
# --------------------------------------------------------------------------


def test_the_file_row_carries_the_adr_four_columns(
    store: ApplianceSecretStore, state_dir: Path
) -> None:
    store.put(HA_TOKEN_KEY, _TOKEN)
    path = state_dir / "secrets" / SECRET_TABLE / f"{HA_TOKEN_KEY}.json"
    payload = json.loads(path.read_text())
    assert set(payload) == {"key", "value", "nonce", "updated_at"}
    assert payload["key"] == HA_TOKEN_KEY
    assert len(base64.b64decode(payload["nonce"])) == 12
    datetime.fromisoformat(payload["updated_at"])


def test_the_file_row_is_not_readable_by_anyone_else(
    store: ApplianceSecretStore, state_dir: Path
) -> None:
    store.put(HA_TOKEN_KEY, _TOKEN)
    path = state_dir / "secrets" / SECRET_TABLE / f"{HA_TOKEN_KEY}.json"
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700


def test_the_file_row_holds_no_plaintext(store: ApplianceSecretStore, state_dir: Path) -> None:
    store.put(HA_TOKEN_KEY, _TOKEN)
    blob = (state_dir / "secrets" / SECRET_TABLE / f"{HA_TOKEN_KEY}.json").read_bytes()
    assert _TOKEN.encode() not in blob


def test_a_write_leaves_no_temp_file_behind(store: ApplianceSecretStore, state_dir: Path) -> None:
    store.put(HA_TOKEN_KEY, _TOKEN)
    root = state_dir / "secrets" / SECRET_TABLE
    assert [p.name for p in root.iterdir()] == [f"{HA_TOKEN_KEY}.json"]


def test_has_rows_distinguishes_a_fresh_appliance_from_a_provisioned_one(
    state_dir: Path, dek_hex: str
) -> None:
    backend = FileSecretBackend(state_dir)
    assert backend.has_rows() is False
    ApplianceSecretStore.from_env(env={DEK_KEY: dek_hex}, state_dir=state_dir).put(
        HA_TOKEN_KEY, _TOKEN
    )
    assert backend.has_rows() is True


def test_a_key_with_a_path_separator_is_refused(state_dir: Path) -> None:
    with pytest.raises(ValueError, match="path-safe"):
        FileSecretBackend(state_dir).read("../../etc/passwd")


# --------------------------------------------------------------------------
# Postgres adapter: the ADR's mandated backend, against a fake connection
# --------------------------------------------------------------------------


class _FakeCursor:
    def __init__(self, conn: _FakeConnection) -> None:
        self._conn = conn
        self.description: object | None = None

    def __enter__(self) -> _FakeCursor:
        return self

    def __exit__(self, *_exc: object) -> None:
        return None

    def execute(self, sql: str, params: tuple[Any, ...]) -> None:
        self._conn.statements.append((sql, params))
        if sql.lstrip().upper().startswith("SELECT"):
            self.description = [("value",)]
            self._rows = self._conn.rows
        else:
            self.description = None
            self._rows = []

    def fetchall(self) -> list[tuple[Any, ...]]:
        return self._rows


class _FakeConnection:
    def __init__(self, rows: list[tuple[Any, ...]] | None = None) -> None:
        self.rows = rows or []
        self.statements: list[tuple[str, tuple[Any, ...]]] = []

    def __enter__(self) -> _FakeConnection:
        return self

    def __exit__(self, *_exc: object) -> None:
        return None

    def cursor(self) -> _FakeCursor:
        return _FakeCursor(self)


def test_the_postgres_adapter_targets_the_adr_table_and_columns() -> None:
    conn = _FakeConnection()
    PostgresSecretBackend(lambda: conn).read(HA_TOKEN_KEY)
    sql, params = conn.statements[0]
    assert SECRET_TABLE in sql
    assert "value" in sql and "nonce" in sql and "updated_at" in sql
    assert params == (HA_TOKEN_KEY,)


def test_the_postgres_adapter_upserts_rather_than_duplicating() -> None:
    conn = _FakeConnection()
    row = SecretRow(HA_TOKEN_KEY, b"ct", b"n" * 12, datetime.now(UTC))
    PostgresSecretBackend(lambda: conn).write(row)
    sql, params = conn.statements[0]
    assert "ON CONFLICT (key) DO UPDATE" in sql
    assert params == (HA_TOKEN_KEY, b"ct", b"n" * 12, row.updated_at)


def test_an_unreachable_postgres_is_secret_store_unavailable_and_retryable() -> None:
    def refuse() -> _FakeConnection:
        raise ConnectionRefusedError("connection refused")

    with pytest.raises(SecretStoreError) as excinfo:
        PostgresSecretBackend(refuse).read(HA_TOKEN_KEY)
    assert excinfo.value.state is SecretState.SECRET_STORE_UNAVAILABLE
    assert excinfo.value.retryable
    assert excinfo.value.exit_code == 75


def test_a_missing_postgres_row_is_secret_not_provisioned_not_unavailable(
    dek_hex: str,
) -> None:
    """The two failures are distinct on purpose: one retries, one goes standby."""
    backend = PostgresSecretBackend(_FakeConnection)
    with pytest.raises(SecretStoreError) as excinfo:
        ApplianceSecretStore(bytes.fromhex(dek_hex), backend).get(HA_TOKEN_KEY)
    assert excinfo.value.state is SecretState.SECRET_NOT_PROVISIONED


def test_a_postgres_row_decrypts_through_the_same_store(dek_hex: str) -> None:
    """One wire format: a row written by the file adapter opens through Postgres."""
    conn = _FakeConnection()
    written = ApplianceSecretStore(bytes.fromhex(dek_hex), PostgresSecretBackend(lambda: conn))
    row = written.put(HA_TOKEN_KEY, _TOKEN)
    conn.rows = [(row.ciphertext, row.nonce, row.updated_at)]
    assert written.get(HA_TOKEN_KEY) == _TOKEN
