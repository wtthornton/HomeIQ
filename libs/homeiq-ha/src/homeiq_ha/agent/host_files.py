"""Transports to files on the Home Assistant host (``/config``).

Two design-doc rows are YAML-only — ``http:`` (row 1.1) and ``recorder:``
(row 2.4) have no API at all — so the agent needs file access to the host.
``HOMEIQ_HA_BACKEND`` is the *only* switch between the two ways to get it,
never the presence of ``HOMEIQ_HA_SSH_HOST`` / ``HOMEIQ_HA_LOCAL_CONFIG_DIR``:

- ``"ssh"`` (default) — the **Terminal & SSH (`core_ssh`) add-on**. See
  docs/deployment/DEPLOYMENT_RUNBOOK.md ("Agent write path to Home Assistant
  `/config`") for provisioning and rotation.
- ``"local"`` — for an appliance whose HA ``/config`` is a bind mount this
  process can already read and write directly. ``HOMEIQ_HA_LOCAL_CONFIG_DIR``
  names the mount (default :data:`HA_CONFIG_DIR`).

:class:`HostFiles` is a Protocol so recipes take the transport by injection
and their tests never open a socket or touch a real filesystem.
:class:`SSHHostFiles` shells out to ``ssh`` (see its docstring for the
checksum-guarded remote script); :class:`LocalHostFiles` uses the filesystem
directly (see its docstring for the temp-file-plus-``os.replace`` algorithm).
Both keep a write atomic and always leave a backup of whatever they overwrote.
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import os
import shlex
import shutil
import stat
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

#: Seconds any single ssh invocation may take.
DEFAULT_TIMEOUT = 30.0

#: Where Home Assistant keeps its configuration on a Supervised install.
HA_CONFIG_DIR = "/config"

#: Permission bits applied to a file :class:`LocalHostFiles` creates from
#: scratch — owner read/write, group and other read-only, matching what Home
#: Assistant itself writes into ``/config``. A file that already exists gets
#: its mode carried over from the pre-write stat instead of this default.
DEFAULT_FILE_MODE = 0o644


#: Exit code the read script uses for "the file is not there". Chosen well
#: clear of the codes ``ssh`` (255) and ``cat`` (1) use, so the two causes can
#: never be confused for one another.
MISSING_FILE_EXIT = 44


class HostFileError(RuntimeError):
    """An ssh file operation failed, or wrote something other than what was sent."""

    def __init__(self, message: str, *, returncode: int | None = None) -> None:
        super().__init__(message)
        #: Exit status of the remote command, when there was one.
        self.returncode = returncode


class HostFileNotFound(HostFileError):
    """The path does not exist on the host.

    Separate from :class:`HostFileError` because callers act on the difference:
    "the file is not deployed yet" is a thing to fix by writing it, while "ssh
    could not reach the host" is a thing to surface. Collapsing the two would
    let a broken transport read as absent config and trigger a blind rewrite.
    """


class HostFiles(Protocol):
    """Read and replace a single text file on the Home Assistant host."""

    async def read_text(self, path: str) -> str:
        """Return the file's contents.

        Raises:
            HostFileNotFound: the path does not exist on the host.
        """
        ...

    async def write_text(self, path: str, content: str) -> str | None:
        """Write the file atomically, returning the backup path if one was taken.

        ``None`` means the file did not exist and was created, so there was
        nothing to back up.
        """
        ...


@dataclass(frozen=True)
class SSHTarget:
    """Where the agent's key reaches the HA host.

    Attributes:
        host: The HA host address.
        port: The published ``core_ssh`` port — 22222, not 22: port 22 on a
            Supervised install belongs to the host OS, not the add-on.
        user: The add-on's account.
        key_path: Path to the agent's private key on *this* machine.
    """

    host: str
    port: int = 22222
    user: str = "root"
    key_path: str = "~/.ssh/homeiq_agent_ed25519"

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> SSHTarget | None:
        """Build a target from ``HOMEIQ_HA_SSH_*``, or ``None`` if unconfigured.

        ``HOMEIQ_HA_SSH_HOST`` is the switch: without it there is no write
        path, and recipes that need one report themselves not applicable
        rather than guessing an address.
        """
        source: Mapping[str, str] = os.environ if env is None else env
        host = str(source.get("HOMEIQ_HA_SSH_HOST") or "").strip()
        if not host:
            return None
        port = str(source.get("HOMEIQ_HA_SSH_PORT") or "").strip()
        return cls(
            host=host,
            port=int(port) if port else cls.port,
            user=str(source.get("HOMEIQ_HA_SSH_USER") or "").strip() or cls.user,
            key_path=str(source.get("HOMEIQ_HA_SSH_KEY") or "").strip() or cls.key_path,
        )


# The existence test is the point: `cat` alone exits 1 for a missing file and
# ssh exits 255 when it cannot connect, but a shell that is up and a `cat` that
# fails for some third reason both land on 1 too. Testing first and exiting a
# code nothing else uses is what makes "absent" unambiguous.
_READ_SCRIPT = """if [ ! -e {path} ]; then
  echo "no such file: {path}" >&2
  exit {code}
fi
cat -- {path}
"""

# Runs under the add-on's ash shell. Placeholders are shell-quoted by the
# caller; the digest is hex from hashlib and is embedded literally.
#
# Both existence branches are here rather than in a second round trip: probing
# for the file first and then writing would be two ssh invocations with a race
# between them, and the shell already knows the answer at the moment it acts.
# The backup path is echoed only when a backup was actually taken, which is how
# the caller learns whether it replaced a file or created one.
_WRITE_SCRIPT = """set -e
mkdir -p -- {parent}
if [ -e {path} ]; then
  cp -p -- {path} {tmp}
else
  : > {tmp}
fi
cat > {tmp}
got=$(sha256sum < {tmp} | cut -d' ' -f1)
if [ "$got" != "{digest}" ]; then
  rm -f -- {tmp}
  echo "transfer corrupted: host has $got, sent {digest}" >&2
  exit 3
fi
if [ -e {path} ]; then
  cp -p -- {path} {backup}
  echo {backup}
fi
mv -f -- {tmp} {path}
"""


class SSHHostFiles:
    """:class:`HostFiles` over the ``core_ssh`` add-on."""

    def __init__(
        self,
        target: SSHTarget,
        *,
        timeout: float = DEFAULT_TIMEOUT,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        """
        Args:
            target: Address, port, user and key path.
            timeout: Seconds any single ssh invocation may take.
            now: Clock returning an aware :class:`~datetime.datetime`, used
                for backup filenames. Injected so tests get stable names.
        """
        self.target = target
        self.timeout = timeout
        self._now = now or (lambda: datetime.now(UTC))

    def _key_file(self) -> str:
        """Return a private-key path ``ssh`` will actually accept.

        OpenSSH refuses a key that is group- or world-readable, and a key
        delivered by bind mount keeps its host ownership and mode — which in a
        container is somebody else's uid. The mount therefore has to be
        group-readable to be readable at all, which is exactly what ssh rejects.

        So when the key as presented is not already private to this process, a
        0600 copy is staged under the runtime user's own ``~/.ssh``. The staged
        path is stable rather than a temp file: restaging on every call would
        churn the filesystem, and a fixed name is idempotent.
        """
        src = Path(self.target.key_path).expanduser()
        try:
            st = src.stat()
        except OSError:
            # Missing or unreadable: hand the original to ssh and let its own
            # error message say so, rather than masking it with a copy failure.
            return str(src)
        if st.st_uid == os.getuid() and not st.st_mode & 0o077:
            return str(src)
        staged = Path.home() / ".ssh" / "homeiq-agent-key"
        staged.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        data = src.read_bytes()
        if not staged.exists() or staged.read_bytes() != data:
            staged.write_bytes(data)
        staged.chmod(0o600)
        return str(staged)

    def _argv(self, remote_command: str) -> list[str]:
        return [
            "ssh",
            "-i",
            self._key_file(),
            "-p",
            str(self.target.port),
            # accept-new, not no: the host key is still pinned after first
            # contact, so a later key change fails loudly instead of silently.
            "-o",
            "StrictHostKeyChecking=accept-new",
            # Never fall back to an interactive prompt in an agent run.
            "-o",
            "BatchMode=yes",
            "-o",
            f"ConnectTimeout={max(1, int(self.timeout))}",
            f"{self.target.user}@{self.target.host}",
            remote_command,
        ]

    async def _run(self, remote_command: str, stdin: bytes | None = None) -> str:
        proc = await asyncio.create_subprocess_exec(
            *self._argv(remote_command),
            stdin=asyncio.subprocess.PIPE if stdin is not None else asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            out, err = await asyncio.wait_for(proc.communicate(stdin), timeout=self.timeout)
        except TimeoutError as exc:
            proc.kill()
            await proc.wait()
            raise HostFileError(
                f"ssh to {self.target.user}@{self.target.host}:{self.target.port} "
                f"timed out after {self.timeout}s"
            ) from exc
        if proc.returncode != 0:
            raise HostFileError(
                f"ssh to {self.target.user}@{self.target.host}:{self.target.port} "
                f"exited {proc.returncode}: {err.decode(errors='replace').strip()}",
                returncode=proc.returncode,
            )
        return out.decode()

    async def read_text(self, path: str) -> str:
        """Return the file's contents.

        Raises:
            HostFileNotFound: the path does not exist on the host.
            HostFileError: ssh itself failed, or the read did.
        """
        script = _READ_SCRIPT.format(path=shlex.quote(path), code=MISSING_FILE_EXIT)
        try:
            return await self._run(script)
        except HostFileError as exc:
            if exc.returncode == MISSING_FILE_EXIT:
                raise HostFileNotFound(
                    f"{path} does not exist on "
                    f"{self.target.user}@{self.target.host}:{self.target.port}",
                    returncode=exc.returncode,
                ) from exc
            raise

    async def write_text(self, path: str, content: str) -> str | None:
        """Write ``path`` atomically, keeping a timestamped backup of any prior file.

        Missing parent directories are created, so this also serves the recipes
        that *add* a file to ``/config`` (a custom quirk, a custom component)
        rather than editing one that is already there.

        Args:
            path: Absolute path on the HA host.
            content: The complete new contents.

        Returns:
            Path of the backup copy taken immediately before the swap, or
            ``None`` when ``path`` did not exist and was created.

        Raises:
            HostFileError: the transfer arrived with a different SHA-256, or
                any step of the remote script failed. Either way ``path`` is
                left exactly as it was — previous contents, or absent.
        """
        payload = content.encode()
        digest = hashlib.sha256(payload).hexdigest()
        stamp = self._now().strftime("%Y%m%dT%H%M%SZ")
        backup = f"{path}.homeiq-{stamp}.bak"
        tmp = f"{path}.homeiq.tmp"
        script = _WRITE_SCRIPT.format(
            parent=shlex.quote(str(PurePosixPath(path).parent)),
            path=shlex.quote(path),
            tmp=shlex.quote(tmp),
            backup=shlex.quote(backup),
            digest=digest,
        )
        # PurePosixPath, not Path: the path being split is on the HA host, and
        # deriving it with the local flavour would break the day an operator
        # runs the agent from Windows.
        return (await self._run(script, stdin=payload)).strip() or None


@dataclass(frozen=True)
class LocalTarget:
    """Where the agent's local mount reaches HA's ``/config``.

    Attributes:
        config_dir: Root of the bind-mounted ``/config`` directory on this
            machine. Recorded for diagnostics and backup naming; it does not
            gate which paths :class:`LocalHostFiles` will touch — the caller
            passes absolute paths, exactly as it does for the SSH transport.
    """

    config_dir: str = HA_CONFIG_DIR

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> LocalTarget:
        """Build a target from ``HOMEIQ_HA_LOCAL_CONFIG_DIR``, defaulting to :data:`HA_CONFIG_DIR`."""
        source: Mapping[str, str] = os.environ if env is None else env
        config_dir = str(source.get("HOMEIQ_HA_LOCAL_CONFIG_DIR") or "").strip()
        return cls(config_dir=config_dir or cls.config_dir)


class LocalHostFiles:
    """:class:`HostFiles` over a local bind mount of HA's ``/config``.

    For an appliance whose HA instance and agent share a filesystem there is
    no SSH hop: the target directory is just a path this process can already
    read and write. A write:

    1. lands in a temp file made by :func:`tempfile.mkstemp` **in the
       target's own directory**, guaranteeing it is on the same filesystem;
    2. backs up any existing target to a timestamped copy first, and matches
       the temp file's mode/ownership to it (ownership is best-effort — a
       non-root process cannot ``chown`` to someone else's uid, the same
       limit :class:`SSHHostFiles` has against a peer-owned remote file);
    3. swaps in with :meth:`Path.replace`, a same-directory rename and
       therefore atomic — it raises ``OSError`` across filesystems rather
       than degrading to a non-atomic copy, which step 1 rules out anyway.
    """

    def __init__(
        self,
        target: LocalTarget,
        *,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        """
        Args:
            target: The local mount's root, for diagnostics.
            now: Clock returning an aware :class:`~datetime.datetime`, used
                for backup filenames. Injected so tests get stable names.
        """
        self.target = target
        self._now = now or (lambda: datetime.now(UTC))

    async def read_text(self, path: str) -> str:
        """Return the file's contents.

        Raises:
            HostFileNotFound: the path does not exist.
            HostFileError: the path exists but could not be read (e.g.
                permission denied) — kept distinct from "absent" so a caller
                never mistakes a permissions problem for missing config.
        """
        return await asyncio.to_thread(self._read_text, path)

    def _read_text(self, path: str) -> str:
        try:
            return Path(path).read_text()
        except FileNotFoundError as exc:
            raise HostFileNotFound(
                f"{path} does not exist under {self.target.config_dir}"
            ) from exc
        except OSError as exc:
            raise HostFileError(f"{path} could not be read: {exc}") from exc

    async def write_text(self, path: str, content: str) -> str | None:
        """Write ``path`` atomically, keeping a timestamped backup of any prior file.

        Missing parent directories are created, so this also serves recipes
        that *add* a file (a custom quirk, a custom component) rather than
        editing one that is already there.

        Args:
            path: Absolute path under the local ``/config`` mount.
            content: The complete new contents.

        Returns:
            Path of the backup copy taken immediately before the swap, or
            ``None`` when ``path`` did not exist and was created.

        Raises:
            HostFileError: the temp file could not be written, or
                :func:`os.replace` failed (including across filesystems,
                which it always refuses rather than degrading to a copy).
        """
        return await asyncio.to_thread(self._write_text, path, content)

    def _write_text(self, path: str, content: str) -> str | None:
        target = Path(path)
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise HostFileError(f"could not create {target.parent}: {exc}") from exc

        try:
            existing: os.stat_result | None = target.stat()
        except FileNotFoundError:
            existing = None
        except OSError as exc:
            raise HostFileError(f"{path} could not be read: {exc}") from exc

        try:
            fd, tmp_name = tempfile.mkstemp(
                dir=target.parent, prefix=f".{target.name}.", suffix=".homeiq.tmp"
            )
        except OSError as exc:
            raise HostFileError(f"could not create a temp file next to {path}: {exc}") from exc
        tmp = Path(tmp_name)

        try:
            self._fill_temp(tmp, content)
            backup = self._prepare_swap(target, tmp, existing)
            try:
                tmp.replace(target)
            except OSError as exc:
                raise HostFileError(f"could not replace {path}: {exc}") from exc
        except BaseException:
            with contextlib.suppress(OSError):
                tmp.unlink()
            raise
        return backup

    @staticmethod
    def _fill_temp(tmp: Path, content: str) -> None:
        with tmp.open("w") as fh:
            fh.write(content)
            fh.flush()
            os.fsync(fh.fileno())

    def _prepare_swap(
        self, target: Path, tmp: Path, existing: os.stat_result | None
    ) -> str | None:
        """Back up ``target`` if it exists and match ``tmp``'s mode/owner to it.

        Returns the backup path, or ``None`` when ``target`` did not exist —
        the same "replace vs. create" signal :meth:`write_text` promises.
        """
        if existing is None:
            tmp.chmod(DEFAULT_FILE_MODE)
            return None

        stamp = self._now().strftime("%Y%m%dT%H%M%SZ")
        backup = f"{target}.homeiq-{stamp}.bak"
        try:
            shutil.copy2(target, backup)
        except OSError as exc:
            raise HostFileError(f"could not back up {target}: {exc}") from exc
        tmp.chmod(stat.S_IMODE(existing.st_mode))
        with contextlib.suppress(OSError):
            # Not running as root / not the file's owner: the target already
            # carried the right ids, and a non-root process cannot chown to
            # someone else's — the same limitation the SSH transport has
            # against a peer-owned file.
            os.chown(tmp, existing.st_uid, existing.st_gid)
        return backup


def host_files_from_env(env: Mapping[str, str] | None = None) -> HostFiles | None:
    """The configured transport, or ``None`` when no write path is provisioned.

    ``HOMEIQ_HA_BACKEND`` is the explicit selection key — ``"ssh"`` (the
    default, so an unset var keeps today's behavior) or ``"local"``. It is
    the only thing that decides which transport is built; the presence of
    ``HOMEIQ_HA_SSH_HOST`` or ``HOMEIQ_HA_LOCAL_CONFIG_DIR`` never does.
    """
    source: Mapping[str, str] = os.environ if env is None else env
    backend = str(source.get("HOMEIQ_HA_BACKEND") or "ssh").strip().lower()
    if backend == "local":
        return LocalHostFiles(LocalTarget.from_env(source))
    if backend == "ssh":
        target = SSHTarget.from_env(source)
        return None if target is None else SSHHostFiles(target)
    raise ValueError(f"HOMEIQ_HA_BACKEND={backend!r} is not 'ssh' or 'local'")


__all__ = [
    "DEFAULT_FILE_MODE",
    "DEFAULT_TIMEOUT",
    "HA_CONFIG_DIR",
    "MISSING_FILE_EXIT",
    "HostFileError",
    "HostFileNotFound",
    "HostFiles",
    "LocalHostFiles",
    "LocalTarget",
    "SSHHostFiles",
    "SSHTarget",
    "host_files_from_env",
]
