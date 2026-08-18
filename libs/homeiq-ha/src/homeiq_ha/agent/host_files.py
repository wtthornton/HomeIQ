"""SSH transport to files on the Home Assistant host (``/config``).

Two design-doc rows are YAML-only — ``http:`` (row 1.1) and ``recorder:``
(row 2.4) have no API at all — so the agent needs file access to the host.
It gets it through the **Terminal & SSH (`core_ssh`) add-on**: a dedicated
agent public key in the add-on's ``authorized_keys`` and its ``22/tcp`` port
published. Provisioning and rotation are in
docs/deployment/DEPLOYMENT_RUNBOOK.md ("Agent write path to Home Assistant
`/config`"). ``HOMEIQ_HA_SSH_KEY`` records the *path* to the private key; the
key itself never leaves the operator host.

:class:`HostFiles` is a Protocol so recipes take the transport by injection
and their tests never open a socket. The only implementation here,
:class:`SSHHostFiles`, shells out to ``ssh``: the add-on speaks plain OpenSSH
and pulling in an SSH client library to issue two commands would be a
dependency nobody asked for.

Writes are integrity-checked and atomic by construction, because the file
being written is the one that decides whether the instance boots:

1. the new content is streamed over stdin into a sibling temp file, seeded by
   ``cp -p`` from the target so mode and ownership survive (a target that does
   not exist yet is created instead, parent directories included);
2. the temp file's SHA-256 is compared **on the host** against the digest of
   what was sent, and a mismatch deletes the temp file and fails — the live
   file is never touched by a short or corrupted transfer;
3. only then is a timestamped backup taken and the temp file ``mv``-ed over
   the target, which is a rename within one directory and therefore atomic.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import shlex
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

    def _argv(self, remote_command: str) -> list[str]:
        return [
            "ssh",
            "-i",
            str(Path(self.target.key_path).expanduser()),
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
            out, err = await asyncio.wait_for(
                proc.communicate(stdin), timeout=self.timeout
            )
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


def host_files_from_env(env: Mapping[str, str] | None = None) -> SSHHostFiles | None:
    """The configured transport, or ``None`` when no write path is provisioned."""
    target = SSHTarget.from_env(env)
    return None if target is None else SSHHostFiles(target)


__all__ = [
    "DEFAULT_TIMEOUT",
    "HA_CONFIG_DIR",
    "MISSING_FILE_EXIT",
    "HostFileError",
    "HostFileNotFound",
    "HostFiles",
    "SSHHostFiles",
    "SSHTarget",
    "host_files_from_env",
]
