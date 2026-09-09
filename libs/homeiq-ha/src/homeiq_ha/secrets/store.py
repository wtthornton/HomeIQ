"""Tier-2 appliance secret store: AES-GCM rows under the tier-1 DEK (TAP-6572).

``docs/architecture/adr-appliance-secret-store.md`` (Accepted 2026-08-26) splits
the appliance's secrets on boot ordering. Tier 1 is a root-owned ``.env`` written
once by ``scripts/appliance/firstboot-secrets.sh``; it holds ``HOMEIQ_SECRET_DEK``.
Tier 2 is everything minted or entered *after* the stack is up -- the Home
Assistant long-lived token first among them -- and this module is tier 2.

What a row is
-------------
The ADR's table ``core.appliance_secret`` has four columns: ``key``, ``value``
(AES-GCM ciphertext), ``nonce`` (per-write, never reused) and ``updated_at``.
:class:`SecretRow` is that row, and the wire format is the same whichever backend
holds it, so a file-backed appliance and a Postgres-backed one are readable by the
same code and the same DEK.

Three properties are load-bearing, and each fails *silently* when it is wrong, so
each has a test that goes red when it is removed:

* **The DEK is the tier-1 value, verbatim.** ``bytes.fromhex(HOMEIQ_SECRET_DEK)``
  must be 32 bytes. A short, long or non-hex value is ``SecretStoreUnsealed`` --
  never a hash, a pad or a KDF over it. Re-deriving a key from a wrong one
  produces a store that opens under the wrong DEK, which is the whole failure.
* **The nonce is 12 fresh bytes per write.** ``os.urandom(12)``, stored beside the
  ciphertext. GCM nonce reuse leaks the XOR of the two plaintexts and lets the tag
  be forged, and nothing in the ciphertext reveals that it happened -- so there is
  no counter, no clock seed and no module-level nonce constant anywhere below.
* **The AAD is the key name.** A blob written for ``ha_token`` will not decrypt as
  ``watttime_password``: it raises ``InvalidTag``, reported as
  ``SecretStoreUnsealed``. Without the binding, anyone who can write the store
  could move one row's ciphertext onto another row's key and have it open cleanly
  under a different meaning.

Storage backend
---------------
The ADR mandates **Postgres** (``core.appliance_secret``), and
:class:`PostgresSecretBackend` is that adapter -- interface, SQL, and the ADR's
named states (``SecretStoreUnavailable`` on an unreachable server,
``SecretNotProvisioned`` on a missing row). What ships wired up for the appliance
first-boot path is :class:`FileSecretBackend`, which writes the identical rows
under ``$HOMEIQ_STATE_DIR/secrets/core.appliance_secret/``. Both satisfy
:class:`SecretBackend`, and the store does not know which one it holds.

Nothing here logs, reprs or raises a plaintext secret or the DEK. Every error
detail names the key; none of them carries the value.
"""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from homeiq_ha.secrets.states import (
    DEK_KEY,
    SecretState,
    SecretStoreError,
    store_unavailable,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

#: The ADR's tier-2 table. Also the directory name the file backend uses, so one
#: string names the store in Postgres and on disk.
SECRET_TABLE = "core.appliance_secret"

#: The row key holding the Home Assistant long-lived token. ``HOME_ASSISTANT_TOKEN``
#: and ``HA_TOKEN`` are two env names for this one credential
#: (``domains/core-platform/compose.yml:262``); the store knows it by one name.
HA_TOKEN_KEY = "ha_token"

#: AES-256: the DEK is 32 bytes of tier-1 randomness, hex-encoded in the file.
_DEK_BYTES = 32

#: AES-GCM's recommended nonce length. Drawn fresh from ``os.urandom`` per write.
_NONCE_BYTES = 12

#: Default appliance state directory, matching ``firstboot-secrets.sh``.
_DEFAULT_STATE_DIR = "/var/lib/homeiq"

_STATE_DIR_ENV = "HOMEIQ_STATE_DIR"


@dataclass(frozen=True, slots=True)
class SecretRow:
    """One row of ``core.appliance_secret``: ciphertext, its nonce, and when.

    ``__repr__`` renders lengths rather than bytes. The ciphertext is useless
    without the DEK, but a repr of it in a traceback is still a copy of the
    customer's credential sitting in a log aggregator, and the habit is the point:
    rows are not rendered.
    """

    key: str
    ciphertext: bytes
    nonce: bytes
    updated_at: datetime

    def __repr__(self) -> str:
        return (
            f"SecretRow(key={self.key!r}, "
            f"ciphertext=<{len(self.ciphertext)} bytes>, "
            f"nonce=<{len(self.nonce)} bytes>, updated_at={self.updated_at.isoformat()})"
        )


class SecretBackend(Protocol):
    """Where rows live. The store encrypts; a backend only persists bytes."""

    def read(self, key: str) -> SecretRow | None:
        """Return the row, or ``None`` when no row exists for ``key``."""

    def write(self, row: SecretRow) -> None:
        """Insert or replace ``row``."""

    def has_rows(self) -> bool:
        """Whether any tier-2 row exists.

        This separates a fresh appliance from an unsealed one: with no rows a
        missing DEK loses nothing, with rows it loses everything.
        """


def _encode(row: SecretRow) -> str:
    return json.dumps(
        {
            "key": row.key,
            "value": base64.b64encode(row.ciphertext).decode("ascii"),
            "nonce": base64.b64encode(row.nonce).decode("ascii"),
            "updated_at": row.updated_at.isoformat(),
        },
        indent=2,
    )


def _decode(key: str, payload: str) -> SecretRow:
    data = json.loads(payload)
    return SecretRow(
        key=key,
        ciphertext=base64.b64decode(data["value"]),
        nonce=base64.b64decode(data["nonce"]),
        updated_at=datetime.fromisoformat(data["updated_at"]),
    )


class FileSecretBackend:
    """Rows as ``0600`` JSON files under ``<state_dir>/secrets/core.appliance_secret/``.

    The ADR's four fields, base64 for the two ``bytea`` columns. Writes go through
    a temp file in the same directory and an atomic rename, so a reader never
    observes half a row -- the rule ``firstboot-secrets.sh`` applies to the tier-1
    file, for the same reason.
    """

    def __init__(self, state_dir: str | Path) -> None:
        self.root = Path(state_dir) / "secrets" / SECRET_TABLE

    def _path(self, key: str) -> Path:
        if "/" in key or os.sep in key or key in {"", ".", ".."}:
            msg = f"secret key {key!r} is not a single path-safe name"
            raise ValueError(msg)
        return self.root / f"{key}.json"

    def read(self, key: str) -> SecretRow | None:
        path = self._path(key)
        if not path.is_file():
            return None
        return _decode(key, path.read_text(encoding="utf-8"))

    def write(self, row: SecretRow) -> None:
        path = self._path(row.key)
        self.root.mkdir(parents=True, exist_ok=True)
        self.root.chmod(0o700)
        tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
        # Created at 0600 rather than written and then chmod-ed: the gap between
        # the two is the window in which the row is world-readable.
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(_encode(row))
            tmp.replace(path)
        finally:
            tmp.unlink(missing_ok=True)

    def has_rows(self) -> bool:
        return self.root.is_dir() and any(self.root.glob("*.json"))


class PostgresSecretBackend:
    """The ADR's mandated backend: ``core.appliance_secret`` in the ``core`` schema.

    Constructed with a zero-argument ``connect`` callable rather than a DSN, so the
    driver choice stays with the caller and the adapter is exercisable against a
    fake connection. Any failure to reach the server becomes
    ``SecretStoreUnavailable`` -- the ADR's one retryable state -- while a missing
    row becomes ``None`` and the store turns that into ``SecretNotProvisioned``.
    The two are deliberately distinct: "the database is down" wants a retry and
    "this capability is not provisioned yet" wants a standby ``/ready``, and
    collapsing them makes a fresh appliance look broken.
    """

    _SELECT = "SELECT value, nonce, updated_at FROM {table} WHERE key = %s"
    _UPSERT = (
        "INSERT INTO {table} (key, value, nonce, updated_at) VALUES (%s, %s, %s, %s) "
        "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, "
        "nonce = EXCLUDED.nonce, updated_at = EXCLUDED.updated_at"
    )
    _ANY_ROW = "SELECT 1 FROM {table} LIMIT 1"

    def __init__(self, connect: Callable[[], Any], *, table: str = SECRET_TABLE) -> None:
        self._connect = connect
        self._table = table

    def _execute(self, sql: str, params: tuple[object, ...]) -> list[tuple[Any, ...]]:
        try:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(sql.format(table=self._table), params)
                return [] if cur.description is None else list(cur.fetchall())
        except SecretStoreError:
            raise
        except Exception as exc:  # noqa: BLE001 - driver exception types are not importable here
            # Named, chained and re-raised. The driver's own class name is the
            # only detail kept: a psycopg error message can quote the DSN.
            raise store_unavailable(f"{self._table}: {type(exc).__name__}") from exc

    def read(self, key: str) -> SecretRow | None:
        rows = self._execute(self._SELECT, (key,))
        if not rows:
            return None
        value, nonce, updated_at = rows[0]
        return SecretRow(
            key=key, ciphertext=bytes(value), nonce=bytes(nonce), updated_at=updated_at
        )

    def write(self, row: SecretRow) -> None:
        self._execute(self._UPSERT, (row.key, row.ciphertext, row.nonce, row.updated_at))

    def has_rows(self) -> bool:
        return bool(self._execute(self._ANY_ROW, ()))


def _unsealed(detail: str, *, key: str = DEK_KEY) -> SecretStoreError:
    return SecretStoreError(SecretState.SECRET_STORE_UNSEALED, key=key, detail=detail)


def load_dek(value: str) -> bytes:
    """Decode the tier-1 DEK, or raise ``SecretStoreUnsealed``.

    The returned key is exactly the tier-1 bytes. A wrong length is a hard stop and
    never a reason to stretch, pad or hash the value up to 32: doing so turns a
    truncated or corrupted DEK into a *usable* key that decrypts nothing, which is
    silent data loss wearing the clothes of a working store.
    """
    try:
        dek = bytes.fromhex(value)
    except ValueError as exc:
        raise _unsealed(f"{DEK_KEY} is not hex") from exc
    if len(dek) != _DEK_BYTES:
        raise _unsealed(f"{DEK_KEY} decodes to {len(dek)} bytes, expected {_DEK_BYTES}")
    return dek


def read_tier1_env(state_dir: str | Path) -> dict[str, str]:
    """Parse ``<state_dir>/.env`` as written by ``firstboot-secrets.sh``.

    Comments and blank lines are ignored; everything else is ``KEY=value`` with the
    value taken verbatim to the end of the line, which is the format that script
    writes. An absent file means no keys, not an error -- whether the key the
    caller wanted being missing is fatal is the caller's decision, not this
    function's.
    """
    path = Path(state_dir) / ".env"
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        values[key.strip()] = value
    return values


def resolve_state_dir(env: Mapping[str, str] | None = None) -> Path:
    """The appliance state directory: ``$HOMEIQ_STATE_DIR``, or the ADR default."""
    environ = os.environ if env is None else env
    return Path(environ.get(_STATE_DIR_ENV, "") or _DEFAULT_STATE_DIR)


class ApplianceSecretStore:
    """Tier-2 secrets, encrypted with the tier-1 DEK.

    :meth:`get` and :meth:`put` are the whole surface, and neither takes a
    ``default=``. The ADR's failure table *is* the return contract: a caller that
    wants to treat a missing row as standby catches ``SecretNotProvisioned`` and
    says so on ``/ready``, rather than receiving ``""`` and quietly building an
    anonymous client out of it.
    """

    def __init__(self, dek: bytes, backend: SecretBackend) -> None:
        if len(dek) != _DEK_BYTES:
            raise _unsealed(f"DEK is {len(dek)} bytes, expected {_DEK_BYTES}")
        self._aead = AESGCM(dek)
        self._backend = backend

    @classmethod
    def from_env(
        cls,
        *,
        env: Mapping[str, str] | None = None,
        backend: SecretBackend | None = None,
        state_dir: str | Path | None = None,
    ) -> ApplianceSecretStore:
        """Build the store from the tier-1 DEK and, by default, the file adapter.

        The DEK is looked for in the process environment first and in
        ``<state_dir>/.env`` second. That order is not a fallback chain but the two
        ways one tier-1 file reaches a process: Compose is started with
        ``--env-file /var/lib/homeiq/.env``, so every *service* sees the DEK in its
        environment, while a boot script that runs before Compose reads the file
        directly. Absent from both is ``SecretStoreUnsealed``.
        """
        environ = dict(os.environ if env is None else env)
        root = Path(state_dir) if state_dir is not None else resolve_state_dir(environ)
        adapter = FileSecretBackend(root) if backend is None else backend
        value = environ.get(DEK_KEY, "") or read_tier1_env(root).get(DEK_KEY, "")
        if not value:
            detail = (
                "tier-2 rows exist but the DEK is absent; they are undecryptable"
                if adapter.has_rows()
                else f"no {DEK_KEY} in the environment or in {root}/.env"
            )
            raise _unsealed(detail)
        return cls(load_dek(value), adapter)

    def put(self, key: str, value: str) -> SecretRow:
        """Encrypt ``value`` under ``key`` and store it. Returns the row written.

        A fresh 12-byte nonce every call, including a rewrite of the same value
        under the same key.
        """
        nonce = os.urandom(_NONCE_BYTES)
        ciphertext = self._aead.encrypt(nonce, value.encode("utf-8"), key.encode("utf-8"))
        row = SecretRow(key=key, ciphertext=ciphertext, nonce=nonce, updated_at=datetime.now(UTC))
        self._backend.write(row)
        return row

    def get(self, key: str) -> str:
        """Return the decrypted secret, or raise one of the ADR's named states.

        ``SecretNotProvisioned`` when there is no row -- for ``ha_token`` that is
        the ordinary pre-onboarding condition, not an error. ``SecretStoreUnsealed``
        when a row exists but will not authenticate: a rotated or corrupted DEK, or
        a blob moved onto another key. Never a re-mint, never an empty string.
        """
        row = self._backend.read(key)
        if row is None:
            raise SecretStoreError(
                SecretState.SECRET_NOT_PROVISIONED,
                key=key,
                detail=f"no row in {SECRET_TABLE}; the capability is standby, not defaulted",
            )
        try:
            plaintext = self._aead.decrypt(row.nonce, row.ciphertext, key.encode("utf-8"))
        except InvalidTag as exc:
            raise _unsealed(
                f"the stored row does not authenticate under this {DEK_KEY}", key=key
            ) from exc
        return plaintext.decode("utf-8")


def load_ha_token(
    *,
    env: Mapping[str, str] | None = None,
    backend: SecretBackend | None = None,
    state_dir: str | Path | None = None,
) -> str:
    """The consumer entry point: the HA long-lived token, from the tier-2 store.

    This is what the ADR means by the token "reaching HomeIQ services and
    AgentForge through the appliance secret store". A service that needs to talk to
    Home Assistant calls this at the point of use instead of reading ``HA_TOKEN``
    from its environment, so a rotation is picked up without a stack restart and no
    plaintext copy of the credential sits in any container's environment.

    Raises ``SecretNotProvisioned`` before the appliance has been onboarded. That
    is the documented standby state and belongs on ``/ready`` as not-ready; it is
    never an empty string, because an empty token builds an anonymous client that
    reports Home Assistant's refusal as a Home Assistant problem.
    """
    store = ApplianceSecretStore.from_env(env=env, backend=backend, state_dir=state_dir)
    return store.get(HA_TOKEN_KEY)
