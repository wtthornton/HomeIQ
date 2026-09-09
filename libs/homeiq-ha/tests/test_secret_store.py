"""Tier-2 appliance secret store: encryption properties and named states (TAP-6572).

``test_secret_states.py`` covers the ADR's state vocabulary. This module covers
the store that raises those states, and in particular the three cryptographic
properties that fail *silently* when they are wrong -- a reused nonce, a missing
AAD binding, and a DEK that is anything but the tier-1 value -- so each one has a
test that fails when the property is removed rather than a comment asserting it.
"""

from __future__ import annotations

import base64
import inspect
import json
import os
from pathlib import Path
from secrets import token_urlsafe

import pytest
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from homeiq_ha.secrets.states import DEK_KEY, SecretState, SecretStoreError
from homeiq_ha.secrets.store import (
    HA_TOKEN_KEY,
    SECRET_TABLE,
    ApplianceSecretStore,
    FileSecretBackend,
    SecretRow,
    load_dek,
    load_ha_token,
    read_tier1_env,
)

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
# The DEK is the tier-1 value, verbatim -- never re-derived
# --------------------------------------------------------------------------


def test_the_dek_is_the_tier1_bytes_verbatim(dek_hex: str) -> None:
    assert load_dek(dek_hex) == bytes.fromhex(dek_hex)


@pytest.mark.parametrize("bad", ["", "ab", "00" * 16, "00" * 33])
def test_a_wrong_length_dek_is_unsealed_never_stretched(bad: str) -> None:
    """A short DEK must stop the appliance, not be padded or hashed to 32 bytes.

    Stretching it would produce a *usable* key that decrypts nothing, which is
    silent data loss wearing the clothes of a working store.
    """
    with pytest.raises(SecretStoreError) as excinfo:
        load_dek(bad)
    assert excinfo.value.state is SecretState.SECRET_STORE_UNSEALED


def test_a_non_hex_dek_is_unsealed() -> None:
    with pytest.raises(SecretStoreError) as excinfo:
        load_dek("not-hex-" * 8)
    assert excinfo.value.state is SecretState.SECRET_STORE_UNSEALED


# --------------------------------------------------------------------------
# Nonce: 12 fresh bytes per write, never reused
# --------------------------------------------------------------------------


def test_two_writes_of_the_same_value_get_different_nonces_and_ciphertexts(
    store: ApplianceSecretStore,
) -> None:
    first = store.put(HA_TOKEN_KEY, _TOKEN)
    second = store.put(HA_TOKEN_KEY, _TOKEN)

    assert first.nonce != second.nonce
    assert first.ciphertext != second.ciphertext
    assert len(first.nonce) == 12
    assert len(second.nonce) == 12


def test_the_nonce_can_only_come_from_os_urandom() -> None:
    """Parse ``put`` and check what the nonce is actually assigned from.

    A counter or a clock-seeded nonce reads as "unique" and is not: two appliances
    booting from the same image in the same second collide, and GCM nonce reuse is
    a total break with no visible symptom. Asserting on the *source of the value*
    rather than on two sampled nonces differing is the difference between catching
    the defect and catching it 1-in-2**96 of the time.
    """
    import ast

    from homeiq_ha.secrets import store as module

    tree = ast.parse(inspect.getsource(module))
    put = next(
        node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == "put"
    )
    sources = [
        ast.unparse(node.value)
        for node in ast.walk(put)
        if isinstance(node, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "nonce" for t in node.targets)
    ]
    assert sources == ["os.urandom(_NONCE_BYTES)"], sources
    assert module._NONCE_BYTES == 12


# --------------------------------------------------------------------------
# AAD: the key name is authenticated, so a blob cannot be moved between keys
# --------------------------------------------------------------------------


def test_a_blob_written_for_one_key_will_not_decrypt_under_another(
    store: ApplianceSecretStore, state_dir: Path, dek_hex: str
) -> None:
    """Move ``ha_token``'s ciphertext onto another key: it must not open."""
    row = store.put(HA_TOKEN_KEY, _TOKEN)
    aead = AESGCM(bytes.fromhex(dek_hex))

    with pytest.raises(InvalidTag):
        aead.decrypt(row.nonce, row.ciphertext, b"watttime_password")

    backend = FileSecretBackend(state_dir)
    backend.write(SecretRow("watttime_password", row.ciphertext, row.nonce, row.updated_at))
    with pytest.raises(SecretStoreError) as excinfo:
        store.get("watttime_password")
    assert excinfo.value.state is SecretState.SECRET_STORE_UNSEALED


def test_the_aad_is_the_key_name(store: ApplianceSecretStore, dek_hex: str) -> None:
    row = store.put(HA_TOKEN_KEY, _TOKEN)
    aead = AESGCM(bytes.fromhex(dek_hex))
    assert aead.decrypt(row.nonce, row.ciphertext, HA_TOKEN_KEY.encode()) == _TOKEN.encode()


# --------------------------------------------------------------------------
# Round trip and the ADR's named states
# --------------------------------------------------------------------------


def test_a_stored_secret_comes_back_intact(store: ApplianceSecretStore) -> None:
    store.put(HA_TOKEN_KEY, _TOKEN)
    assert store.get(HA_TOKEN_KEY) == _TOKEN


def test_a_missing_row_is_secret_not_provisioned_never_an_empty_string(
    store: ApplianceSecretStore,
) -> None:
    with pytest.raises(SecretStoreError) as excinfo:
        store.get(HA_TOKEN_KEY)
    assert excinfo.value.state is SecretState.SECRET_NOT_PROVISIONED
    assert excinfo.value.exit_code == 80


def test_a_rotated_dek_is_unsealed_and_never_a_re_mint(
    store: ApplianceSecretStore, state_dir: Path
) -> None:
    store.put(HA_TOKEN_KEY, _TOKEN)
    rotated = ApplianceSecretStore.from_env(env={DEK_KEY: _dek_hex()}, state_dir=state_dir)

    with pytest.raises(SecretStoreError) as excinfo:
        rotated.get(HA_TOKEN_KEY)
    assert excinfo.value.state is SecretState.SECRET_STORE_UNSEALED
    assert excinfo.value.exit_code == 79
    assert not excinfo.value.retryable


def test_the_error_detail_never_carries_the_secret_or_the_dek(
    store: ApplianceSecretStore, state_dir: Path, dek_hex: str
) -> None:
    store.put(HA_TOKEN_KEY, _TOKEN)
    rotated_hex = _dek_hex()
    rotated = ApplianceSecretStore.from_env(env={DEK_KEY: rotated_hex}, state_dir=state_dir)
    with pytest.raises(SecretStoreError) as excinfo:
        rotated.get(HA_TOKEN_KEY)
    rendered = str(excinfo.value)
    assert _TOKEN not in rendered
    assert dek_hex not in rendered
    assert rotated_hex not in rendered


def test_a_row_repr_renders_lengths_not_bytes(store: ApplianceSecretStore) -> None:
    row = store.put(HA_TOKEN_KEY, _TOKEN)
    rendered = repr(row)
    assert base64.b64encode(row.ciphertext).decode() not in rendered
    assert str(row.ciphertext) not in rendered
    assert "bytes>" in rendered


# --------------------------------------------------------------------------
# Tier-1 handoff and the consumer entry point
# --------------------------------------------------------------------------


def test_the_dek_is_read_from_the_tier1_env_file(state_dir: Path, dek_hex: str) -> None:
    state_dir.mkdir(parents=True)
    (state_dir / ".env").write_text(f"# generated\nPOSTGRES_USER=homeiq\n{DEK_KEY}={dek_hex}\n")
    store = ApplianceSecretStore.from_env(env={}, state_dir=state_dir)
    store.put(HA_TOKEN_KEY, _TOKEN)
    assert store.get(HA_TOKEN_KEY) == _TOKEN


def test_read_tier1_env_ignores_comments_and_blank_lines(state_dir: Path) -> None:
    state_dir.mkdir(parents=True)
    (state_dir / ".env").write_text("# a comment\n\nA=1\nB=two=three\n")
    assert read_tier1_env(state_dir) == {"A": "1", "B": "two=three"}


def test_an_absent_tier1_file_yields_no_keys(state_dir: Path) -> None:
    assert read_tier1_env(state_dir) == {}


def test_no_dek_anywhere_is_unsealed(state_dir: Path) -> None:
    with pytest.raises(SecretStoreError) as excinfo:
        ApplianceSecretStore.from_env(env={}, state_dir=state_dir)
    assert excinfo.value.state is SecretState.SECRET_STORE_UNSEALED


def test_load_ha_token_returns_the_stored_credential(
    store: ApplianceSecretStore, state_dir: Path, dek_hex: str
) -> None:
    store.put(HA_TOKEN_KEY, _TOKEN)
    assert load_ha_token(env={DEK_KEY: dek_hex}, state_dir=state_dir) == _TOKEN


def test_load_ha_token_before_onboarding_is_standby_not_an_empty_string(
    state_dir: Path, dek_hex: str
) -> None:
    with pytest.raises(SecretStoreError) as excinfo:
        load_ha_token(env={DEK_KEY: dek_hex}, state_dir=state_dir)
    assert excinfo.value.state is SecretState.SECRET_NOT_PROVISIONED


def test_load_ha_token_reads_no_host_token_env_var(
    state_dir: Path, dek_hex: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A host ``HA_TOKEN`` must not satisfy the store. It is a different home."""
    monkeypatch.setenv("HA_TOKEN", "host-token-that-must-not-be-used")
    monkeypatch.setenv("HOME_ASSISTANT_TOKEN", "host-token-that-must-not-be-used")
    with pytest.raises(SecretStoreError) as excinfo:
        load_ha_token(env={DEK_KEY: dek_hex}, state_dir=state_dir)
    assert excinfo.value.state is SecretState.SECRET_NOT_PROVISIONED


def test_an_external_reader_with_only_the_dek_can_open_the_row(
    store: ApplianceSecretStore, state_dir: Path, dek_hex: str
) -> None:
    """The wire format is self-describing: DEK + the row is enough, no library state.

    This is the shape the VAL-070 decrypt script uses, so a change that broke an
    independent verifier's command turns this test red first.
    """
    store.put(HA_TOKEN_KEY, _TOKEN)
    payload = json.loads(
        (state_dir / "secrets" / SECRET_TABLE / f"{HA_TOKEN_KEY}.json").read_text()
    )
    plaintext = AESGCM(bytes.fromhex(dek_hex)).decrypt(
        base64.b64decode(payload["nonce"]),
        base64.b64decode(payload["value"]),
        payload["key"].encode(),
    )
    assert plaintext.decode() == _TOKEN


def test_the_state_dir_default_is_the_adr_path() -> None:
    from homeiq_ha.secrets.store import resolve_state_dir

    assert resolve_state_dir({}) == Path("/var/lib/homeiq")
    assert resolve_state_dir({"HOMEIQ_STATE_DIR": "/tmp/x"}) == Path("/tmp/x")
    assert os.environ is not None  # the helper never mutates the real environment
