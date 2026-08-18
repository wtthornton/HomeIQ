"""Contract tests for rubric judging (judge_model, cross-family, scope clause),
rubric-less case classification, passk-eval rule 1 golden-case composition, and
policy deny/allow confinement.

Split from tests/test_validate.py (TAP-6023).
"""

from __future__ import annotations

import kit_checks
import kit_rules
import pytest
import yaml
from kit_rules import AGENTS_DIR
from validate_helpers import findings, isolated_findings, write_agent  # noqa: F401

# --- rubric judging: a criterion must name a judge, and not its own family ---
#
# The platform default is not neutral. AgentForge 4.59.1, probed live on
# 2026-08-07: `DEFAULT_JUDGE_MODEL = "sonnet"` with no env override in the
# running container, so an undeclared rubric on a `model: sonnet` gene is graded
# by its own family. On a `haiku` gene the same default happens to be
# cross-family — which is exactly why 48 undeclared rubrics looked fine.


# Every fixture criterion carries the scope clause, because a rubric without one
# is refused before the judge rules are ever reached — see check_rubric_scope.
SCOPED = f"approved is false. {kit_rules.RUBRIC_SCOPE_CLAUSE}"


def rubric_case(trials: int = 1, **assertion):
    return [
        {
            "id": "c",
            "trials": trials,
            "assertions": [{"kind": "rubric", "rubric": SCOPED, "threshold": 0.9, **assertion}],
        }
    ]


def test_rubric_without_a_judge_model_is_rejected(tmp_path) -> None:
    kit_checks.check_agent(write_agent(tmp_path, model="sonnet", golden_cases=rubric_case()))
    assert "needs an explicit judge_model" in findings()


def test_rubric_judged_by_its_own_family_is_rejected(tmp_path) -> None:
    kit_checks.check_agent(
        write_agent(
            tmp_path,
            model="sonnet",
            golden_cases=rubric_case(judge_model="sonnet", require_cross_family=True),
        )
    )
    assert "same family as the gene's model" in findings()


def test_a_full_model_id_collapses_to_its_family() -> None:
    """`claude-sonnet-4-6` is `sonnet` — a rename must not defeat the check.

    Asserted on `model_family` directly rather than through `check_agent`,
    because the short-alias rule now refuses a full id before the family
    comparison is ever reached. The collapse still has to be right: it is what
    AF itself does at publish, and a gene may legitimately declare its own
    `model:` as a full id.
    """
    assert kit_checks.model_family("claude-sonnet-4-6") == kit_checks.model_family("sonnet")
    assert kit_checks.model_family("CLAUDE-OPUS-4-8") == "opus"
    assert kit_checks.model_family("claude-sonnet-4-5") != "sonnet", (
        "an id outside the alias table stays a literal — the trap the short-alias rule closes"
    )


def test_a_judge_model_without_cross_family_is_rejected(tmp_path) -> None:
    """AF only compares families when `require_cross_family` is set (probed: 422)."""
    kit_checks.check_agent(
        write_agent(tmp_path, model="sonnet", golden_cases=rubric_case(judge_model="opus"))
    )
    assert "not require_cross_family: true" in findings()


def test_a_cross_family_rubric_passes(tmp_path) -> None:
    kit_checks.check_agent(
        write_agent(
            tmp_path,
            model="sonnet",
            golden_cases=rubric_case(judge_model="opus", require_cross_family=True, trials=3),
        )
    )
    assert not kit_checks.ERRORS


def test_a_haiku_gene_may_not_lean_on_the_sonnet_default(tmp_path) -> None:
    """The default *is* cross-family here — and still has to be declared.

    An undeclared property is one a platform-default change silently revokes.
    """
    kit_checks.check_agent(write_agent(tmp_path, model="haiku", golden_cases=rubric_case()))
    assert "needs an explicit judge_model" in findings()


def test_the_live_kit_declares_a_judge_on_every_rubric() -> None:
    for path in sorted(AGENTS_DIR.glob("*.md")):
        kit_checks.check_agent(path)
    assert "judge_model" not in findings()


# --- a rubric must close by scoping the judge to the properties it names ---
#
# Measured 2026-08-07 on `grounds-verdict-in-supplied-matrix`: the opus judge
# wrote that the deduction "does not violate the criterion" and deducted anyway,
# on all five trials, landing 0.83-0.89 under a 0.90 bar. An unscoped rubric
# reads to the judge as a general quality bar, and the only other way out of that
# is lowering the threshold — the one remedy TAP-5762 exists to forbid.


def test_a_rubric_without_the_scope_clause_is_rejected(tmp_path) -> None:
    kit_checks.check_agent(
        write_agent(
            tmp_path,
            model="haiku",
            golden_cases=[
                {
                    "id": "c",
                    "trials": 3,
                    "assertions": [
                        {
                            "kind": "rubric",
                            "rubric": "approved is false",
                            "threshold": 0.9,
                            "judge_model": "sonnet",
                            "require_cross_family": True,
                        }
                    ],
                }
            ],
        )
    )
    assert "does not close with the scope clause" in findings()


def test_a_reworded_scope_clause_is_rejected(tmp_path) -> None:
    """Near-misses are refused, or the clause erodes a phrase at a time.

    This is the failure mode `judge_model` already demonstrated: a rule that
    accepts approximations is a rule that stops meaning one thing.
    """
    kit_checks.check_agent(
        write_agent(
            tmp_path,
            model="haiku",
            golden_cases=[
                {
                    "id": "c",
                    "trials": 3,
                    "assertions": [
                        {
                            "kind": "rubric",
                            "threshold": 0.9,
                            "rubric": "approved is false. Only score the properties named here.",
                            "judge_model": "sonnet",
                            "require_cross_family": True,
                        }
                    ],
                }
            ],
        )
    )
    assert "does not close with the scope clause" in findings()


def test_a_re_wrapped_scope_clause_is_accepted(tmp_path) -> None:
    """A folded YAML scalar arrives re-wrapped; the comparison normalises first."""
    kit_checks.check_agent(
        write_agent(
            tmp_path,
            model="haiku",
            golden_cases=[
                {
                    "id": "c",
                    "trials": 3,
                    "assertions": [
                        {
                            "kind": "rubric",
                            "threshold": 0.9,
                            "rubric": f"approved is false.\n{kit_rules.RUBRIC_SCOPE_CLAUSE}".replace(
                                "; ", ";\n"
                            ),
                            "judge_model": "sonnet",
                            "require_cross_family": True,
                        }
                    ],
                }
            ],
        )
    )
    assert not kit_checks.ERRORS


def test_the_live_kit_scopes_every_rubric() -> None:
    for path in sorted(AGENTS_DIR.glob("*.md")):
        kit_checks.check_agent(path)
    assert "scope clause" not in findings()


# --- the rubric-less count is spoken out loud so it cannot silently regrow ---


def test_rubricless_cases_are_counted(tmp_path) -> None:
    agent = write_agent(
        tmp_path,
        model="haiku",
        golden_cases=[
            {
                "id": "shape",
                "assertions": [{"kind": "output_schema_valid"}, {"kind": "guardrails_clean"}],
            },
            {
                "id": "behaviour",
                "assertions": [
                    {
                        "kind": "rubric",
                        "rubric": SCOPED,
                        "threshold": 0.9,
                        "judge_model": "sonnet",
                        "require_cross_family": True,
                    },
                ],
            },
        ],
    )
    kit_checks.report_rubricless_golden_cases([agent])
    assert "1 of 2 golden case(s) carry no rubric assertion" in "\n".join(kit_checks.WARNINGS)


def test_a_kit_with_no_cases_reports_no_count(tmp_path) -> None:
    kit_checks.report_rubricless_golden_cases([write_agent(tmp_path)])
    assert not kit_checks.WARNINGS


def test_the_live_kit_reports_its_real_rubricless_count() -> None:
    """Pins the number so it moves when the situation does — in either direction."""
    kit_checks.report_rubricless_golden_cases(sorted(AGENTS_DIR.glob("*.md")))
    warning = "\n".join(kit_checks.WARNINGS)
    assert "golden case(s) carry no rubric assertion" in warning
    assert "never that the gene reached the right answer" in warning


# --- a rubric-less case must say, in its own body, that shape is the point ---


def test_a_case_with_no_rubric_and_no_classification_is_rejected(tmp_path) -> None:
    kit_checks.check_agent(
        write_agent(
            tmp_path,
            model="haiku",
            golden_cases=[
                {
                    "id": "c",
                    "assertions": [{"kind": "output_schema_valid"}, {"kind": "guardrails_clean"}],
                },
            ],
        )
    )
    assert "no shape_only_because" in findings()


def test_a_declared_shape_case_passes(tmp_path) -> None:
    kit_checks.check_agent(
        write_agent(
            tmp_path,
            model="haiku",
            golden_cases=[
                {
                    "id": "c",
                    "shape_only_because": "conformance only; the behaviour is asserted next door",
                    "assertions": [{"kind": "output_schema_valid"}],
                },
            ],
        )
    )
    assert not kit_checks.ERRORS


def test_a_stale_marker_left_beside_a_rubric_is_rejected(tmp_path) -> None:
    """The same lie in the other direction: a marker that outlived its case."""
    cases = rubric_case(judge_model="opus", require_cross_family=True)
    cases[0]["shape_only_because"] = "no longer true"
    kit_checks.check_agent(write_agent(tmp_path, model="sonnet", golden_cases=cases))
    assert "shape_only_because is stale" in findings()


def test_every_live_case_is_classified_one_way_or_the_other() -> None:
    for path in sorted(AGENTS_DIR.glob("*.md")):
        kit_checks.check_agent(path)
    assert "shape_only_because" not in findings()


# --- a judge is declared by short alias, never by a full model id ---
#
# AF's MODEL_ALIASES is a fixed seven-entry table, not a general collapse of
# Anthropic ids. Probed 2026-08-07 against 4.59.1 with an agent on `model:
# sonnet`: `claude-sonnet-4-6` is refused 422 as same-family, but
# `claude-sonnet-4-5` and `claude-3-7-sonnet-latest` PASS require_cross_family
# while self-family grading. Compliance-shaped, and wrong.


@pytest.mark.parametrize(
    "judge", ["claude-sonnet-4-5", "claude-3-7-sonnet-latest", "sonnet-4-6", "gpt-5"]
)
def test_a_judge_model_outside_the_short_aliases_is_rejected(tmp_path, judge: str) -> None:
    kit_checks.check_agent(
        write_agent(
            tmp_path,
            model="sonnet",
            golden_cases=rubric_case(judge_model=judge, require_cross_family=True, trials=3),
        )
    )
    assert "declare a judge by short alias" in findings()


@pytest.mark.parametrize("judge", ["opus", "sonnet", "haiku", "OPUS"])
def test_the_short_aliases_are_accepted(tmp_path, judge: str) -> None:
    model = "haiku" if judge.lower() != "haiku" else "sonnet"
    kit_checks.check_agent(
        write_agent(
            tmp_path,
            model=model,
            golden_cases=rubric_case(judge_model=judge, require_cross_family=True, trials=3),
        )
    )
    assert not kit_checks.ERRORS


def test_the_alias_rule_fires_before_the_family_rule(tmp_path) -> None:
    """`claude-sonnet-4-5` on a sonnet gene is BOTH wrong — report the actionable one.

    The family check would pass it (the literal is not in the alias table), so
    only the alias rule catches it. Reporting a same-family error here would be
    a lie about why it was refused.
    """
    kit_checks.check_agent(
        write_agent(
            tmp_path,
            model="sonnet",
            golden_cases=rubric_case(
                judge_model="claude-sonnet-4-5", require_cross_family=True, trials=3
            ),
        )
    )
    assert "declare a judge by short alias" in findings()
    assert "same family" not in findings()


# --- a behaviour case is worth three trials or it is worth very little ---


def test_a_rubric_case_at_one_trial_is_rejected(tmp_path) -> None:
    kit_checks.check_agent(
        write_agent(
            tmp_path,
            model="haiku",
            golden_cases=rubric_case(judge_model="sonnet", require_cross_family=True),
        )
    )
    assert "needs trials: 3 or more" in findings()


def test_a_rubric_case_at_three_trials_passes(tmp_path) -> None:
    kit_checks.check_agent(
        write_agent(
            tmp_path,
            model="haiku",
            golden_cases=rubric_case(judge_model="sonnet", require_cross_family=True, trials=3),
        )
    )
    assert not kit_checks.ERRORS


def test_a_shape_case_may_still_run_once(tmp_path) -> None:
    """The rule is about behaviour, not about every case. Schema conformance is
    near-deterministic and one trial is the documented choice for it."""
    kit_checks.check_agent(
        write_agent(
            tmp_path,
            model="haiku",
            golden_cases=[
                {
                    "id": "c",
                    "trials": 1,
                    "shape_only_because": "conformance only",
                    "assertions": [{"kind": "output_schema_valid"}],
                },
            ],
        )
    )
    assert not kit_checks.ERRORS


def test_the_live_kit_runs_every_behaviour_case_at_least_three_times() -> None:
    for path in sorted(AGENTS_DIR.glob("*.md")):
        kit_checks.check_agent(path)
    assert "trials: 3 or more" not in findings()


# --- passk-eval rule 1: golden-case composition, ratcheted (TODO 5) ---
#
# Rule 1 wants three cases per gene — one shape, two behaviour. 23 of 30 genes
# were below it on 2026-08-07, so `RULE1_BASELINE` freezes their counts and the
# check refuses only movement in the wrong direction. These tests exercise each
# direction: a check that never fires would be indistinguishable from no check.


def _behaviour_case(cid: str = "b"):
    return {
        "id": cid,
        "prompt": "p",
        "trials": 3,
        "pass_threshold": 1.0,
        "assertions": [{"kind": "rubric", "criterion": "names an observable property"}],
    }


def _shape_case(cid: str = "s"):
    return {
        "id": cid,
        "prompt": "p",
        "trials": 1,
        "pass_threshold": 1.0,
        "shape_only_because": "conformance is the whole assertion",
        "assertions": [{"kind": "output_schema_valid"}],
    }


def test_a_new_gene_below_rule_one_is_refused(tmp_path) -> None:
    """No baseline entry means the full rule applies — that is the point of the ratchet."""
    path = write_agent(tmp_path, name="wstore-brandnew", golden_cases=[_shape_case()])
    kit_checks.check_rule1_composition([path])
    assert "violate passk-eval rule 1" in findings()


def test_a_new_gene_meeting_rule_one_passes(tmp_path) -> None:
    path = write_agent(
        tmp_path,
        name="wstore-brandnew",
        golden_cases=[_shape_case(), _behaviour_case("b1"), _behaviour_case("b2")],
    )
    kit_checks.check_rule1_composition([path])
    assert not kit_checks.ERRORS


def test_a_new_gene_with_no_shape_case_is_refused(tmp_path) -> None:
    """Three behaviour cases is still not rule 1 — the shape case is its own clause."""
    path = write_agent(
        tmp_path, name="wstore-brandnew", golden_cases=[_behaviour_case(f"b{i}") for i in range(3)]
    )
    kit_checks.check_rule1_composition([path])
    assert "violate passk-eval rule 1" in findings()


def test_a_baselined_gene_held_at_its_entry_passes(tmp_path) -> None:
    """`hiq-correlate` is frozen at (1 total, 0 shape, 1 behaviour) and may sit there."""
    path = write_agent(tmp_path, name="hiq-correlate", golden_cases=[_behaviour_case("b1")])
    kit_checks.check_rule1_composition([path])
    assert not kit_checks.ERRORS


def test_a_baselined_gene_that_loses_a_case_is_refused(tmp_path) -> None:
    """`hiq-memory-curator` is frozen at 3 cases; shipping 2 is a regression."""
    path = write_agent(
        tmp_path,
        name="hiq-memory-curator",
        golden_cases=[_behaviour_case(f"b{i}") for i in range(2)],
    )
    kit_checks.check_rule1_composition([path])
    assert "regressed below the RULE1_BASELINE entry" in findings()


def test_a_baselined_gene_that_becomes_compliant_must_lose_its_entry(tmp_path) -> None:
    """The exemption must not outlive the debt, or the table never shrinks.

    `hiq-correlate` is held at (1, 0, 1) by the baseline. If it ships with
    (3, 1, 2), it becomes compliant and the entry should be deleted.
    """
    path = write_agent(
        tmp_path,
        name="hiq-correlate",
        golden_cases=[_shape_case(), _behaviour_case("b1"), _behaviour_case("b2")],
    )
    kit_checks.check_rule1_composition([path])
    assert "delete 'correlate' from RULE1_BASELINE" in findings()


def test_trap_for_outside_the_seeded_six_is_refused(tmp_path) -> None:
    case = {**_behaviour_case(), "trap_for": "covers the bad input"}
    kit_checks.check_golden_cases(write_agent(tmp_path, model="haiku"), {"golden_cases": [case]})
    assert "trap_for must name one of the six seeded traps" in findings()


def test_a_seeded_trap_id_is_accepted(tmp_path) -> None:
    case = {**_behaviour_case(), "trap_for": "injection-payload"}
    kit_checks.check_golden_cases(write_agent(tmp_path, model="haiku"), {"golden_cases": [case]})
    assert "trap_for" not in findings()


def test_the_live_kit_satisfies_the_rule_one_ratchet() -> None:
    """Every real gene is either compliant or held at its own frozen entry."""
    kit_checks.check_rule1_composition(sorted(AGENTS_DIR.glob("*.md")))
    assert not kit_checks.ERRORS


def test_the_rule_one_baseline_has_no_stale_entries() -> None:
    """A gene listed in the baseline that no longer exists is a dead exemption."""
    prefix = kit_checks.species_prefix()
    live = {kit_checks.baseline_key(p.stem, prefix) for p in AGENTS_DIR.glob("*.md")}
    assert not set(kit_rules.RULE1_BASELINE) - live


def test_the_rule_one_baseline_keys_survive_a_reslug() -> None:
    """A key carrying this store's prefix would miss on every renamed gene, so a
    fresh stamp would fail its own publish gate on debt it inherited unchanged."""
    assert not [
        k for k in kit_rules.RULE1_BASELINE if k.startswith(f"{kit_checks.species_prefix()}-")
    ]


# --- deny/allow pairs must confine, not shadow (TAP-5953) --------------------
#
# These assert the rule FIRES. `check_policy_deny_covers_every_workflow` exists
# because the money and broadcast denies shipped with no `workflow_context`, an
# empty condition matches every workflow, and deny wins over priority — so the
# paired allow was unreachable and strict enforcement blocked the chromosome's
# own flow. A check nobody has watched fail is indistinguishable from one that
# cannot.

MONEY_CAPS = ["wstore.act.money", "wstore.act.capture", "wstore.act.refund", "wstore.act.payout"]


@pytest.fixture
def policy_rules(tmp_path, monkeypatch):
    """Point the check at a scratch workflow dir and a clean findings list."""
    workflows = tmp_path / "workflows"
    workflows.mkdir()
    for name in ("store-health", "cx-inbox", "money-movement"):
        (workflows / f"{name}.yaml").write_text("name: x\n", encoding="utf-8")
    monkeypatch.setattr(kit_checks, "WORKFLOWS_DIR", workflows)
    monkeypatch.setattr(kit_checks, "ERRORS", [])
    monkeypatch.setattr(kit_checks, "WARNINGS", [])

    def run(deny_context, allow_context=("money-movement",)):
        rules = [
            {
                "rule_id": "deny-money",
                "capabilities": MONEY_CAPS,
                "decision": "deny",
                **({"workflow_context": list(deny_context)} if deny_context is not None else {}),
            },
            {
                "rule_id": "allow-money",
                "capabilities": MONEY_CAPS,
                "decision": "allow",
                "workflow_context": list(allow_context),
            },
        ]
        kit_checks.check_policy_deny_covers_every_workflow(tmp_path / "rules.yaml", rules)
        return "\n".join(kit_checks.ERRORS)

    return run


def test_a_deny_with_no_workflow_context_is_refused(policy_rules) -> None:
    """The exact TAP-5953 defect: the allow can never fire."""
    findings = policy_rules(None)
    assert "deny-money" in findings
    assert "names no workflow_context" in findings
    assert "paired allow can never fire" in findings


def test_a_deny_that_omits_the_empty_context_is_refused(policy_rules) -> None:
    """`""` is the ad-hoc invoke — the caller confinement most wants to stop, and
    the one an enumeration of workflow FILES would never produce.
    """
    findings = policy_rules(["store-health", "cx-inbox"])
    assert 'must include ""' in findings


def test_a_workflow_named_by_neither_rule_is_refused(policy_rules) -> None:
    """The fail-open an enumeration invites: nothing matching is an ALLOW, so an
    unlisted chromosome silently gains the confined capabilities.
    """
    findings = policy_rules(["", "store-health"])
    assert "cx-inbox" in findings
    assert "silently gain these capabilities" in findings


def test_a_fully_enumerated_pair_is_accepted(policy_rules) -> None:
    """The other direction — a rule that stops firing on good input is a false green."""
    assert policy_rules(["", "store-health", "cx-inbox"]) == ""


def test_the_real_policy_file_is_valid() -> None:
    """The shipped rules file must be valid YAML and pass kit checks.

    This test verifies the policy file for the species is correctly formatted
    and understood by the validation system. homeiq's policy is a placeholder;
    species-specific confinement rules will be added as needed.
    """
    kit_checks.ERRORS.clear()
    policy_path = kit_rules.ROOT / "policy" / f"{kit_rules.SPECIES}.rules.yaml"
    kit_checks.check_policy(policy_path)
    assert not kit_checks.ERRORS, kit_checks.ERRORS

    # Policy must be valid YAML
    doc = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    assert isinstance(doc, dict), "policy must be a YAML object"
    assert "rules" in doc, "policy must have a 'rules' key"
    assert isinstance(doc["rules"], list), "rules must be a list"

    # Each rule must have required fields
    for rule in doc["rules"]:
        assert "rule_id" in rule, f"rule missing rule_id: {rule}"
        assert "decision" in rule, f"rule {rule['rule_id']} missing decision"
        assert rule["decision"] in ("allow", "deny"), (
            f"rule {rule['rule_id']} invalid decision: {rule['decision']}"
        )
