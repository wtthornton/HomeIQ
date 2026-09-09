"""Tests for the local-mount transport to the Home Assistant host.

Unlike the SSH transport, this one really touches the filesystem — that is
the whole point of a local mount — so these tests use ``tmp_path`` rather
than mocking a subprocess.
"""

from __future__ import annotations

import os
import stat
import tempfile
from pathlib import Path

import pytest
from homeiq_ha.agent.config_yaml import HttpLoginThresholdRecipe
from homeiq_ha.agent.host_files import (
    DEFAULT_FILE_MODE,
    HostFileError,
    HostFileNotFound,
    LocalHostFiles,
    LocalTarget,
    SSHHostFiles,
    host_files_from_env,
)
from homeiq_ha.agent.zha_quirks import AqaraFP1EQuirkRecipe


def _transport(tmp_path) -> LocalHostFiles:
    return LocalHostFiles(LocalTarget(config_dir=str(tmp_path)))


# --- VAL-020: LocalTarget round-trips with no HOMEIQ_HA_SSH_HOST set --------


@pytest.mark.asyncio
async def test_local_target_round_trips_a_write_with_no_ssh_host_set(tmp_path, monkeypatch):
    monkeypatch.delenv("HOMEIQ_HA_SSH_HOST", raising=False)
    target_file = tmp_path / "configuration.yaml"

    transport = host_files_from_env({"HOMEIQ_HA_BACKEND": "local", "HOMEIQ_HA_LOCAL_CONFIG_DIR": str(tmp_path)})

    assert isinstance(transport, LocalHostFiles)
    backup = await transport.write_text(str(target_file), "http:\n")
    assert backup is None  # created, nothing to back up
    assert await transport.read_text(str(target_file)) == "http:\n"


# --- selection is explicit ---------------------------------------------------


def test_backend_selection_is_explicit_not_inferred_from_which_env_var_is_set(tmp_path):
    """Both vars set: HOMEIQ_HA_BACKEND wins, not "whichever var happens to exist"."""
    both_set = {
        "HOMEIQ_HA_BACKEND": "local",
        "HOMEIQ_HA_LOCAL_CONFIG_DIR": str(tmp_path),
        "HOMEIQ_HA_SSH_HOST": "192.168.1.80",
    }
    assert isinstance(host_files_from_env(both_set), LocalHostFiles)

    both_set["HOMEIQ_HA_BACKEND"] = "ssh"
    assert isinstance(host_files_from_env(both_set), SSHHostFiles)

    # No HOMEIQ_HA_BACKEND at all, but a local dir is set: still defaults to
    # ssh, and with no SSH host that means no transport — never a silent
    # fallback to whichever var is present.
    assert host_files_from_env({"HOMEIQ_HA_LOCAL_CONFIG_DIR": str(tmp_path)}) is None

    with pytest.raises(ValueError, match="HOMEIQ_HA_BACKEND"):
        host_files_from_env({"HOMEIQ_HA_BACKEND": "bogus"})


# --- backup on overwrite -----------------------------------------------------


@pytest.mark.asyncio
async def test_write_text_backs_up_before_overwriting_with_pre_overwrite_content(tmp_path):
    transport = _transport(tmp_path)
    target = tmp_path / "configuration.yaml"
    target.write_text("original:\n  value: 1\n")

    backup = await transport.write_text(str(target), "original:\n  value: 2\n")

    assert backup is not None
    # The backup is the pre-overwrite content, not a copy taken too late.
    assert Path(backup).read_text() == "original:\n  value: 1\n"
    # The caller can tell replace (a backup path) from create (None).
    assert target.read_text() == "original:\n  value: 2\n"


@pytest.mark.asyncio
async def test_write_text_returns_no_backup_when_it_created_the_file(tmp_path):
    transport = _transport(tmp_path)
    target = tmp_path / "custom_zha_quirks" / "aqara_fp1e.py"

    backup = await transport.write_text(str(target), "x = 1\n")

    assert backup is None
    assert target.read_text() == "x = 1\n"


# --- atomic writes ------------------------------------------------------------


@pytest.mark.asyncio
async def test_write_text_leaves_the_target_untouched_when_os_replace_fails(tmp_path, monkeypatch):
    transport = _transport(tmp_path)
    target = tmp_path / "configuration.yaml"
    target.write_text("original:\n")

    def _boom(_src, _dst):
        raise OSError("Invalid cross-device link")

    monkeypatch.setattr(os, "replace", _boom)

    with pytest.raises(HostFileError, match="could not replace"):
        await transport.write_text(str(target), "new:\n")

    # os.replace never ran, so the original content is exactly as it was —
    # no non-atomic fallback wrote a truncated file.
    assert target.read_text() == "original:\n"
    # The temp file used for the failed replace is cleaned up. A backup may
    # legitimately exist (it is taken before the replace attempt), but no
    # ``.homeiq.tmp`` file is left orphaned behind a failed swap.
    leftover_tmp = [p for p in tmp_path.iterdir() if p.name.endswith(".homeiq.tmp")]
    assert leftover_tmp == []


@pytest.mark.asyncio
async def test_write_text_uses_a_temp_file_in_the_same_directory(tmp_path, monkeypatch):
    """os.replace only stays atomic within one filesystem; same-directory guarantees that."""
    transport = _transport(tmp_path)
    target = tmp_path / "sub" / "configuration.yaml"
    seen_dirs: list[str] = []
    real_mkstemp = tempfile.mkstemp

    def _spy(*args, **kwargs):
        seen_dirs.append(str(kwargs.get("dir")))
        return real_mkstemp(*args, **kwargs)

    monkeypatch.setattr(tempfile, "mkstemp", _spy)

    await transport.write_text(str(target), "x: 1\n")

    assert seen_dirs == [str(target.parent)]


# --- absent vs unreadable -----------------------------------------------------


@pytest.mark.asyncio
async def test_read_text_raises_not_found_for_a_missing_file(tmp_path):
    transport = _transport(tmp_path)

    with pytest.raises(HostFileNotFound, match="does not exist"):
        await transport.read_text(str(tmp_path / "nope.yaml"))


@pytest.mark.asyncio
async def test_read_text_distinguishes_unreadable_from_absent(tmp_path):
    transport = _transport(tmp_path)
    target = tmp_path / "secret.yaml"
    target.write_text("http:\n")
    target.chmod(0)

    try:
        with pytest.raises(HostFileError) as caught:
            await transport.read_text(str(target))
        assert not isinstance(caught.value, HostFileNotFound)
    finally:
        target.chmod(0o644)  # so tmp_path cleanup can remove it


# --- ownership / permissions --------------------------------------------------


@pytest.mark.asyncio
async def test_write_text_applies_the_default_mode_to_a_created_file(tmp_path):
    transport = _transport(tmp_path)
    target = tmp_path / "configuration.yaml"

    await transport.write_text(str(target), "http:\n")

    assert stat.S_IMODE(target.stat().st_mode) == DEFAULT_FILE_MODE


@pytest.mark.asyncio
async def test_write_text_preserves_the_existing_files_mode_on_overwrite(tmp_path):
    transport = _transport(tmp_path)
    target = tmp_path / "configuration.yaml"
    target.write_text("original:\n")
    target.chmod(0o640)

    await transport.write_text(str(target), "new:\n")

    assert stat.S_IMODE(target.stat().st_mode) == 0o640


# --- raise sites reach applicable status with a local backend ----------------


def test_config_yaml_raise_site_is_applicable_with_local_backend_no_ssh_host(tmp_path, monkeypatch):
    monkeypatch.delenv("HOMEIQ_HA_SSH_HOST", raising=False)
    local = LocalHostFiles(LocalTarget(config_dir=str(tmp_path)))
    recipe = HttpLoginThresholdRecipe(host_files=local, path=str(tmp_path / "configuration.yaml"))

    # No raise: a configured local transport is not "no write path".
    assert recipe._transport is local


def test_zha_quirks_raise_site_is_applicable_with_local_backend_no_ssh_host(tmp_path, monkeypatch):
    monkeypatch.delenv("HOMEIQ_HA_SSH_HOST", raising=False)
    local = LocalHostFiles(LocalTarget(config_dir=str(tmp_path)))
    recipe = AqaraFP1EQuirkRecipe(host_files=local, config_path=str(tmp_path / "configuration.yaml"))

    assert recipe._transport is local
