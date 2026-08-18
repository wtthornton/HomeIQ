"""Contract tests for failure-sentence verifiability, golden-case coverage
reporting, species discovery, and fleet memory wiring (share_scope, hive
membership, the fleet group name).

Split from tests/test_validate.py (TAP-6023).
"""

from __future__ import annotations

from pathlib import Path

import kit_checks
import kit_rules
import pytest
import yaml
from kit_rules import AGENTS_DIR
from validate_helpers import AGENT_BASE, findings, isolated_findings, write_agent  # noqa: F401

# --- a gene must not be handed a failure sentence it cannot verify ---
#
# `wstore-pull-orders` carried its own required credential in the worked example
# for rule 6, paired with a "not vaulted" reason. On 2026-07-31 it emitted a
# near-verbatim copy while that credential was returning live Shopify data to
# `wstore-pull-analytics` in the same run, and orders.json answered HTTP 200 with
# an empty list. The digest believed it.
#
# Four ingest genes carry an example of this shape. Only this one named a
# credential it declares `required: true`, and only this one lied — the others
# illustrate with an optional or undeclared key, so completing the pattern
# produces a true sentence about a genuinely unconfigured source.

REQUIRED_CRED = [{"key": "WSTORE_SHOPIFY_ADMIN_TOKEN", "required": True}]


def write_agent_with_body(tmp_path, body: str, **overrides):
    fm = {**AGENT_BASE, **overrides}
    path = tmp_path / f"{fm['name']}.md"
    path.write_text(f"---\n{yaml.safe_dump(fm)}---\n\n{body}\n", encoding="utf-8")
    return path


def test_ungated_credential_failure_example_is_rejected(tmp_path) -> None:
    kit_checks.check_agent(
        write_agent_with_body(
            tmp_path,
            "6. Name each source: `shopify_orders: WSTORE_SHOPIFY_ADMIN_TOKEN not vaulted`.",
            credentials=REQUIRED_CRED,
        )
    )
    assert "without conditioning it on an observed response" in findings()


def test_a_failure_gated_on_an_observed_status_is_allowed(tmp_path) -> None:
    """The correct shape, and the first draft of this rule wrongly flagged it.

    `wstore-upsert-product` already said "if the Admin API answers 401/403,
    report ... not accessible". That is a gene reporting something it saw, which
    is exactly what the rule wants — the hazard is the claim it cannot check.
    """
    kit_checks.check_agent(
        write_agent_with_body(
            tmp_path,
            "2. **Credential unavailable.** If the Admin API answers 401/403, report\n"
            "   `shopify_admin: WSTORE_SHOPIFY_ADMIN_TOKEN not accessible` and write nothing.",
            credentials=REQUIRED_CRED,
        )
    )
    assert not kit_checks.ERRORS


def test_naming_a_required_credential_without_a_failure_claim_is_fine(tmp_path) -> None:
    """Documenting the operator dependency is not the defect."""
    kit_checks.check_agent(
        write_agent_with_body(
            tmp_path,
            "**Operator dependency.** Needs `WSTORE_SHOPIFY_ADMIN_TOKEN` in the vault.",
            credentials=REQUIRED_CRED,
        )
    )
    assert not kit_checks.ERRORS


def test_an_optional_credential_may_illustrate_a_failure(tmp_path) -> None:
    """`stripe: WSTORE_STRIPE_READ_KEY not vaulted` is a legitimate example."""
    kit_checks.check_agent(
        write_agent_with_body(
            tmp_path,
            "6. Name each source: `stripe: WSTORE_STRIPE_READ_KEY not vaulted`.",
            credentials=[{"key": "WSTORE_STRIPE_READ_KEY", "required": False}],
        )
    )
    assert not kit_checks.ERRORS


# test_the_orders_gene_can_still_report_a_real_auth_failure: removed
# This test was specific to the web-store species, testing the wstore-pull-orders
# gene's credential handling. Since homeiq uses different genes with different
# credential patterns, this test is removed. The general principle of testing
# credential failures is covered by individual agent golden cases.


# --- a golden case that never runs is not coverage ---
#
# Probed 2026-07-31: AF's runner (backend/services/agent_eval.py) grades all four
# assertion kinds, but it is reachable only from `agent_staging.promote_staged()`
# and the self-improvement loop. A Pattern A consumer publishes with
# `PUT /projects/{slug}/agents/{name}` + activate and touches neither. Of 224 live
# route paths, the nine under /projects/{slug}/agents/... include no eval endpoint,
# and GET /configs/<our-agent>/quality returns 404. Skills do have
# POST /skills/{name}/eval — the precedent the ask cites.
#
# The warning must keep firing while that is true. Silence here would let a green
# `validate.py` read as "the genes were tested", which is the failure this repo
# refuses everywhere else.


def test_unexecuted_golden_cases_are_reported(tmp_path) -> None:
    agent = write_agent(
        tmp_path,
        golden_cases=[
            {"id": "a", "trials": 5, "assertions": [{"kind": "guardrails_clean"}]},
            {"id": "b", "trials": 3, "assertions": [{"kind": "guardrails_clean"}]},
        ],
    )
    kit_checks.report_unexecuted_golden_cases([agent])
    warning = "\n".join(kit_checks.WARNINGS)
    assert "2 golden case(s) / 8 declared trial(s)" in warning
    assert "a green kit is a schema verdict" in warning


def test_it_is_a_warning_not_an_error(tmp_path) -> None:
    """The cases are correct and worth keeping; the claim of coverage is not."""
    agent = write_agent(
        tmp_path,
        golden_cases=[
            {"id": "a", "assertions": [{"kind": "guardrails_clean"}]},
        ],
    )
    kit_checks.report_unexecuted_golden_cases([agent])
    assert kit_checks.WARNINGS and not kit_checks.ERRORS


def test_a_kit_with_no_golden_cases_says_nothing(tmp_path) -> None:
    kit_checks.report_unexecuted_golden_cases([write_agent(tmp_path)])
    assert not kit_checks.WARNINGS


def test_the_live_kit_reports_its_real_unexecuted_count() -> None:
    """Pins the number so it moves when the situation does — in either direction."""
    kit_checks.report_unexecuted_golden_cases(sorted(AGENTS_DIR.glob("*.md")))
    warning = "\n".join(kit_checks.WARNINGS)
    assert "NOT executed by this validator" in warning
    # The warning used to assert the runner was unreachable from a Pattern A
    # publish. That was disproved on 2026-08-06 — the project-scoped eval
    # endpoint exists and judge cases were graded through it — so the claim was
    # removed rather than left to keep parking the suite. What the warning must
    # still say is that a green kit is a schema verdict, never behavioural
    # evidence, which is the part that was always true.
    assert "never evidence the genes behave" in warning
    assert "unreachable" not in warning
    # A case that reaches a live system must state its observed result and
    # forbid the call. If the warning stops saying so, the next unattended run
    # writes real products to the catalog — measured, not hypothetical.
    assert "EVAL FIXTURE" in warning
    assert "http-fetch-is-the-admin-tool" in warning


class TestSpeciesDiscovery:
    """`SPECIES` is read from the repo, not pinned — NFR-7's precondition.

    A stamped instance repo publishes its own slug. While this was the literal
    string "web-store", such a repo pointed AGENTS_DIR at a directory it does
    not contain and failed its own validator with "no agents found" — the one
    thing a self-validating repo must never do.
    """

    @staticmethod
    def _repo(tmp_path: Path, *slugs: str) -> Path:
        for slug in slugs:
            (tmp_path / "agentforge" / "projects" / slug / "agents").mkdir(parents=True)
        return tmp_path

    def test_it_finds_a_slug_that_is_not_web_store(self, tmp_path) -> None:
        """The whole point: an instance repo is named for its own store."""
        assert kit_rules._discover_species(self._repo(tmp_path, "acme-store")) == "acme-store"

    def test_the_live_repo_still_resolves_to_homeiq(self) -> None:
        """Renamed from test_the_live_factory_repo_still_resolves_to_web_store."""
        assert kit_rules.SPECIES == "homeiq"
        assert AGENTS_DIR.is_dir()

    def test_a_directory_without_agents_is_not_a_project(self, tmp_path) -> None:
        """Guards against a stray sibling dir silently winning the election."""
        repo = self._repo(tmp_path, "real-store")
        (repo / "agentforge" / "projects" / "notes").mkdir()
        assert kit_rules._discover_species(repo) == "real-store"

    def test_no_project_is_fatal(self, tmp_path) -> None:
        with pytest.raises(SystemExit, match="expected exactly one"):
            kit_rules._discover_species(tmp_path)

    def test_two_projects_are_fatal_rather_than_guessed(self, tmp_path) -> None:
        with pytest.raises(SystemExit, match="publishes exactly one"):
            kit_rules._discover_species(self._repo(tmp_path, "one-store", "two-store"))


# --- fleet memory wiring (FR-6 / AD-4) ---


class TestShareScopeIsNotAClosedSet:
    """`share_scope` accepts three builtins plus a dynamic `group:<name>`.

    Mirroring only the builtins made this validator stricter than the platform
    and rejected `group:` outright, which is what blocked the fleet wiring.
    """

    @pytest.mark.parametrize("scope", sorted(kit_rules.SHARE_SCOPE_BUILTIN))
    def test_builtin_scopes_pass(self, tmp_path, scope: str) -> None:
        kit_checks.check_agent_closed_sets(
            write_agent(tmp_path, share_scope=scope), {"share_scope": scope}
        )
        assert "share_scope" not in findings()

    def test_well_formed_group_scope_passes(self, tmp_path) -> None:
        fm = {"share_scope": "group:nlt-store-fleet"}
        kit_checks.check_agent_closed_sets(write_agent(tmp_path, **fm), fm)
        assert "share_scope" not in findings()

    @pytest.mark.parametrize(
        "scope",
        [
            "group:",
            "group:-leading-hyphen",
            "group:Has-Caps",
            "group:has_underscore",
            "shared",
            "group",
        ],
    )
    def test_malformed_scope_is_rejected(self, tmp_path, scope: str) -> None:
        fm = {"share_scope": scope}
        kit_checks.check_agent_closed_sets(write_agent(tmp_path, **fm), fm)
        assert "share_scope" in findings(), f"{scope!r} should not have been accepted"

    def test_the_platform_pattern_is_mirrored_exactly(self) -> None:
        """Drift here means the local gate and the publish PUT disagree."""
        assert kit_rules.SHARE_SCOPE_GROUP.pattern == r"^group:[a-z0-9][a-z0-9-]{0,63}$"
        assert {"private", "domain", "hive"} == kit_rules.SHARE_SCOPE_BUILTIN


class TestHiveGroupMembership:
    """A group write only lands if provisioning registered the gene as a member.

    brain keeps a non-member's group write local and merely warns, so both
    failures below are silent at runtime — the gene reports a successful write
    the fleet never receives.
    """

    def _check(self, tmp_path, **fm):
        kit_checks.check_agent_hive_membership(write_agent(tmp_path, **fm), fm)

    def test_the_fleet_group_on_a_writer_passes(self, tmp_path) -> None:
        self._check(
            tmp_path,
            share_scope=f"group:{kit_rules.FLEET_HIVE_GROUP}",
            memory_profile="full",
        )
        assert findings() == ""

    def test_an_unregistered_group_is_rejected(self, tmp_path) -> None:
        self._check(tmp_path, share_scope="group:some-other-pool", memory_profile="full")
        assert "provisioning step 6 declares membership" in findings()

    @pytest.mark.parametrize("profile", ["readonly", "none"])
    def test_a_group_scope_that_no_write_path_carries_is_rejected(
        self, tmp_path, profile: str
    ) -> None:
        """AF forwards share_scope only when memory_profile is 'full'."""
        self._check(
            tmp_path,
            share_scope=f"group:{kit_rules.FLEET_HIVE_GROUP}",
            memory_profile=profile,
        )
        assert "no write path carries it" in findings()

    def test_non_group_scopes_are_none_of_this_rule_s_business(self, tmp_path) -> None:
        self._check(tmp_path, share_scope="domain", memory_profile="readonly")
        assert findings() == ""


class TestFleetGroupSurvivesReslugging:
    """A fleet-wide constant that re-slugs per store isolates every store.

    This is the defect the name `<prefix>-fleet` would have shipped: each
    stamped store joins a group of one, no cross-store row is ever shared, and
    the stamped validator re-slugs its own constant so it agrees with the
    broken genes.
    """

    def test_the_shipped_name_is_immune(self) -> None:
        kit_checks.check_fleet_group_is_reslug_immune()
        assert findings() == ""

    def test_a_prefix_bearing_name_is_caught(self, tmp_path, monkeypatch) -> None:
        """`<prefix>-fleet` — the name AD-4 and FR-6 propose — is the live hazard.

        The prefix is bounded by a plain `\\b`, so it substitutes happily inside
        a compound. The *slug* would have been safe here (its bound refuses to
        rewrite a compound identifier), which is exactly why picking the name by
        eye is not good enough and this check exists.
        """
        core = kit_checks.render_dna_core
        prefix = core.Identity.of(core.load_species(kit_rules.SPECIES)).prefix
        monkeypatch.setattr(kit_checks, "CORE_DIR", tmp_path / "dna-core")
        monkeypatch.setattr(kit_checks, "FLEET_HIVE_GROUP", f"{prefix}-fleet")
        kit_checks.check_fleet_group_is_reslug_immune()
        assert "contains an identity token" in findings()

    def test_a_slug_bearing_name_would_have_passed(self, tmp_path, monkeypatch) -> None:
        """Documents why the check probes rather than pattern-matches by hand."""
        monkeypatch.setattr(kit_checks, "CORE_DIR", tmp_path / "dna-core")
        monkeypatch.setattr(kit_checks, "FLEET_HIVE_GROUP", f"{kit_rules.SPECIES}-fleet")
        kit_checks.check_fleet_group_is_reslug_immune()
        assert findings() == ""

    def test_the_real_genome_declares_only_the_fleet_group(self) -> None:
        """No gene may name a pool provisioning does not create."""
        for path in sorted(AGENTS_DIR.glob("*.md")):
            scope = str((kit_checks.frontmatter(path) or {}).get("share_scope", ""))
            if scope.startswith("group:"):
                assert scope == f"group:{kit_rules.FLEET_HIVE_GROUP}", path.name
