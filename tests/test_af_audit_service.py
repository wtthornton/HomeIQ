"""Tests for scripts/af_audit_service.py.

Focused on the parts that actually broke during development: the AgentForge
response shapes (which differ from the kit docs) and the budget/exit-code logic
that decides whether CI passes.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = REPO_ROOT / "scripts" / "af_audit_service.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("af_audit_service", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["af_audit_service"] = module
    spec.loader.exec_module(module)
    return module


af = _load_module()


class TestRequireHttpUrl:
    """B310 mitigation: urlopen honours file:/, so the scheme must be checked."""

    @pytest.mark.parametrize("url", ["http://localhost:8010", "https://af.example.com/health"])
    def test_allows_http_schemes(self, url):
        assert af.require_http_url(url) == url

    @pytest.mark.parametrize("url", ["file:///etc/passwd", "ftp://host/x", "gopher://host"])
    def test_rejects_other_schemes(self, url):
        with pytest.raises(SystemExit, match="Refusing non-HTTP URL"):
            af.require_http_url(url)


class TestCollectSource:
    def test_marks_each_file_with_its_relative_path(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "a.py").write_text("print('a')\n")

        source, count = af.collect_source(tmp_path, "*.py", max_bytes=10_000)

        assert count == 1
        assert "=== FILE: src/a.py ===" in source
        assert "print('a')" in source

    def test_skips_vendor_and_cache_directories(self, tmp_path):
        (tmp_path / "node_modules").mkdir()
        (tmp_path / "node_modules" / "dep.py").write_text("x = 1\n")
        (tmp_path / "__pycache__").mkdir()
        (tmp_path / "__pycache__" / "c.py").write_text("x = 2\n")
        (tmp_path / "real.py").write_text("x = 3\n")

        source, count = af.collect_source(tmp_path, "*.py", max_bytes=10_000)

        assert count == 1
        assert "real.py" in source
        assert "dep.py" not in source

    def test_stops_before_exceeding_budget_without_truncating_a_file(self, tmp_path):
        # Whole files only: a half-file would give the auditor wrong line numbers.
        (tmp_path / "a.py").write_text("a" * 500)
        (tmp_path / "b.py").write_text("b" * 500)

        source, count = af.collect_source(tmp_path, "*.py", max_bytes=600)

        assert count == 1
        assert len(source) <= 600
        assert "b" * 500 not in source

    def test_reports_zero_when_nothing_matches(self, tmp_path):
        (tmp_path / "readme.md").write_text("nope\n")
        source, count = af.collect_source(tmp_path, "*.py", max_bytes=10_000)
        assert (source, count) == ("", 0)


class TestWaitForRun:
    """The run poll nests state under 'run'; outputs live on a separate endpoint.

    Getting this wrong produced state=None and a spurious failure, so it is
    pinned here against the shapes observed from AgentForge 4.56.1.
    """

    def test_reads_nested_run_state_and_fetches_outputs(self, monkeypatch):
        responses = {
            "http://af/workflows/runs/r1": {"run": {"state": "complete"}},
            "http://af/workflows/runs/r1/outputs": {
                "state": "complete",
                "node_outputs": {"decide": {"decision": "ship"}},
                "total_cost_usd": 0.25,
            },
        }
        monkeypatch.setattr(af, "get_json", lambda url, _key, **_kwargs: responses[url])

        state, outputs, cost = af.wait_for_run("http://af", "r1", "afp_x", timeout_s=5)

        assert state == "complete"
        assert outputs["decide"]["decision"] == "ship"
        assert cost == 0.25

    def test_polls_while_non_terminal(self, monkeypatch):
        states = ["pending", "running", "complete"]
        calls = {"n": 0}

        def fake_get(url, _key, **_kwargs):
            if url.endswith("/outputs"):
                return {"node_outputs": {}, "total_cost_usd": 0}
            state = states[min(calls["n"], len(states) - 1)]
            calls["n"] += 1
            return {"run": {"state": state}}

        monkeypatch.setattr(af, "get_json", fake_get)
        monkeypatch.setattr(af.time, "sleep", lambda _: None)

        state, _, _ = af.wait_for_run("http://af", "r1", "afp_x", timeout_s=60)

        assert state == "complete"
        assert calls["n"] == 3

    def test_treats_complete_not_success_as_terminal(self):
        # AgentForge never emits "success"; asserting on it silently hangs.
        assert af.NON_TERMINAL_STATES.isdisjoint({"complete", "success"})
        assert sorted(af.NON_TERMINAL_STATES) == ["pending", "running"]


class TestDiscoverChangedServices:
    def test_maps_changed_files_to_two_level_service_dirs(self, monkeypatch):
        diff = "\n".join(
            [
                "domains/core-platform/data-api/src/app.py",
                "domains/core-platform/data-api/README.md",
                "domains/automation-core/ai-query-service/main.py",
                "domains/stray-file.txt",
                "scripts/unrelated.py",
            ]
        )
        monkeypatch.setattr(af.shutil, "which", lambda _name: "/usr/bin/git")
        monkeypatch.setattr(
            af.subprocess,
            "run",
            lambda *_a, **_k: argparse.Namespace(returncode=0, stdout=diff, stderr=""),
        )

        services = af.discover_changed_services("origin/master")

        assert services == [
            "domains/automation-core/ai-query-service",
            "domains/core-platform/data-api",
        ]

    def test_fails_loudly_when_base_ref_is_bad(self, monkeypatch):
        monkeypatch.setattr(af.shutil, "which", lambda _name: "/usr/bin/git")
        monkeypatch.setattr(
            af.subprocess,
            "run",
            lambda *_a, **_k: argparse.Namespace(returncode=128, stdout="", stderr="bad revision"),
        )
        with pytest.raises(SystemExit, match="bad revision"):
            af.discover_changed_services("nope")


class TestResolveTargets:
    def _args(self, **kwargs):
        base = {"service_path": [], "changed_only": None, "max_services": 10}
        base.update(kwargs)
        return argparse.Namespace(**base)

    def test_caps_at_max_services(self, capsys):
        args = self._args(service_path=[f"domains/g/s{i}" for i in range(5)], max_services=2)

        targets = af.resolve_targets(args)

        assert len(targets) == 2
        # A capped run must say what it dropped — silent truncation reads as
        # "everything was audited".
        assert "skipping 3" in capsys.readouterr().err

    def test_changed_only_supersedes_positional_paths(self, monkeypatch, capsys):
        monkeypatch.setattr(af, "discover_changed_services", lambda _ref: ["domains/g/changed"])
        args = self._args(service_path=["domains/g/explicit"], changed_only="origin/master")

        targets = af.resolve_targets(args)

        assert targets == ["domains/g/changed"]
        assert "supersedes" in capsys.readouterr().err


class TestResolveApiKey:
    def test_prefers_repo_dotenv_over_polluted_global(self, monkeypatch, tmp_path):
        # The real bug this guards: a truncated machine-global AGENTFORGE_API_KEY
        # exported by unrelated services shadows this repo's working key.
        env_file = tmp_path / ".env"
        env_file.write_text("OTHER=1\nAGENTFORGE_API_KEY=afp_the_real_one\n")
        monkeypatch.setattr(af, "REPO_ROOT", tmp_path)
        monkeypatch.setenv("AGENTFORGE_API_KEY", "afp_new")

        assert af.resolve_api_key() == "afp_the_real_one"

    def test_falls_back_to_environment_when_no_dotenv(self, monkeypatch, tmp_path):
        monkeypatch.setattr(af, "REPO_ROOT", tmp_path)
        monkeypatch.setenv("AGENTFORGE_API_KEY", "afp_from_env")

        assert af.resolve_api_key() == "afp_from_env"

    def test_raises_when_no_key_anywhere(self, monkeypatch, tmp_path):
        monkeypatch.setattr(af, "REPO_ROOT", tmp_path)
        monkeypatch.delenv("AGENTFORGE_API_KEY", raising=False)

        with pytest.raises(SystemExit, match="No AGENTFORGE_API_KEY"):
            af.resolve_api_key()


class TestExitCodes:
    """CI branches on these, so the mapping is load-bearing."""

    def test_constants_match_ci_contract(self):
        assert (af.EXIT_SHIP, af.EXIT_BLOCK, af.EXIT_ERROR) == (0, 1, 2)

    @pytest.mark.parametrize(
        ("outcomes", "expected"),
        [
            (["ship"], 0),
            (["ship", "ship"], 0),
            (["ship", "block"], 1),
            (["block"], 1),
            (["ship", "error"], 2),
            (["block", "error"], 2),
        ],
    )
    def test_worst_outcome_wins(self, outcomes, expected, monkeypatch, capsys):
        records = [{"service_path": f"s{i}", "outcome": o, "cost_usd": 0.0} for i, o in enumerate(outcomes)]
        monkeypatch.setattr(af, "resolve_targets", lambda _args: [r["service_path"] for r in records])
        monkeypatch.setattr(af, "resolve_api_key", lambda: "afp_x")
        monkeypatch.setattr(af, "audit_one", lambda path, _key, _args: next(r for r in records if r["service_path"] == path))
        monkeypatch.setattr(sys, "argv", ["af_audit_service.py", "domains/g/s"])

        assert af.main() == expected
        capsys.readouterr()

    def test_stops_once_max_spend_is_exceeded(self, monkeypatch, capsys):
        audited: list[str] = []

        def fake_audit(path, _key, _args):
            audited.append(path)
            return {"service_path": path, "outcome": "ship", "cost_usd": 3.0}

        monkeypatch.setattr(af, "resolve_targets", lambda _args: ["a", "b", "c"])
        monkeypatch.setattr(af, "resolve_api_key", lambda: "afp_x")
        monkeypatch.setattr(af, "audit_one", fake_audit)
        monkeypatch.setattr(sys, "argv", ["af_audit_service.py", "a", "--max-spend", "5.0"])

        af.main()

        # First run costs 3.0 (under 5.0), second pushes to 6.0, third is skipped.
        assert audited == ["a", "b"]
        assert "not audited" in capsys.readouterr().err


class TestJsonOutput:
    def test_writes_total_cost_and_results(self, monkeypatch, tmp_path):
        out = tmp_path / "report.json"
        monkeypatch.setattr(af, "resolve_targets", lambda _args: ["domains/g/s"])
        monkeypatch.setattr(af, "resolve_api_key", lambda: "afp_x")
        monkeypatch.setattr(
            af,
            "audit_one",
            lambda path, _key, _args: {"service_path": path, "outcome": "ship", "cost_usd": 0.12},
        )
        monkeypatch.setattr(sys, "argv", ["af_audit_service.py", "domains/g/s", "--json", str(out)])

        af.main()

        payload = json.loads(out.read_text())
        assert payload["total_cost_usd"] == pytest.approx(0.12)
        assert payload["results"][0]["outcome"] == "ship"
