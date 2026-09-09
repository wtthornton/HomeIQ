"""Shared contract for the host-file transports.

Split out of :mod:`host_files` so the SSH transport (:mod:`host_files`) and
the local-mount transport (:mod:`host_files_local`) can each import the
shared errors, protocol, and constants without importing each other.
"""

from __future__ import annotations

from typing import Protocol

#: Where Home Assistant keeps its configuration on a Supervised install.
HA_CONFIG_DIR = "/config"

#: Permission bits applied to a file :class:`~homeiq_ha.agent.host_files_local.LocalHostFiles`
#: creates from scratch — owner read/write, group and other read-only,
#: matching what Home Assistant itself writes into ``/config``. A file that
#: already exists gets its mode carried over from the pre-write stat instead
#: of this default.
DEFAULT_FILE_MODE = 0o644


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


__all__ = [
    "DEFAULT_FILE_MODE",
    "HA_CONFIG_DIR",
    "HostFileError",
    "HostFileNotFound",
    "HostFiles",
]
