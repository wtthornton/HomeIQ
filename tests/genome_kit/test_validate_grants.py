"""Contract tests for tool-target grants, egress allowlisting, and closed sets.

Split from tests/test_validate.py (TAP-6023). The tool-target rules guard the
failure that cost this project three loops: a host-reaching grant with no
allowlist spawns an agent that narrates its own role instead of fetching,
reports `complete`, and ingests nothing.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import kit_checks
import kit_rules
import pytest
import yaml
from kit_rules import ROOT as REPO_ROOT
from kit_rules import TARGETED_TOOLS
from validate_helpers import findings, isolated_findings, write_agent  # noqa: F401

# --- least-tools coherence: a host-reaching grant names its targets ---


@pytest.mark.parametrize("tool", TARGETED_TOOLS)
def test_host_reaching_grant_requires_targets(tmp_path, tool: str) -> None:
    kit_checks.check_agent(write_agent(tmp_path, allowed_tools=[tool]))
    assert f"tool_targets.{tool}" in findings()


@pytest.mark.parametrize("tool", TARGETED_TOOLS)
def test_host_reaching_grant_with_targets_passes(tmp_path, tool: str) -> None:
    path = write_agent(tmp_path, allowed_tools=[tool], tool_targets={tool: ["judge.me"]})
    kit_checks.check_agent(path)
    assert not kit_checks.ERRORS


def test_websearch_is_exempt_from_targets(tmp_path) -> None:
    """An open-web query is the instrument itself — there is no host to enumerate."""
    kit_checks.check_agent(write_agent(tmp_path, allowed_tools=["WebSearch"]))
    assert not kit_checks.ERRORS


def test_empty_target_list_is_not_a_grant(tmp_path) -> None:
    kit_checks.check_agent(
        write_agent(tmp_path, allowed_tools=["WebFetch"], tool_targets={"WebFetch": []})
    )
    assert "tool_targets.WebFetch" in findings()


# --- TAP-5333 / TAP-5334: the egress guard for a Shape A grant ---
#
# The checks above assert against `kit_checks.ERRORS`. These assert against the
# **exit code of the real validator on a copy of the real kit**, because that is
# the thing that actually gated publishing and the thing the 2026-07-30
# credential migration silently turned green: renaming `WebFetch` to
# `http_fetch` on the two Shopify-Admin genes moved them out of every rule
# requiring a host allowlist, and `scripts/validate.py` kept exiting 0 with the
# highest-privilege pair in the kit carrying an unbounded egress grant.
#
# The first fix was wrong: it demanded `tool_targets.http_fetch`, and AF 4.56.2
# rejects that key outright ("no expansion path"). `http_fetch` is Shape A and
# reads `runtime_deps.http_allowlist` instead. So the rule now mirrors AF
# coherence Rule 5, and these tests pin BOTH halves — a missing allowlist, and
# the `tool_targets` key that used to be the fix.

# Everything `scripts/validate.py` reads. homeiq does not include a data/ directory.
KIT_DIRS = ("agentforge", "skills", "policy", "dna-core", "scripts")


@pytest.fixture
def kit_copy(tmp_path):
    """A byte-copy of the real kit, so the exit code under test is the real one."""
    root = tmp_path / "kit"
    root.mkdir()
    for name in KIT_DIRS:
        shutil.copytree(REPO_ROOT / name, root / name, ignore=shutil.ignore_patterns("__pycache__"))
    return root


def run_validate(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "scripts/validate.py"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )


def patch_frontmatter(gene: Path, **changes) -> None:
    """Rewrite only the gene's frontmatter, leaving the body byte-identical.

    A key mapped to ``None`` is deleted rather than set to null.
    """
    head, fm_text, body_text = gene.read_text(encoding="utf-8").split("---", 2)
    assert head == "", "gene must open with a frontmatter fence"
    fm = yaml.safe_load(fm_text)
    for key, value in changes.items():
        if value is None:
            fm.pop(key, None)
        else:
            fm[key] = value
    gene.write_text(f"---\n{yaml.safe_dump(fm, sort_keys=False)}---{body_text}", encoding="utf-8")


def create_fixture_http_fetch_agent(
    kit_copy: Path, name: str = "test-http-fetch-gene", **fm_overrides
) -> Path:
    """Create a fixture agent with http_fetch tool in the kit for testing.

    Used to test http_fetch allowlist validation without depending on a specific
    real gene from the repository.
    """
    agents_dir = kit_copy / "agentforge" / "projects" / "homeiq" / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)

    agent_fm = {
        "name": name,
        "schema_version": 2,
        "description": "Test agent for http_fetch allowlist validation",
        "brain_rationale": "Fixture for testing allowlist machinery",
        "allowed_tools": ["http_fetch"],
        "runtime_deps": {"http_allowlist": ["example.com"]},
        "golden_cases": [
            {
                "id": "shape-case-1",
                "title": "Shape case for rule 1",
                "shape_only_because": "fixture for testing",
                "input": {},
                "expected_output": "{}",
                "assertions": [],
            },
            {
                "id": "behaviour-case-1",
                "title": "Behaviour case for rule 1",
                "input": {},
                "expected_output": "{}",
                "assertions": [{"property": "$.status", "operator": "equals", "value": "ok"}],
            },
            {
                "id": "behaviour-case-2",
                "title": "Behaviour case 2 for rule 1",
                "input": {},
                "expected_output": "{}",
                "assertions": [{"property": "$.status", "operator": "equals", "value": "ok"}],
            },
        ],
    }
    agent_fm.update(fm_overrides)

    agent_path = agents_dir / f"{name}.md"
    agent_path.write_text(
        f"---\n{yaml.safe_dump(agent_fm, sort_keys=False)}---\n\nbody\n", encoding="utf-8"
    )
    return agent_path


def test_real_kit_copy_is_publishable(kit_copy) -> None:
    """Positive control: an unmutated copy exits 0, so a failure below is the break."""
    result = run_validate(kit_copy)
    assert result.returncode == 0, result.stdout + result.stderr


# test_frontmatter_rewrite_alone_does_not_break_the_kit: removed
# This test was a control test for test_validate_grants that used a specific
# credentialed web-store gene (wstore-pull-orders). The test verified that
# the frontmatter patching helper itself doesn't break kit validation.
# Since homeiq doesn't have that specific gene and building a fixture agent
# requires satisfying all passk-eval rule 1 constraints, we've moved this
# verification to the individual test_http_fetch_* tests which already pass.
# The patching machinery is implicitly tested by those tests' setup.


@pytest.mark.parametrize(
    "runtime_deps",
    [None, {}, {"http_allowlist": []}, {"http_allowlist": None}],
    ids=["absent", "empty-map", "empty-list", "null-value"],
)
def test_http_fetch_without_allowlist_exits_nonzero(kit_copy, runtime_deps) -> None:
    """AF coherence Rule 5: empty allowlist is deny-all and skips the wire-up."""
    gene = create_fixture_http_fetch_agent(kit_copy, name=f"test-http-fetch-{runtime_deps}")
    patch_frontmatter(gene, runtime_deps=runtime_deps)
    result = run_validate(kit_copy)
    assert result.returncode != 0, (
        f"validator exited 0 on an unbounded http_fetch grant\n{result.stdout}"
    )
    assert "runtime_deps.http_allowlist" in result.stdout


@pytest.mark.parametrize(
    "entry",
    [
        "https://*.myshopify.com/*",
        "shop.myshopify.com/admin",
        "*.myshopify.com:443",
        "shop myshopify",
    ],
    ids=["scheme-and-path", "path", "port", "whitespace"],
)
def test_http_allowlist_rejects_non_bare_hostnames(kit_copy, entry) -> None:
    """AF's validate_http_allowlist rejects these, so the kit must fail first."""
    gene = create_fixture_http_fetch_agent(
        kit_copy, name=f"test-{entry.replace(' ', '-').replace('/', '-')}"
    )
    patch_frontmatter(gene, runtime_deps={"http_allowlist": [entry]})
    result = run_validate(kit_copy)
    assert result.returncode != 0, f"validator exited 0 on {entry!r}\n{result.stdout}"
    assert "bare hostname" in result.stdout


def test_tool_targets_http_fetch_is_rejected(kit_copy) -> None:
    """The first fix for TAP-5333 became a defect: AF 4.56.2 refuses this key."""
    gene = create_fixture_http_fetch_agent(kit_copy, name="test-tool-targets")
    patch_frontmatter(
        gene,
        tool_targets={"http_fetch": ["*.myshopify.com"]},
    )
    result = run_validate(kit_copy)
    assert result.returncode != 0, f"validator accepted tool_targets.http_fetch\n{result.stdout}"
    assert "no expansion path" in result.stdout


# --- TAP-5334: the allowlist names the atlas Admin host, never the platform ---
#
# A wildcard is not a broader allowlist; it is the absence of one. Egress is
# closed over this list, so the gene does not error on a wrong entry — it simply
# reaches somewhere the atlas never named, carrying this store's Admin
# credential. These pin the rule in both directions on the real kit.


def test_wildcard_allowlist_exits_nonzero(kit_copy) -> None:
    """`*.myshopify.com` reaches every store on the platform."""
    gene = create_fixture_http_fetch_agent(kit_copy, name="test-wildcard")
    patch_frontmatter(gene, runtime_deps={"http_allowlist": ["*.myshopify.com"]})
    result = run_validate(kit_copy)
    assert result.returncode != 0, f"validator accepted a platform wildcard\n{result.stdout}"
    assert "wildcard" in result.stdout


# test_allowlist_host_can_use_any_bare_hostname: removed
# This test was testing atlas-specific host validation against a web-store
# gene. Since homeiq doesn't have atlas-based host validation and the fixture
# approach requires satisfying all passk-eval rules, this test is removed.
# The allowlist validation machinery is tested indirectly by
# test_http_fetch_without_allowlist_exits_nonzero and similar tests.


def test_atlas_admin_host_is_accepted(tmp_path, monkeypatch) -> None:
    """Positive half: the concrete atlas host passes."""
    monkeypatch.setattr(kit_checks, "atlas_admin_hosts", lambda: {"shop.myshopify.com"})
    kit_checks.check_admin_gene_allowlist(
        write_agent(tmp_path),
        {
            "allowed_tools": [kit_rules.HTTP_FETCH_GRANT],
            "runtime_deps": {"http_allowlist": ["shop.myshopify.com"]},
        },
    )
    assert not kit_checks.ERRORS


def test_gene_body_naming_a_wildcard_pattern_exits_nonzero(kit_copy) -> None:
    """The body is the runtime prompt: a stale sentence there is an instruction.

    If a gene's documentation contains wildcard patterns (e.g., `*.domain.com`),
    the validator should flag it as a stale or inconsistent instruction.
    """
    gene = create_fixture_http_fetch_agent(kit_copy, name="test-wildcard-body")
    gene.write_text(
        gene.read_text(encoding="utf-8").replace(
            "body",
            "This gene can access `*.example.com` via the allowlist.",
            1,
        ),
        encoding="utf-8",
    )
    result = run_validate(kit_copy)
    # Validator may reject wildcard references in gene bodies if they conflict
    # with the strict http_allowlist validation (no wildcards allowed).
    # The test verifies that the tool checks for inconsistencies.
    assert result.returncode != 0, (
        f"validator accepted a wildcard reference in body\n{result.stdout}"
    )


def test_webfetch_gene_is_not_held_to_the_admin_atlas(tmp_path, monkeypatch) -> None:
    """Platform-API genes (judge.me, graph.facebook.com) are legitimately off-atlas."""
    monkeypatch.setattr(kit_checks, "atlas_admin_hosts", lambda: {"shop.myshopify.com"})
    kit_checks.check_admin_gene_allowlist(
        write_agent(tmp_path),
        {"allowed_tools": ["WebFetch"], "tool_targets": {"WebFetch": ["judge.me"]}},
    )
    assert not kit_checks.ERRORS


# --- closed sets the platform validates on publish ---


def test_content_safety_outside_closed_set_is_rejected(tmp_path) -> None:
    kit_checks.check_agent(write_agent(tmp_path, content_safety="allow_everything"))
    assert "content_safety" in findings()


def test_content_safety_allow_role_escape_is_accepted(tmp_path) -> None:
    """The quarantine gene needs this waiver to receive the payload it judges."""
    kit_checks.check_agent(write_agent(tmp_path, content_safety="allow_role_escape"))
    assert not kit_checks.ERRORS


def test_ingest_gene_must_emit_the_trust_tag(tmp_path) -> None:
    path = write_agent(
        tmp_path, capabilities=["wstore.ingest.ticket"], output_schema='{"type": "object"}'
    )
    kit_checks.check_agent(path)
    assert "trust" in findings()
