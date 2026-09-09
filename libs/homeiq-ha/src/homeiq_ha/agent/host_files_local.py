"""The local-mount transport to the Home Assistant host.

Split out of :mod:`host_files` (which keeps the SSH transport) so each
transport's implementation stays a single, independently scored module —
see that module's docstring for why both transports exist and how callers
choose between them.
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import shutil
import stat
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from .host_files_base import DEFAULT_FILE_MODE, HA_CONFIG_DIR, HostFileError, HostFileNotFound

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping


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
       limit :class:`~homeiq_ha.agent.host_files.SSHHostFiles` has against a
       peer-owned remote file);
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
            raise HostFileNotFound(f"{path} does not exist under {self.target.config_dir}") from exc
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

    def _prepare_swap(self, target: Path, tmp: Path, existing: os.stat_result | None) -> str | None:
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


__all__ = ["LocalHostFiles", "LocalTarget"]
