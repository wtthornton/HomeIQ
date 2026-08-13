"""Preflight env guard behavior (TAP-5902).

Runs scripts/preflight-env.sh against synthetic manifest/.env pairs via its
PREFLIGHT_* seams — the real .env is never read by these tests.
"""

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "preflight-env.sh"

MANIFEST = (
    "# test manifest\n"
    "API_KEY\trequired\tshared service auth\n"
    "WATTTIME_USERNAME\tconditional\tcarbon feed\n"
)


def run_preflight(tmp_path: Path, env_text: str, manifest_text: str = MANIFEST):
    manifest = tmp_path / "env.required"
    manifest.write_text(manifest_text)
    env_file = tmp_path / "dotenv"
    env_file.write_text(env_text)
    return subprocess.run(
        ["bash", str(SCRIPT)],
        env={
            "PATH": "/usr/bin:/bin",
            "PREFLIGHT_MANIFEST": str(manifest),
            "PREFLIGHT_ENV_FILE": str(env_file),
        },
        capture_output=True,
        text=True,
        check=False,
    )


def test_missing_required_key_fails_and_names_it(tmp_path):
    result = run_preflight(tmp_path, "OTHER=x\n")
    assert result.returncode == 1
    assert "API_KEY" in result.stderr
    assert "x" not in result.stderr, "values must never be printed"


def test_empty_required_key_fails(tmp_path):
    result = run_preflight(tmp_path, "API_KEY=\n")
    assert result.returncode == 1
    assert "API_KEY" in result.stderr


def test_present_required_key_passes(tmp_path):
    result = run_preflight(tmp_path, "API_KEY=some-value\n")
    assert result.returncode == 0
    assert "some-value" not in result.stdout + result.stderr, "values must never be printed"


def test_empty_conditional_key_warns_but_passes(tmp_path):
    result = run_preflight(tmp_path, "API_KEY=some-value\nWATTTIME_USERNAME=\n")
    assert result.returncode == 0
    assert "WATTTIME_USERNAME" in result.stderr


def test_malformed_manifest_is_a_hard_error(tmp_path):
    result = run_preflight(tmp_path, "API_KEY=x\n", manifest_text="API_KEY only-one-field\n")
    assert result.returncode == 2


def test_committed_manifest_stays_coherent_with_template():
    result = subprocess.run(
        ["bash", str(SCRIPT), "--ci"],
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 0, result.stderr
