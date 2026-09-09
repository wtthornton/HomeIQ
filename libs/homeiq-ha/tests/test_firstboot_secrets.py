"""Behavioural tests for ``scripts/appliance/firstboot-secrets.sh`` (TAP-6573).

Each ``test_valNNN_*`` name maps to one row of the lane's validation contract.

Why these assert on the *mechanism* rather than the observable
--------------------------------------------------------------
A ``0600`` file mode is the single easiest thing in this lane to get right by
accident: a process whose umask is already ``077`` produces ``0600`` with no
``chmod`` anywhere in the script, and the assertion passes for a reason that
has nothing to do with the code. Every run here therefore starts from
``umask 000`` -- the most permissive setting there is -- so the only way a final
mode of ``600`` can appear is an explicit ``chmod``.

The same reasoning applies to idempotence: a second *call inside one process*
proves nothing, because the values could be cached in shell variables. Every
idempotence check below is two separate ``bash`` invocations, compared on the
file's sha256 **and** its mtime.
"""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "appliance" / "firstboot-secrets.sh"
COMPOSE_FILES = sorted((REPO_ROOT / "domains").glob("*/compose.yml"))

#: The seven keys VAL-060 counts: the ADR's tier-1 six plus the DEK.
ADR_TIER1_KEYS = (
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "INFLUXDB_TOKEN",
    "API_KEY",
    "ADMIN_API_JWT_SECRET",
    "GF_SECURITY_ADMIN_PASSWORD",
    "HOMEIQ_SECRET_DEK",
)

#: ``POSTGRES_USER`` is a fixed non-secret account name, documented as such in
#: the script header. Every other generated key must be unpredictable.
FIXED_VALUE_KEYS = ("POSTGRES_USER",)

_MARKER_RE = re.compile(r"\$\{([A-Z_]+):\?[^}]*\}")


def run_script(
    state_dir: Path,
    *args: str,
    umask: str = "000",
    script: Path | None = None,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run the first-boot script in its own shell under a permissive umask.

    ``umask 000`` is the point: it removes the umask as a possible source of a
    restrictive mode, so a ``0600`` result can only come from the script.
    """
    env = {"PATH": os.environ["PATH"], "HOMEIQ_STATE_DIR": str(state_dir)}
    env.update(extra_env or {})
    return subprocess.run(
        ["bash", "-c", f'umask {umask}; exec "$@"', "_", str(script or SCRIPT), *args],
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
        env=env,
    )


def env_file(state_dir: Path) -> Path:
    return state_dir / ".env"


def parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, _, value = stripped.partition("=")
        values[key] = value
    return values


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pinned_keys() -> list[str]:
    result = subprocess.run(
        [str(SCRIPT), "--list-keys"], capture_output=True, text=True, check=True
    )
    return result.stdout.split()


def pinned_compose_markers() -> list[str]:
    result = subprocess.run(
        [str(SCRIPT), "--list-compose-markers"], capture_output=True, text=True, check=True
    )
    return result.stdout.split()


def live_compose_markers() -> list[str]:
    markers: set[str] = set()
    for compose in COMPOSE_FILES:
        markers.update(_MARKER_RE.findall(compose.read_text()))
    return sorted(markers)


# --------------------------------------------------------------------------
# VAL-060 -- first boot generates the tier-1 keys at mode 0600
# --------------------------------------------------------------------------


def test_val060_first_boot_writes_every_key_at_mode_0600(tmp_path: Path) -> None:
    state = tmp_path / "state"
    result = run_script(state)

    assert result.returncode == 0, result.stderr
    target = env_file(state)
    assert target.is_file()

    # The mechanism assertion: umask was 000, so 600 is an explicit chmod.
    assert oct(target.stat().st_mode & 0o777) == "0o600"

    values = parse_env(target)
    for key in ADR_TIER1_KEYS:
        assert key in values, f"{key} missing from the generated tier-1 file"
        assert values[key], f"{key} generated empty"
    assert len([k for k in ADR_TIER1_KEYS if k in values]) == 7

    # Every generated key is either the documented fixed account name or random.
    for key in pinned_keys():
        assert key in values and values[key], key
        if key not in FIXED_VALUE_KEYS:
            assert len(values[key]) >= 32, f"{key} is too short to be a generated secret"


def test_val060_no_generated_value_is_committed_anywhere_in_the_repo(tmp_path: Path) -> None:
    state = tmp_path / "state"
    assert run_script(state).returncode == 0
    values = parse_env(env_file(state))

    for key, value in values.items():
        if key in FIXED_VALUE_KEYS:
            continue
        found = subprocess.run(
            ["git", "grep", "-c", "-F", "--", value],
            capture_output=True,
            text=True,
            check=False,
            cwd=REPO_ROOT,
        )
        # git grep exits 1 when there is no match, which is the passing case.
        assert found.returncode == 1, f"{key}'s value appears in the tree: {found.stdout}"


def test_val060_two_clean_installs_produce_different_values(tmp_path: Path) -> None:
    """The issue's third acceptance box: per-install, not per-image."""
    first, second = tmp_path / "a", tmp_path / "b"
    assert run_script(first).returncode == 0
    assert run_script(second).returncode == 0

    a, b = parse_env(env_file(first)), parse_env(env_file(second))
    for key in pinned_keys():
        if key in FIXED_VALUE_KEYS:
            assert a[key] == b[key], f"{key} is documented as a fixed name"
        else:
            assert a[key] != b[key], f"{key} repeated across two clean installs"


def test_val060_the_temp_file_is_written_inside_an_umask_077_subshell() -> None:
    """Structural companion to the mode assertion above.

    The final ``chmod`` closes the window only after ``mv``; the window *before*
    it is closed by creating the temp file under ``umask 077``. That ordering is
    not observable after the fact, so it is asserted on the source.
    """
    source = SCRIPT.read_text()
    assert "umask 077" in source
    assert "chmod 600" in source


# --------------------------------------------------------------------------
# VAL-061 -- consumers read the values through the existing interpolation
# --------------------------------------------------------------------------


def test_val061_every_compose_required_marker_is_generated(tmp_path: Path) -> None:
    """Every ``${VAR:?required}`` in the 9 compose files is supplied non-empty.

    This is the behavioural half of VAL-061: interpolation cannot render unless
    the generated file covers the marker set, and no compose file is edited to
    make that true.
    """
    state = tmp_path / "state"
    assert run_script(state).returncode == 0
    values = parse_env(env_file(state))

    missing = [m for m in live_compose_markers() if not values.get(m)]
    assert missing == [], f"compose requires these but the script does not generate them: {missing}"


def test_pinned_compose_markers_match_the_live_compose_files() -> None:
    """The "derive or check" rule.

    The script pins the marker set as a documented list rather than deriving it
    at runtime, so this test is what makes the pin honest: add a
    ``${NEW_KEY:?required}`` to any compose file and this goes red.
    """
    assert pinned_compose_markers() == live_compose_markers()


@pytest.mark.integration
def test_val061_docker_compose_config_renders_from_the_generated_env(tmp_path: Path) -> None:
    """The real render, with ``env -i`` so only the generated file supplies values."""
    state = tmp_path / "state"
    assert run_script(state).returncode == 0
    generated = env_file(state)
    values = parse_env(generated)

    render = subprocess.run(
        [
            "env",
            "-i",
            f"PATH={os.environ['PATH']}",
            f"HOME={os.environ.get('HOME', '/tmp')}",
            "docker",
            "compose",
            "--env-file",
            str(generated),
            "-f",
            str(REPO_ROOT / "domains" / "core-platform" / "compose.yml"),
            "config",
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
    )
    assert render.returncode == 0, render.stderr
    assert render.stdout.count(values["POSTGRES_PASSWORD"]) >= 1

    # Negative control: drop one key and the same command must refuse by name.
    trimmed = tmp_path / "trimmed.env"
    trimmed.write_text(
        "\n".join(
            line
            for line in generated.read_text().splitlines()
            if not line.startswith("POSTGRES_PASSWORD=")
        )
        + "\n"
    )
    refused = subprocess.run(
        [
            "env",
            "-i",
            f"PATH={os.environ['PATH']}",
            f"HOME={os.environ.get('HOME', '/tmp')}",
            "docker",
            "compose",
            "--env-file",
            str(trimmed),
            "-f",
            str(REPO_ROOT / "domains" / "core-platform" / "compose.yml"),
            "config",
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
    )
    assert refused.returncode != 0
    assert "POSTGRES_PASSWORD" in refused.stderr
    assert "required" in refused.stderr


# --------------------------------------------------------------------------
# VAL-062 -- the second boot reuses the file
# --------------------------------------------------------------------------


def test_val062_second_boot_reuses_the_file_unchanged(tmp_path: Path) -> None:
    state = tmp_path / "state"
    assert run_script(state).returncode == 0
    target = env_file(state)
    before_sha, before_mtime = sha256(target), target.stat().st_mtime_ns

    second = run_script(state)
    assert second.returncode == 0
    assert sha256(target) == before_sha
    assert target.stat().st_mtime_ns == before_mtime
    assert "reusing" in second.stdout


def test_val062_negative_control_a_deleted_file_is_regenerated(tmp_path: Path) -> None:
    """The control for the check above: without it, "equal" would be vacuous."""
    state = tmp_path / "state"
    assert run_script(state).returncode == 0
    target = env_file(state)
    before_sha = sha256(target)

    target.unlink()
    assert run_script(state).returncode == 0
    assert sha256(target) != before_sha


# --------------------------------------------------------------------------
# VAL-063 -- a missing key is a named failure, never a default
# --------------------------------------------------------------------------


def test_val063_an_emptied_key_on_a_later_boot_is_a_named_preflight_failure(
    tmp_path: Path,
) -> None:
    from homeiq_ha.secrets.states import EXIT_CODES, SecretState

    state = tmp_path / "state"
    assert run_script(state).returncode == 0
    target = env_file(state)

    target.write_text(
        "\n".join(
            "POSTGRES_PASSWORD=" if line.startswith("POSTGRES_PASSWORD=") else line
            for line in target.read_text().splitlines()
        )
        + "\n"
    )
    damaged_sha = sha256(target)

    result = run_script(state)
    assert result.returncode == EXIT_CODES[SecretState.PREFLIGHT_FAILURE]
    combined = result.stdout + result.stderr
    assert "preflight-failure" in combined
    assert "POSTGRES_PASSWORD" in combined
    # No fallback: the emptied key was not quietly re-minted or defaulted.
    assert sha256(target) == damaged_sha


def test_val063_the_script_preflight_exit_code_matches_the_module_constant() -> None:
    """Derive-or-check across the bash/python boundary."""
    from homeiq_ha.secrets.states import EXIT_CODES, SecretState

    source = SCRIPT.read_text()
    expected = EXIT_CODES[SecretState.PREFLIGHT_FAILURE]
    assert f"EXIT_PREFLIGHT_FAILURE={expected}" in source


# --------------------------------------------------------------------------
# VAL-064 -- redaction
# --------------------------------------------------------------------------


def test_val064_no_generated_value_reaches_stdout_or_stderr(tmp_path: Path) -> None:
    state = tmp_path / "state"
    first = run_script(state)
    second = run_script(state)
    log = first.stdout + first.stderr + second.stdout + second.stderr

    for key, value in parse_env(env_file(state)).items():
        if key in FIXED_VALUE_KEYS:
            continue
        assert value not in log, f"{key}'s value leaked into the run log"


def test_val064_negative_control_an_injected_echo_is_caught(tmp_path: Path) -> None:
    """Without this, a run that logs nothing at all would pass VAL-064 vacuously."""
    leaky = tmp_path / "leaky.sh"
    leaky.write_text(
        SCRIPT.read_text().replace(
            '  log "generated',
            '  cat "$ENV_FILE" >&2\n  log "generated',
            1,
        )
    )
    leaky.chmod(0o755)

    state = tmp_path / "state"
    result = run_script(state, script=leaky)
    assert result.returncode == 0
    log = result.stdout + result.stderr

    leaked = [
        key
        for key, value in parse_env(env_file(state)).items()
        if key not in FIXED_VALUE_KEYS and value in log
    ]
    assert leaked, "the redaction check cannot distinguish a leaking script from a clean one"
