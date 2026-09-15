"""Bind-mount sweep behaviour (TAP-7646).

Runs scripts/check-bind-mounts.py against synthetic `docker inspect` JSON via
the BIND_MOUNT_CHECK_DOCKER_JSON seam -- the real docker daemon is never
called by these tests.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "check-bind-mounts.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("check_bind_mounts", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def container(name: str, sources: list[str], *, mount_type: str = "bind") -> dict:
    return {
        "Name": f"/{name}",
        "Mounts": [{"Type": mount_type, "Source": src, "Destination": "/x"} for src in sources],
    }


def run_check(tmp_path: Path, guarded_root: Path, docker_json: object):
    fixture = tmp_path / "docker-inspect.json"
    fixture.write_text(json.dumps(docker_json), encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(guarded_root)],
        capture_output=True,
        text=True,
        env={
            "PATH": "/usr/bin:/bin",
            "BIND_MOUNT_CHECK_DOCKER_JSON": str(fixture),
        },
    )


def test_positive_control_all_sources_outside_repo_passes(tmp_path):
    repo = tmp_path / "HomeIQ"
    repo.mkdir()
    outside = tmp_path / "deploy-root"
    outside.mkdir()
    result = run_check(tmp_path, repo, [container("homeiq-data-api", [str(outside)])])
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout
    assert "examined 1 bind source" in result.stdout


def test_negative_control_repo_internal_source_fails(tmp_path):
    repo = tmp_path / "HomeIQ"
    repo.mkdir()
    inside = repo / "libs" / "data-api" / "src"
    inside.mkdir(parents=True)
    result = run_check(tmp_path, repo, [container("homeiq-data-api", [str(inside)])])
    assert result.returncode == 1
    assert "FAIL" in result.stderr
    assert "homeiq-data-api" in result.stderr
    assert str(inside) in result.stderr


def test_empty_container_list_fails_inspection_not_ok(tmp_path):
    repo = tmp_path / "HomeIQ"
    repo.mkdir()
    result = run_check(tmp_path, repo, [])
    assert result.returncode == 2
    assert "INSPECTION FAILED" in result.stderr
    assert "containers=0" in result.stderr


def test_zero_bind_sources_fails_inspection_not_ok(tmp_path):
    """Containers exist but none have bind mounts -- also treated as inspecting nothing."""
    repo = tmp_path / "HomeIQ"
    repo.mkdir()
    result = run_check(tmp_path, repo, [container("homeiq-grafana", [])])
    assert result.returncode == 2
    assert "INSPECTION FAILED" in result.stderr
    assert "bind sources=0" in result.stderr


def test_docker_inspect_returning_object_instead_of_array_is_rejected(tmp_path):
    """The exact hazard called out in the orchestrator prompt: an object read as if it had no mounts."""
    repo = tmp_path / "HomeIQ"
    repo.mkdir()
    fixture = tmp_path / "docker-inspect.json"
    fixture.write_text(json.dumps({"Mounts": []}), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(repo)],
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin", "BIND_MOUNT_CHECK_DOCKER_JSON": str(fixture)},
    )
    assert result.returncode == 2
    assert "INSPECTION FAILED" in result.stderr


def test_non_bind_mounts_are_not_counted_as_sources(tmp_path):
    repo = tmp_path / "HomeIQ"
    repo.mkdir()
    inside = repo / "data"
    inside.mkdir()
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    containers = [
        {
            "Name": "/homeiq-postgres",
            "Mounts": [
                {
                    "Type": "volume",
                    "Source": str(inside),
                    "Destination": "/var/lib/postgresql/data",
                },
                {"Type": "bind", "Source": str(outside), "Destination": "/etc/conf"},
            ],
        }
    ]
    result = run_check(tmp_path, repo, containers)
    assert result.returncode == 0, result.stderr
    assert "examined 1 bind source" in result.stdout


def test_symlinked_source_is_resolved_before_comparison(tmp_path):
    """A mount source that is a symlink into the repo must not escape detection via its literal string."""
    repo = tmp_path / "HomeIQ"
    data_dir = repo / "libs" / "rag-service" / "data"
    data_dir.mkdir(parents=True)
    link = tmp_path / "outside-link"
    link.symlink_to(data_dir)
    result = run_check(tmp_path, repo, [container("homeiq-rag-service", [str(link)])])
    assert result.returncode == 1
    assert "homeiq-rag-service" in result.stderr
    assert str(data_dir) in result.stderr


def test_sibling_directory_sharing_a_prefix_is_not_a_false_positive(tmp_path):
    """`/HomeIQ-other` must not be treated as inside `/HomeIQ`."""
    repo = tmp_path / "HomeIQ"
    repo.mkdir()
    sibling = tmp_path / "HomeIQ-other"
    sibling.mkdir()
    result = run_check(tmp_path, repo, [container("homeiq-admin", [str(sibling)])])
    assert result.returncode == 0, result.stderr


def test_repo_root_defaults_to_git_rev_parse_when_omitted():
    """With no positional argument, the script asks git for the toplevel of its own cwd."""
    fixture_dir = Path(__file__).resolve().parent
    fixture = fixture_dir / "_bind_mount_git_default_fixture.json"
    outside = fixture_dir.parent.parent  # definitely outside this repo checkout
    fixture.write_text(json.dumps([container("homeiq-data-api", [str(outside)])]), encoding="utf-8")
    try:
        result = subprocess.run(
            [sys.executable, str(SCRIPT)],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            env={"PATH": "/usr/bin:/bin", "BIND_MOUNT_CHECK_DOCKER_JSON": str(fixture)},
        )
        assert result.returncode == 0, result.stderr
        assert str(REPO_ROOT) in result.stdout
    finally:
        fixture.unlink()


def test_bind_sources_rejects_non_list_mounts_field():
    module = _load_module()
    import pytest

    with pytest.raises(RuntimeError, match="not an array"):
        module.bind_sources({"Name": "/x", "Mounts": {"not": "a list"}})


def test_is_inside_true_for_root_itself(tmp_path):
    module = _load_module()
    assert module.is_inside(tmp_path, tmp_path) is True


def test_is_inside_false_for_unrelated_path(tmp_path):
    module = _load_module()
    other = tmp_path.parent / "unrelated"
    assert module.is_inside(other, tmp_path) is False
