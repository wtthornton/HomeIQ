#!/usr/bin/env python3
"""Standalone kit validator for web-store (no AgentForge checkout needed).

Adapted from the species-one validator (wtthornton/personal-ops
scripts/validate.py) for the scout layout, plus species-three checks:
policy-rule shape, envelope trust-tagging on ingest genes, and pass^k trial
bounds on golden cases.

Catches the publish-breaking defect classes before anything reaches an AF
instance:

  1. hyphen-case frontmatter keys (AF's loader rejects them — must be snake_case)
  2. malformed YAML frontmatter / missing required fields
  3. output_schema values that are not valid JSON
  4. golden-case shape: rubric assertions need a `rubric` criterion; trials 1-20
  5. workflow shape errors (missing nodes/output, output not a node,
     dangling depends_on, goal without verify.kind+expression, loop members
     that are not nodes, agents that are not in the kit)
  6. skill files missing name/description or name != parent dir
  7. policy rules: rule_id + decision present, decisions in the valid set
  8. dna-core drift: shared genes no longer render byte-identical to the kit
  9. skill tiers: an unclassified pack, or one that violates its tier's rules
 10. a node whose agent declares an output_schema but which declares none
     itself — the orchestrator validates only the node's, so the gene's prose
     is stored as success
 11. `$all_outputs` on a node whose agent is not the quarantine judge
 12. a `memory_profile: full` gene whose body never mentions the trust envelope
 13. a node downstream of the quarantine gate that reads the gate's own sources
     directly instead of reading through it
 14. golden-case composition: a gene below passk-eval rule 1 (one shape case,
     two behaviour cases) that is not held at a frozen `RULE1_BASELINE` count,
     and any baselined gene that regresses below its own entry

The platform contract each check enforces lives in `kit_rules.py`; the checks
themselves live in `kit_checks.py`. This module is discovery and reporting.

Run: python3 scripts/validate.py   (exit 0 = kit is publishable)
"""

from __future__ import annotations

import sys

from kit_checks import (
    ERRORS,
    WARNINGS,
    check_agent,
    check_deployment_packs,
    check_dna_core,
    check_fleet_group_is_reslug_immune,
    check_intake_required_slots,
    check_policy,
    check_rule1_composition,
    check_skill,
    check_skill_tiers,
    check_workflow,
    err,
    report_rubricless_golden_cases,
    report_rule1_debt,
    report_unexecuted_golden_cases,
    report_untrapped_golden_cases,
)
from kit_rules import (
    AGENTS_DIR,
    CORE_DIR,
    POLICY_DIR,
    ROOT,
    SKILLS_DIR,
    TARGETED_TOOLS,
    WORKFLOWS_DIR,
)

__all__ = [
    "ERRORS",
    "TARGETED_TOOLS",
    "WARNINGS",
    "check_agent",
    "check_workflow",
    "main",
]


def main() -> int:
    # Scout layout — must match af_publish.py's _discover_scout() exactly.
    agents = sorted(AGENTS_DIR.glob("*.md"))
    workflows = sorted(WORKFLOWS_DIR.glob("*.yaml"))
    skills = sorted(SKILLS_DIR.glob("*/SKILL.md"))
    policies = sorted(POLICY_DIR.glob("*.yaml"))

    if not agents:
        print(f"ERROR: no agents found under {AGENTS_DIR.relative_to(ROOT)}/*.md", file=sys.stderr)
        print("  scout layout expects flat '<name>.md' files, not '<name>/AGENTS.md' dirs", file=sys.stderr)
        return 1

    stray = sorted(AGENTS_DIR.glob("*/AGENTS.md"))
    if stray:
        for p in stray:
            err(p, "nlt-layout file in a scout project — af_publish will not discover it")

    # The workflow checks need each gene's frontmatter, not just its name: a
    # node's required output contract and its right to read `$all_outputs` are
    # both properties of the agent behind it.
    specs = {p.stem: check_agent(p) or {} for p in agents}
    for p in workflows:
        check_workflow(p, specs)
    for p in skills:
        check_skill(p)
    for p in policies:
        check_policy(p)
    check_dna_core()
    check_deployment_packs()
    check_intake_required_slots()
    check_fleet_group_is_reslug_immune()
    check_skill_tiers(skills)
    check_rule1_composition(agents)
    report_unexecuted_golden_cases(agents)
    report_rubricless_golden_cases(agents)
    report_rule1_debt(agents)
    report_untrapped_golden_cases(agents)

    print(
        f"checked {len(agents)} agents, {len(workflows)} workflows, "
        f"{len(skills)} skills, {len(policies)} policy file(s), "
        f"{len(sorted((CORE_DIR / 'genes').glob('*.md.tmpl')))} shared gene template(s)"
    )
    if WARNINGS:
        print(f"\n{len(WARNINGS)} warning(s):")
        for w in WARNINGS:
            print(f"  WARN {w}")
    if ERRORS:
        print(f"\n{len(ERRORS)} error(s):")
        for e in ERRORS:
            print(f"  FAIL {e}")
        return 1
    print("kit is publishable")
    return 0


if __name__ == "__main__":
    sys.exit(main())
