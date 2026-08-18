"""Container-count ratchet behaviour (TAP-5303).

Runs scripts/check-container-budget.py against synthetic compose trees via its
CONTAINER_BUDGET_* seams -- the repo's real compose files and baseline are never
read by these tests.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "check-container-budget.py"


def build_tree(tmp_path: Path, services: dict[str, dict], *, ceiling: int, memory: int = 100):
    """Write a one-domain compose tree plus a baseline recording `ceiling` services."""
    domain = tmp_path / "domains" / "example"
    domain.mkdir(parents=True)
    (domain / "compose.yml").write_text(yaml.safe_dump({"services": services}), encoding="utf-8")
    baseline = tmp_path / "container-budget.json"
    production = [
        n for n, b in services.items() if "production" in (b.get("profiles") or ["production"])
    ]
    baseline.write_text(
        json.dumps(
            {
                "target": {"services": 1, "memory_mib": 50, "ref": "TAP-5283"},
                "ceiling": {"services": ceiling, "memory_mib": memory},
                "measured": {
                    "services": sorted(production),
                    "memory_mib": memory,
                    "containers": len(production),
                    "at": "2026-08-18",
                },
            }
        ),
        encoding="utf-8",
    )
    return baseline


def run_check(tmp_path: Path, baseline: Path):
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        capture_output=True,
        text=True,
        env={
            "PATH": "/usr/bin:/bin",
            "CONTAINER_BUDGET_ROOT": str(tmp_path),
            "CONTAINER_BUDGET_FILE": str(baseline),
        },
    )


SVC = {"alpha": {"image": "a"}, "beta": {"image": "b"}}


def test_matching_count_passes(tmp_path):
    baseline = build_tree(tmp_path, SVC, ceiling=2)
    result = run_check(tmp_path, baseline)
    assert result.returncode == 0, result.stderr
    assert "2 production services" in result.stdout


def test_added_service_fails_and_is_named(tmp_path):
    baseline = build_tree(tmp_path, SVC, ceiling=2)
    compose = tmp_path / "domains" / "example" / "compose.yml"
    doc = yaml.safe_load(compose.read_text())
    doc["services"]["gamma"] = {"image": "c"}
    compose.write_text(yaml.safe_dump(doc), encoding="utf-8")

    result = run_check(tmp_path, baseline)
    assert result.returncode == 1
    assert "exceeds the ceiling" in result.stderr
    assert "gamma" in result.stderr
    assert "alpha" not in result.stderr


def test_removed_service_fails_so_the_ratchet_cannot_go_stale(tmp_path):
    baseline = build_tree(tmp_path, SVC, ceiling=2)
    compose = tmp_path / "domains" / "example" / "compose.yml"
    compose.write_text(yaml.safe_dump({"services": {"alpha": {"image": "a"}}}), encoding="utf-8")

    result = run_check(tmp_path, baseline)
    assert result.returncode == 1
    assert "BELOW the ceiling" in result.stderr
    assert "beta" in result.stderr


def test_non_production_profile_is_not_counted(tmp_path):
    services = dict(SVC, gamma={"image": "c", "profiles": ["dev"]})
    baseline = build_tree(tmp_path, services, ceiling=2)
    result = run_check(tmp_path, baseline)
    assert result.returncode == 0, result.stderr


def test_service_without_profiles_key_is_counted(tmp_path):
    """A service with no `profiles` runs under every profile, so it counts."""
    services = {"alpha": {"image": "a"}, "beta": {"image": "b", "profiles": ["production", "dev"]}}
    baseline = build_tree(tmp_path, services, ceiling=2)
    result = run_check(tmp_path, baseline)
    assert result.returncode == 0, result.stderr


def test_recorded_memory_over_ceiling_fails(tmp_path):
    baseline = build_tree(tmp_path, SVC, ceiling=2, memory=100)
    doc = json.loads(baseline.read_text())
    doc["measured"]["memory_mib"] = 101
    baseline.write_text(json.dumps(doc), encoding="utf-8")

    result = run_check(tmp_path, baseline)
    assert result.returncode == 1
    assert "memory footprint 101 MiB exceeds" in result.stderr


@pytest.mark.parametrize(
    ("usage", "expected"),
    [
        ("512B / 1GiB", 0),
        ("1024KiB / 1GiB", 1),
        ("128.5MiB / 1GiB", 128.5),
        ("1.5GiB / 4GiB", 1536),
    ],
)
def test_docker_stats_units_parse(usage, expected):
    import importlib.util

    spec = importlib.util.spec_from_file_location("container_budget", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module._mib(usage) == pytest.approx(expected, abs=0.01)


def test_unparseable_memory_value_raises():
    import importlib.util

    spec = importlib.util.spec_from_file_location("container_budget", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with pytest.raises(ValueError, match="cannot parse"):
        module._mib("lots / 1GiB")
