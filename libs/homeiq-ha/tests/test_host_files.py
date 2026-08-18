"""Tests for the ssh transport to the Home Assistant host.

``ssh`` itself is never executed: the argv and the remote script are what
matter, and both are asserted directly. A wrong quote or a missing checksum
guard is a corrupted ``configuration.yaml``, which is exactly the failure this
transport exists to make impossible.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

import pytest
from homeiq_ha.agent.host_files import (
    MISSING_FILE_EXIT,
    HostFileError,
    HostFileNotFound,
    SSHHostFiles,
    SSHTarget,
    host_files_from_env,
)

ENV = {
    "HOMEIQ_HA_SSH_HOST": "192.168.1.80",
    "HOMEIQ_HA_SSH_PORT": "22222",
    "HOMEIQ_HA_SSH_USER": "root",
    "HOMEIQ_HA_SSH_KEY": "/keys/agent_ed25519",
}


def _transport(**kwargs) -> SSHHostFiles:
    return SSHHostFiles(
        SSHTarget.from_env(ENV),
        now=lambda: datetime(2026, 8, 18, 1, 2, 3, tzinfo=UTC),
        **kwargs,
    )


class FakeRun:
    """Stands in for :meth:`SSHHostFiles._run`, recording what it was asked."""

    def __init__(self, stdout: str = "", error: Exception | None = None) -> None:
        self.stdout = stdout
        self.error = error
        self.commands: list[str] = []
        self.stdin: list[bytes | None] = []

    async def __call__(self, remote_command: str, stdin: bytes | None = None) -> str:
        self.commands.append(remote_command)
        self.stdin.append(stdin)
        if self.error is not None:
            raise self.error
        return self.stdout


# --- target resolution -----------------------------------------------------


def test_target_from_env_reads_all_four_values():
    target = SSHTarget.from_env(ENV)

    assert target == SSHTarget(
        host="192.168.1.80", port=22222, user="root", key_path="/keys/agent_ed25519"
    )


def test_target_from_env_is_none_without_a_host():
    assert SSHTarget.from_env({"HOMEIQ_HA_SSH_PORT": "22222"}) is None
    assert host_files_from_env({}) is None


def test_target_from_env_defaults_the_optional_values():
    target = SSHTarget.from_env({"HOMEIQ_HA_SSH_HOST": "ha.local"})

    assert (target.port, target.user) == (22222, "root")
    assert target.key_path.endswith("homeiq_agent_ed25519")


def test_argv_is_batch_mode_and_pins_the_host_key():
    argv = _transport()._argv("cat -- /config/configuration.yaml")

    assert argv[0] == "ssh"
    assert argv[-2:] == ["root@192.168.1.80", "cat -- /config/configuration.yaml"]
    assert "BatchMode=yes" in argv
    assert "StrictHostKeyChecking=accept-new" in argv
    assert argv[argv.index("-p") + 1] == "22222"
    assert argv[argv.index("-i") + 1] == "/keys/agent_ed25519"


# --- read ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_read_text_cats_the_quoted_path():
    transport = _transport()
    run = FakeRun(stdout="default_config:\n")
    transport._run = run

    assert await transport.read_text("/config/configuration.yaml") == "default_config:\n"
    assert run.commands[0].endswith("cat -- /config/configuration.yaml\n")
    assert run.stdin == [None]


@pytest.mark.asyncio
async def test_read_text_quotes_a_hostile_path():
    transport = _transport()
    run = FakeRun()
    transport._run = run

    await transport.read_text("/config/a b; rm -rf /")

    # Quoted in the existence test as well as the cat, or the guard itself
    # becomes the injection point.
    assert run.commands[0].count("'/config/a b; rm -rf /'") == 3


@pytest.mark.asyncio
async def test_read_text_tests_for_existence_before_reading():
    transport = _transport()
    run = FakeRun()
    transport._run = run

    await transport.read_text("/config/custom_zha_quirks/aqara_fp1e.py")

    script = run.commands[0]
    assert script.startswith("if [ ! -e ")
    assert f"exit {MISSING_FILE_EXIT}" in script
    assert script.index(f"exit {MISSING_FILE_EXIT}") < script.index("cat --")


@pytest.mark.asyncio
async def test_read_text_raises_not_found_only_for_the_missing_file_code():
    transport = _transport()
    transport._run = FakeRun(
        error=HostFileError("exited 44", returncode=MISSING_FILE_EXIT)
    )

    with pytest.raises(HostFileNotFound, match="does not exist"):
        await transport.read_text("/config/custom_zha_quirks/aqara_fp1e.py")


@pytest.mark.asyncio
async def test_a_transport_failure_is_never_reported_as_a_missing_file():
    """ssh being down must not read as "not deployed yet" — see HostFileNotFound."""
    transport = _transport()
    transport._run = FakeRun(error=HostFileError("connection refused", returncode=255))

    with pytest.raises(HostFileError) as caught:
        await transport.read_text("/config/custom_zha_quirks/aqara_fp1e.py")

    assert not isinstance(caught.value, HostFileNotFound)


# --- write -----------------------------------------------------------------


@pytest.mark.asyncio
async def test_write_text_streams_content_and_returns_a_timestamped_backup():
    transport = _transport()
    # The remote script echoes the backup path only when it took one, which is
    # how the caller learns it replaced a file rather than creating one.
    run = FakeRun(stdout="/config/configuration.yaml.homeiq-20260818T010203Z.bak\n")
    transport._run = run

    backup = await transport.write_text("/config/configuration.yaml", "http:\n")

    assert backup == "/config/configuration.yaml.homeiq-20260818T010203Z.bak"
    assert run.stdin == [b"http:\n"]


@pytest.mark.asyncio
async def test_write_text_returns_no_backup_when_it_created_the_file():
    transport = _transport()
    transport._run = FakeRun()

    assert await transport.write_text("/config/custom_zha_quirks/q.py", "x = 1\n") is None


@pytest.mark.asyncio
async def test_write_script_creates_a_missing_file_and_its_parent_directory():
    transport = _transport()
    run = FakeRun()
    transport._run = run

    await transport.write_text("/config/custom_zha_quirks/aqara_fp1e.py", "x = 1\n")

    script = run.commands[0]
    assert "mkdir -p -- /config/custom_zha_quirks" in script
    # Seeded from the target when it exists, created empty when it does not —
    # so mode and ownership survive a replace without the create failing.
    assert "if [ -e /config/custom_zha_quirks/aqara_fp1e.py ]; then" in script
    assert ": > /config/custom_zha_quirks/aqara_fp1e.py.homeiq.tmp" in script
    # The checksum guard still stands in front of the swap on the create path.
    assert script.index('if [ "$got" !=') < script.index("mv -f")


@pytest.mark.asyncio
async def test_write_script_is_checksum_guarded_atomic_and_backed_up():
    transport = _transport()
    run = FakeRun()
    transport._run = run
    content = "recorder:\n  purge_keep_days: 3\n"

    await transport.write_text("/config/configuration.yaml", content)

    script = run.commands[0]
    digest = hashlib.sha256(content.encode()).hexdigest()
    assert script.startswith("set -e\n")
    # Seeded from the target so mode and ownership survive the swap.
    assert "cp -p -- /config/configuration.yaml /config/configuration.yaml.homeiq.tmp" in script
    assert f'if [ "$got" != "{digest}" ]; then' in script
    # A corrupted transfer deletes the temp file and never touches the target.
    assert script.index("rm -f -- /config/configuration.yaml.homeiq.tmp") < script.index("mv -f")
    # Backup is taken before the swap, and the swap is a same-directory rename.
    assert script.index(".homeiq-20260818T010203Z.bak") < script.index("mv -f")
    assert script.rstrip().endswith(
        "mv -f -- /config/configuration.yaml.homeiq.tmp /config/configuration.yaml"
    )


@pytest.mark.asyncio
async def test_a_failed_remote_script_surfaces_as_a_host_file_error():
    transport = _transport()
    transport._run = FakeRun(error=HostFileError("ssh exited 3: transfer corrupted"))

    with pytest.raises(HostFileError, match="transfer corrupted"):
        await transport.write_text("/config/configuration.yaml", "http:\n")


@pytest.mark.asyncio
async def test_a_nonzero_exit_is_reported_with_its_stderr():
    """The real subprocess path, with a local command standing in for ssh."""
    transport = _transport(timeout=5.0)
    transport._argv = lambda _remote: ["sh", "-c", "echo 'no such file' >&2; exit 3"]

    with pytest.raises(HostFileError, match="exited 3: no such file"):
        await transport._run("cat -- /config/configuration.yaml")


@pytest.mark.asyncio
async def test_stdin_reaches_the_remote_command_byte_for_byte():
    transport = _transport(timeout=5.0)
    transport._argv = lambda _remote: ["sh", "-c", "sha256sum | cut -d' ' -f1"]
    content = "recorder:\n  purge_keep_days: 3\n"

    out = await transport._run("ignored", stdin=content.encode())

    assert out.strip() == hashlib.sha256(content.encode()).hexdigest()
