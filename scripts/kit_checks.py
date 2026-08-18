"""The kit checks themselves — one function per publish-breaking defect class.

Every check reports through `err`/`warn` rather than raising, so a single run
surfaces the whole error set instead of stopping at the first bad file.
`ERRORS` and `WARNINGS` are module-level and shared by import: `validate.py`
binds the same list objects and reads them after the checks run.

Split out of `validate.py` so the orchestration (discovery, reporting, exit
code) stays readable next to the checking logic it drives.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import input_source
import render_dna_core
import yaml
from kit_rules import (
    AF_VERSION,
    AGENT_REQUIRED,
    BEHAVIOUR_TRIALS,
    CORE_DIR,
    CREDENTIAL_AUTH_HEADERS,
    CREDENTIAL_FAILURE_TERMS,
    FLEET_HIVE_GROUP,
    GATE_TRANSPARENT_FIELDS,
    HTTP_ALLOWLIST_FORBIDDEN_CHARS,
    HTTP_FETCH_GRANT,
    HYPHEN_KEYS,
    INJECT_HEADER,
    JUDGE_MODEL_ALIASES,
    JUDGE_PASS_THRESHOLD,
    JUDGE_TRIALS,
    MODEL_ALIASES,
    OBSERVED_FAILURE_MARKERS,
    PATTERN_A_UNAVAILABLE_KINDS,
    QUARANTINE_CAPABILITY,
    RESERVED_INPUT_REFS,
    ROOT,
    RUBRIC_SCOPE_CLAUSE,
    RULE1_BASELINE,
    RULE1_MIN_BEHAVIOUR,
    RULE1_MIN_SHAPE,
    RULE1_MIN_TOTAL,
    SCRIPT_ID_FIELD,
    SCRIPT_KIND,
    SHARE_SCOPE_BUILTIN,
    SHARE_SCOPE_GROUP,
    SHOPIFY_ADMIN_CREDENTIAL,
    SKILLS_DIR,
    SPECIES,
    STORE_INPUT,
    STOREFRONT_INGEST_CAPABILITY,
    TARGETED_TOOLS,
    TRAP_IDS,
    TRUST_ENVELOPE_TERMS,
    VALID_ASSERTION_KINDS,
    VALID_DECISIONS,
    VALID_ENUMS,
    VALID_GUARDRAILS,
    VALID_NODE_KINDS,
    VALID_SCRIPT_IDS,
    VALID_TIERS,
    WILDCARD_INPUT,
    WORKFLOW_INPUT_SOURCES,
    WORKFLOWS_DIR,
)
from skill_pack import SkillPackError

ERRORS: list[str] = []
WARNINGS: list[str] = []


def err(path: Path, msg: str) -> None:
    ERRORS.append(f"{path.relative_to(ROOT)}: {msg}")


def warn(path: Path, msg: str) -> None:
    WARNINGS.append(f"{path.relative_to(ROOT)}: {msg}")


def frontmatter(path: Path) -> dict | None:
    parts = path.read_text(encoding="utf-8").split("---\n")
    if len(parts) < 3:
        err(path, "no frontmatter block")
        return None
    try:
        fm = yaml.safe_load(parts[1])
    except yaml.YAMLError as exc:
        err(path, f"frontmatter YAML error: {exc}")
        return None
    if not isinstance(fm, dict):
        err(path, "frontmatter is not a mapping")
        return None
    return fm


def body(path: Path) -> str:
    """The prose below the frontmatter block — the gene's actual instructions."""
    parts = path.read_text(encoding="utf-8").split("---\n", 2)
    return parts[2] if len(parts) > 2 else ""


def model_family(model: str) -> str:
    """Reduce a model id or alias to the family key AF compares on."""
    m = (model or "").strip().lower()
    return MODEL_ALIASES.get(m, m)


def check_assertion(path: Path, cid: str, assertion: object, agent_model: str = "") -> None:
    if not isinstance(assertion, dict):
        err(path, f"golden case '{cid}': assertions must be mappings")
        return
    kind = assertion.get("kind")
    if kind not in VALID_ASSERTION_KINDS:
        err(path, f"golden case '{cid}': unknown assertion kind {kind!r}")
    if kind == "rubric":
        if not str(assertion.get("rubric", "")).strip():
            err(path, f"golden case '{cid}': kind='rubric' needs a non-empty 'rubric' criterion")
        check_rubric_judge(path, cid, assertion, agent_model)
        check_rubric_scope(path, cid, assertion)


def check_rubric_judge(path: Path, cid: str, assertion: dict, agent_model: str) -> None:
    """A rubric must name its judge, and that judge must not be the gene's own family.

    The platform default is not neutral. Probed against AgentForge 4.59.1 on
    2026-08-07: `DEFAULT_JUDGE_MODEL = "sonnet"` (`backend/eval/contract.py:26`)
    with no env override in the running container, so an undeclared rubric on a
    `model: sonnet` gene is **graded by its own family** — the self-preference
    exposure `skills/passk-eval/SKILL.md` rule 4 exists to close. On a `haiku`
    gene the same default happens to be cross-family, which is why the gap was
    invisible: two thirds of the fleet's rubrics looked fine by accident.

    AF enforces the family rule itself, but only when `require_cross_family` is
    declared — an omitted `judge_model` is silently accepted and silently
    defaulted. That is the hole this check closes, and it closes it here rather
    than at publish so the answer arrives before the round trip.
    """
    judge = str(assertion.get("judge_model", "")).strip()
    if not judge:
        err(
            path,
            f"golden case '{cid}': kind='rubric' needs an explicit judge_model — an "
            f"omitted one defaults to sonnet, which self-grades every model: sonnet "
            f"gene (skills/passk-eval/SKILL.md § Who grades a rubric)",
        )
        return
    if judge.lower() not in JUDGE_MODEL_ALIASES:
        err(
            path,
            f"golden case '{cid}': judge_model: {judge} — declare a judge by short alias "
            f"({'/'.join(sorted(JUDGE_MODEL_ALIASES))}). AF's alias table is seven fixed "
            f"entries; a full id outside it is compared as a literal, so "
            f"judge_model: claude-sonnet-4-5 passes require_cross_family against a "
            f"model: sonnet gene while self-family grading it (probed 2026-08-07)",
        )
        return
    if not assertion.get("require_cross_family"):
        err(
            path,
            f"golden case '{cid}': kind='rubric' declares judge_model: {judge} but not "
            f"require_cross_family: true — without it AF never checks the families",
        )
    if agent_model and model_family(judge) == model_family(agent_model):
        err(
            path,
            f"golden case '{cid}': judge_model: {judge} is the same family as the gene's "
            f"model: {agent_model} — a rubric may not be graded by its own family",
        )


def check_rubric_scope(path: Path, cid: str, assertion: dict) -> None:
    """A rubric must close by telling the judge to score only what it names.

    Without it the judge grades the output rather than the criterion. Measured
    2026-08-07 on `grounds-verdict-in-supplied-matrix`: the opus judge stated the
    deduction did not violate the criterion and deducted anyway, across all five
    trials, landing 0.83-0.89 under a 0.90 bar. That is a fail that says nothing
    about the property the case is named for.

    The clause is compared exactly, on whitespace-normalised text, so that a
    folded YAML scalar re-wrapped at a different width still matches while a
    reworded one does not. Approximate matching would let the clause erode a
    phrase at a time, which is how the `judge_model` gap opened in the first
    place.
    """
    body = " ".join(str(assertion.get("rubric", "")).split())
    if not body:
        return
    if " ".join(RUBRIC_SCOPE_CLAUSE.split()) in body:
        return
    err(
        path,
        f"golden case '{cid}': kind='rubric' criterion does not close with the scope "
        f"clause — append it verbatim: {RUBRIC_SCOPE_CLAUSE!r}. An unscoped judge "
        f"deducts for properties it agrees the criterion does not require "
        f"(measured 2026-08-07, reports/suite-quality-2026-08-07.md)",
    )


def check_golden_cases(path: Path, fm: dict) -> None:
    # `skills/passk-eval/SKILL.md:25` — every golden case on a judgment gene runs
    # 5 trials at threshold 1.0, "no exceptions", because a judge that fails one
    # time in five is not a gate.
    #
    # This rule exists because the invariant regressed once and nothing caught it:
    # two cases were added to `wstore-judge-disclosure` at `trials: 3` (copied from
    # a `role: gateway` gene, where 3 is correct) and validate.py stayed green.
    # `.ralph/fix_plan.md` had recorded the audit as complete, so the only record
    # of the rule was prose in a skill no gene can read. Enforce it here instead.
    is_judge = fm.get("role") == "judge"

    for case in fm.get("golden_cases") or []:
        if not isinstance(case, dict):
            err(path, "golden_cases entries must be mappings")
            continue
        cid = case.get("id", "<no id>")
        trials = case.get("trials", 1)
        if not isinstance(trials, int) or not (1 <= trials <= 20):
            err(path, f"golden case '{cid}': trials must be an int in 1..20, got {trials!r}")
        elif is_judge and trials != JUDGE_TRIALS:
            err(
                path,
                f"golden case '{cid}': role: judge requires trials: {JUDGE_TRIALS}, "
                f"got {trials} (skills/passk-eval/SKILL.md:25)",
            )
        threshold = case.get("pass_threshold", 1.0)
        if not isinstance(threshold, (int, float)) or not (0.0 <= threshold <= 1.0):
            err(path, f"golden case '{cid}': pass_threshold must be in 0.0..1.0, got {threshold!r}")
        elif is_judge and threshold != JUDGE_PASS_THRESHOLD:
            err(
                path,
                f"golden case '{cid}': role: judge requires pass_threshold: "
                f"{JUDGE_PASS_THRESHOLD}, got {threshold} (skills/passk-eval/SKILL.md:25)",
            )
        assertions = case.get("assertions") or []
        if not assertions:
            err(path, f"golden case '{cid}': needs at least one assertion")
        for assertion in assertions:
            check_assertion(path, cid, assertion, fm.get("model", ""))
        check_case_is_classified(path, cid, case, assertions)
        # A trap is only checkable if it says which trap it is. Free text would let
        # `trap_for: covers the bad input` count as coverage of a specific seeded
        # trap it never exercises, so the value is drawn from the fixed six.
        if "trap_for" in case:
            trap = str(case.get("trap_for", "")).strip()
            if trap not in TRAP_IDS:
                err(
                    path,
                    f"golden case '{cid}': trap_for must name one of the six seeded traps "
                    f"({', '.join(sorted(TRAP_IDS))}), got {trap!r} "
                    f"(skills/passk-eval/SKILL.md 'Seeded traps')",
                )


def check_case_is_classified(path: Path, cid: str, case: dict, assertions: list) -> None:
    """A case with no rubric must say, in its own body, that shape is the point.

    `output_schema_valid` + `guardrails_clean` assert that the gene emitted
    conforming JSON and tripped no blocklist. Both are real — and both pass for a
    gene that put the wrong values in the right keys. So a rubric-less case is
    honest as a *shape* case and dishonest as anything else, and the only way to
    tell them apart from the outside is for the author to say which it is.

    `shape_only_because` is repo-local: AgentForge's `GoldenCase` ignores unknown
    keys (probed 2026-08-07 — `PUT` returned 201 with the key present), so this
    costs nothing on the wire and everything to the next reader. Declaring it on a
    case that *does* carry a rubric is rejected too, because a stale marker left
    behind after a rubric is added is the same lie in the other direction.
    """
    has_rubric = any(a.get("kind") == "rubric" for a in assertions if isinstance(a, dict))
    reason = str(case.get("shape_only_because", "")).strip()
    trials = case.get("trials", 1)
    if has_rubric and isinstance(trials, int) and trials < BEHAVIOUR_TRIALS:
        err(
            path,
            f"golden case '{cid}': carries a rubric, so it is a behaviour case and needs "
            f"trials: {BEHAVIOUR_TRIALS} or more, got {trials} — a behaviour rubric measured "
            f"once measures very little (skills/passk-eval/SKILL.md:25)",
        )
    if has_rubric and reason:
        err(path, f"golden case '{cid}': carries a rubric, so shape_only_because is stale — drop it")
    elif not has_rubric and not reason:
        err(
            path,
            f"golden case '{cid}': has no rubric assertion and no shape_only_because — say why "
            f"schema conformance is the whole assertion here, or assert the behaviour "
            f"(skills/passk-eval/SKILL.md rule 1)",
        )


def case_composition(fm: dict) -> tuple[int, int, int]:
    """Count a gene's cases as `(total, shape, behaviour)`.

    A behaviour case is one carrying a rubric — the only assertion kind that says
    the gene reached the right answer. Everything else is a shape case, and
    `check_case_is_classified` already refuses a rubric-less case that does not
    declare `shape_only_because`, so the two classes partition cleanly here.
    """
    cases = [c for c in fm.get("golden_cases") or [] if isinstance(c, dict)]
    behaviour = sum(
        1
        for c in cases
        if any(a.get("kind") == "rubric" for a in c.get("assertions") or [] if isinstance(a, dict))
    )
    return len(cases), len(cases) - behaviour, behaviour


def check_rule1_composition(agents: list[Path]) -> None:
    """Ratchet `skills/passk-eval/SKILL.md` rule 1 onto a fleet that predates it.

    Rule 1 wants three cases per gene: one shape, two behaviour, one of those a
    trap. 23 of 30 genes were below that on 2026-08-07 because nothing counted.
    Erroring on all of them would have made the kit unpublishable and blocked the
    gene fixes queued behind it, so `RULE1_BASELINE` freezes what each one had and
    this check only refuses movement in the wrong direction:

      * a gene with no baseline entry must satisfy rule 1 outright — that covers
        every new gene and the seven already compliant;
      * a listed gene may not drop below its own frozen counts;
      * a listed gene that reaches full compliance must lose its entry, so the
        table shrinks to nothing instead of outliving the debt it records.

    The trap clause is deliberately not ratcheted: no case declares `trap_for`
    yet, so there is no count to protect. `report_untrapped_golden_cases` states
    that gap rather than letting a baseline of zeroes imply it is handled.

    Composition is a property of the kit's real gene set, not of a single file, so
    this runs over `agents` from `validate.py` like the other kit-level reports —
    not from `check_agent`, whose job is the shape of one file.
    """
    prefix = species_prefix()
    for path in agents:
        fm = frontmatter(path)
        if fm is not None:
            check_gene_composition(path, fm, prefix)


def species_prefix() -> str:
    """This store's gene-name prefix (`wstore`), or "" if the species cannot be read.

    An unreadable species is already reported by `check_fleet_group_is_reslug_immune`;
    falling back to "" here leaves gene names unstripped rather than adding a second
    copy of the same error.
    """
    try:
        return render_dna_core.Identity.of(render_dna_core.load_species(SPECIES)).prefix
    except (SystemExit, KeyError, OSError):
        return ""


def baseline_key(stem: str, prefix: str) -> str:
    """`wstore-rank` -> `rank`, so the entry survives a re-slug into another store."""
    token = f"{prefix}-"
    return stem[len(token):] if prefix and stem.startswith(token) else stem


def check_gene_composition(path: Path, fm: dict, prefix: str) -> None:
    """Hold one gene to rule 1, or to its frozen `RULE1_BASELINE` entry."""
    name = baseline_key(path.stem, prefix)
    total, shape, behaviour = case_composition(fm)
    complies = total >= RULE1_MIN_TOTAL and shape >= RULE1_MIN_SHAPE and behaviour >= RULE1_MIN_BEHAVIOUR
    baseline = RULE1_BASELINE.get(name)

    if baseline is None:
        if not complies:
            err(
                path,
                f"golden cases violate passk-eval rule 1: {total} case(s) "
                f"({shape} shape, {behaviour} behaviour), needs at least "
                f"{RULE1_MIN_TOTAL} ({RULE1_MIN_SHAPE} shape, {RULE1_MIN_BEHAVIOUR} behaviour) "
                f"— a gene ships one shape case and two behaviour cases "
                f"(skills/passk-eval/SKILL.md rule 1)",
            )
        return

    if complies:
        err(
            path,
            f"golden cases now satisfy passk-eval rule 1 ({total} case(s): {shape} shape, "
            f"{behaviour} behaviour) — delete '{name}' from RULE1_BASELINE in "
            f"scripts/kit_rules.py so the exemption does not outlive the debt",
        )
        return

    want_total, want_shape, want_behaviour = baseline
    if total < want_total or shape < want_shape or behaviour < want_behaviour:
        err(
            path,
            f"golden cases regressed below the RULE1_BASELINE entry: had "
            f"({want_total} total, {want_shape} shape, {want_behaviour} behaviour), "
            f"now ({total}, {shape}, {behaviour}) — a baselined gene may only improve "
            f"(skills/passk-eval/SKILL.md rule 1)",
        )


def report_rule1_debt(agents: list[Path]) -> None:
    """Print what rule 1 is still owed, so the ratchet visibly burns down."""
    prefix = species_prefix()
    outstanding = sum(1 for p in agents if baseline_key(p.stem, prefix) in RULE1_BASELINE)
    if not outstanding:
        return
    WARNINGS.append(
        f"{outstanding} gene(s) ship fewer golden cases than passk-eval rule 1 requires "
        f"(at least {RULE1_MIN_TOTAL}: {RULE1_MIN_SHAPE} shape, {RULE1_MIN_BEHAVIOUR} behaviour) "
        "and are held at their 2026-08-07 counts by RULE1_BASELINE. They may only improve — "
        "a new or edited gene is held to the full rule. Watch this number: it only ever goes down"
    )


def report_untrapped_golden_cases(agents: list[Path]) -> None:
    """Name the trap clause as unmet rather than letting silence imply coverage.

    Rule 1 asks that one behaviour case per gene be a trap where that gene's
    failure mode lives, and `skills/passk-eval/SKILL.md` seeds six specific ones.
    `trap_for` makes that declarable and `check_golden_cases` validates it, but no
    case declares one yet — so every gene's trap count is zero and the clause is
    unenforced. Saying so is the difference between a known gap and a silent one.
    """
    total = trapped = 0
    for path in agents:
        for case in (frontmatter(path) or {}).get("golden_cases") or []:
            if not isinstance(case, dict):
                continue
            total += 1
            if str(case.get("trap_for", "")).strip() in TRAP_IDS:
                trapped += 1
    if not total:
        return
    WARNINGS.append(
        f"{trapped} of {total} golden case(s) declare trap_for — passk-eval rule 1 wants one "
        "trap case per gene drawn from the six seeded traps, and a case that does not name its "
        "trap cannot be counted as one. Until this number rises the trap clause is declared and "
        "validated but not enforced; the case count above is the part being ratcheted"
    )


def report_unexecuted_golden_cases(agents: list[Path]) -> None:
    """Say out loud that the declared cases have never run. Probed 2026-07-31.

    AF has a complete golden-case runner — `backend/services/agent_eval.py`
    grades all four assertion kinds and ships an LLM judge — but it is reachable
    only from `agent_staging.promote_staged()` (AF-native agents) and the
    self-improvement loop. A Pattern A consumer publishes with
    `PUT /projects/{slug}/agents/{name}` + activate, which touches neither.

    Confirmed against the live route table: of 224 paths, the nine under
    `/projects/{slug}/agents/...` include no eval endpoint, and
    `GET /configs/<our-agent>/quality` returns 404 because project-scoped agents
    are not in the global namespace. Skills, by contrast, do have
    `POST /skills/{name}/eval`. Asked for in
    `docs/agentforge-ask-golden-case-execution.md`.

    This is a WARNING, not an error, and deliberately so: the cases are correct
    and worth keeping, and `check_golden_cases` should go on enforcing
    `trials: 5` on judges for the day they run. What must not happen is the kit
    reporting "publishable" in a way that reads as "the contracts were checked".
    A case that never executes is worse than no case, because it looks like
    coverage — which is the same failure this repo already refuses to tolerate
    in a gate that always blocks.
    """
    declared = trials = 0
    for path in agents:
        fm = frontmatter(path)
        for case in (fm or {}).get("golden_cases") or []:
            if isinstance(case, dict):
                declared += 1
                trials += case.get("trials", 1)
    if not declared:
        return
    WARNINGS.append(
        f"{declared} golden case(s) / {trials} declared trial(s) are declared here but "
        "NOT executed by this validator — a green kit is a schema verdict, never "
        "evidence the genes behave. Execute them against AF's project-scoped eval "
        "endpoint (scripts/af_preflight.py proves the lane first; drive them PER CASE "
        "— a whole-agent run never completes, TAP-5730). Cases that reach live systems "
        "must state their observed result and forbid the call (EVAL FIXTURE, see "
        "wstore-pull-orders rule 5c and wstore-upsert-product rule 2b) — as authored, "
        "http-fetch-is-the-admin-tool wrote five real products to the catalog per run"
    )


def report_rubricless_golden_cases(agents: list[Path]) -> None:
    """Say the rubric-less case count out loud so it cannot silently regrow.

    A case whose only assertions are `output_schema_valid` + `guardrails_clean`
    asserts that the gene emitted conforming JSON and tripped no blocklist. That
    is a real property and a shape case is *supposed* to stop there — but the
    same shape passes for a gene that emitted the wrong values in the right
    keys. So a rubric-less case is only honest when its body says it is a shape
    case; unlabelled, it reads as behavioural coverage that does not exist.

    31 of 77 cases carried no rubric on 2026-08-07 and nothing named the number,
    which is how it got that high. A count, printed every run, is the cheapest
    control that survives an author who never reads this file.
    """
    total = rubricless = 0
    for path in agents:
        for case in (frontmatter(path) or {}).get("golden_cases") or []:
            if not isinstance(case, dict):
                continue
            total += 1
            if not any(a.get("kind") == "rubric" for a in case.get("assertions") or [] if isinstance(a, dict)):
                rubricless += 1
    if not total:
        return
    WARNINGS.append(
        f"{rubricless} of {total} golden case(s) carry no rubric assertion — they assert "
        "schema conformance and a clean guardrail sweep, never that the gene reached the "
        "right answer. Each one declares shape_only_because saying why that is the whole "
        "assertion (check_case_is_classified refuses one that does not). Watch this number: "
        "it only ever goes up by accident"
    )


def atlas_hosts(field: str) -> set[str]:
    """Hosts named by `field` rows in the store-atlas markdown table.

    Takes only the **first** backticked value in the value cell. The rest of the
    cell is prose that frequently backticks other field names — the
    `myshopify_domain` row ends "...301s to `primary_domain` for storefront
    traffic", and reading every backtick harvested `primary_domain` as if it were
    a hostname. That made the check accept the literal string `primary_domain` as
    a valid store default.

    `UNSET` is skipped: it means "no such storefront", never a wildcard
    (`skills/store-atlas/SKILL.md:134`).
    """
    path = SKILLS_DIR / "store-atlas" / "SKILL.md"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return set()

    hosts = set()
    pattern = rf"^\|\s*`{re.escape(field)}`\s*\|([^|]*)\|"
    for row in re.finditer(pattern, text, re.MULTILINE):
        first = re.search(r"`([^`]+)`", row.group(1))
        if first and first.group(1) != "UNSET":
            hosts.add(first.group(1))
    return hosts


def atlas_primary_domains() -> set[str]:
    """Storefront hosts — where shoppers and probe genes go."""
    return atlas_hosts("primary_domain")


#: The atlas rows that together address the agent-discovery surface. Under
#: `head: theme` all three hold the same host and this set collapses to one
#: entry; under `head: hydrogen` they split, because Hydrogen reverse-proxies
#: `/api/mcp` onto its own origin while UCP stays Shopify-served.
STOREFRONT_ORIGIN_FIELDS = ("primary_domain", "agent_origin", "ucp_origin")


def atlas_storefront_origins() -> set[str]:
    """Every origin the atlas names for the agent-discovery surface (TAP-5392).

    `primary_domain` alone was right only while the storefront had one origin.
    A headless store serves pages from the Hydrogen head, `/api/mcp` from that
    same head (Hydrogen proxies it), and `/api/ucp/mcp` plus `/.well-known/ucp`
    from the `.myshopify.com` origin — so a probe grant checked against
    `primary_domain` alone would reject the UCP origin as a stray host.
    """
    origins: set[str] = set()
    for field in STOREFRONT_ORIGIN_FIELDS:
        origins |= atlas_hosts(field)
    return origins


def check_storefront_probe_targets(path: Path, fm: dict) -> None:
    """A storefront-ingest gene may only fetch hosts the atlas names.

    These drifted once and nothing caught it: the atlas moved to the real Shopify
    storefront in 569db51 while `wstore-probe-storefront` kept the old marketing
    site in `tool_targets.WebFetch`. Egress is closed over that list, so the gene
    did not error — `agent-readiness` simply probed a host the atlas no longer
    knew about, and every check stayed green.

    Scoped to `wstore.ingest.storefront` on purpose. Platform-API genes
    (`fetch-social` → graph.facebook.com, `pull-tickets` → judge.me) hold hosts
    that are legitimately absent from the atlas, and a blanket rule would fail them.
    """
    if STOREFRONT_INGEST_CAPABILITY not in (fm.get("capabilities") or []):
        return
    declared = set((fm.get("tool_targets") or {}).get("WebFetch") or [])
    if not declared:
        return
    known = atlas_storefront_origins()
    if not known:
        return
    stray = sorted(declared - known)
    if stray:
        err(
            path,
            f"tool_targets.WebFetch names host(s) absent from the store-atlas "
            f"origin rows {list(STOREFRONT_ORIGIN_FIELDS)}: {stray} — "
            f"atlas knows {sorted(known)}",
        )
    # The other direction, and the one dual-origin introduces (TAP-5392). Egress
    # is closed over the declared list, so an atlas origin missing from it is not
    # an error at runtime — the gene simply never reaches that origin and reports
    # the surface as absent. "We checked and found nothing" and "we never checked"
    # are different results, and this gene is explicitly forbidden to conflate
    # them, so the omission has to fail here instead.
    missing = sorted(known - declared)
    if missing:
        err(
            path,
            f"store-atlas names origin(s) this storefront-ingest gene cannot "
            f"reach: {missing} — add them to tool_targets.WebFetch or the "
            f"surfaces they serve get reported as absent without being probed",
        )


def check_admin_gene_allowlist(path: Path, fm: dict) -> None:
    """A Shape-A gene's egress allowlist may only name atlas Admin hosts.

    The `http_fetch` sibling of `check_storefront_probe_targets`, and the same
    failure it guards against: egress is closed over this list, so a wrong entry
    does not error — the gene simply reaches somewhere the atlas never named.

    A platform-wide wildcard is the sharper case. `*.myshopify.com` reaches every
    Shopify store on the internet with this store's Admin credential attached,
    while the store-atlas is documented as the registry of truth where an
    unlisted target does not exist (`skills/store-atlas/SKILL.md`). The wildcard
    is not a broader allowlist so much as the absence of one.

    Concrete hosts are safe to inline here because `render_dna_core.revaluation`
    re-stamps hostname fields per instance, so a stamped store gets its own
    Admin host rather than inheriting this one's.
    """
    if HTTP_FETCH_GRANT not in (fm.get("allowed_tools") or []):
        return
    declared = set((fm.get("runtime_deps") or {}).get("http_allowlist") or [])
    if not declared:
        return  # check_agent_grants already errors on an empty allowlist
    if wildcards := sorted(h for h in declared if "*" in h):
        err(
            path,
            f"runtime_deps.http_allowlist uses wildcard host(s) {wildcards} — name "
            "the store-atlas myshopify_domain instead; a wildcard reaches every "
            "store on the platform with this store's Admin credential",
        )
    check_admin_gene_body_agrees(path)

    known = atlas_admin_hosts()
    if not known:
        return
    if stray := sorted(h for h in declared if "*" not in h and h not in known):
        err(
            path,
            f"runtime_deps.http_allowlist names host(s) absent from store-atlas "
            f"myshopify_domain: {stray} — atlas knows {sorted(known)}",
        )


def check_admin_gene_body_agrees(path: Path) -> None:
    """A Shape-A gene's prose must not teach the guard its frontmatter rejects.

    Narrowing the frontmatter alone left both ingest genes with a body still
    telling the model it was "pinned by `tool_targets` to
    `https://*.myshopify.com/*`" — a mechanism AF refuses and a wildcard the
    frontmatter no longer carries, ~160 lines below a comment saying so. The
    body is the gene's runtime prompt, so a stale sentence there is an
    instruction, not a stale comment.
    """
    text = body(path)
    for line in text.splitlines():
        if "*.myshopify.com" in line:
            err(
                path,
                f"body names the platform wildcard `*.myshopify.com`: {line.strip()[:90]!r} "
                "— name the store-atlas myshopify_domain instead",
            )
        if "tool_targets" in line and HTTP_FETCH_GRANT in line:
            err(
                path,
                f"body ties {HTTP_FETCH_GRANT} to `tool_targets`: {line.strip()[:90]!r} "
                "— the Shape A egress guard is runtime_deps.http_allowlist",
            )


def atlas_admin_hosts() -> set[str]:
    """Admin API hosts — where the Admin API and OAuth address the store.

    Deliberately distinct from `atlas_primary_domains`. Confusing the two "fails
    in a way that looks like a credential problem"
    (`skills/store-atlas/SKILL.md`), so the two readers stay separate.
    """
    return atlas_hosts("myshopify_domain")


def check_workflow_store_matches_atlas(path: Path, spec: dict) -> None:
    """A `store` input's default must be a host the atlas actually names.

    The default exists because these chromosomes are scheduled and a scheduled
    fire passes no inputs, so the host cannot come from the caller. That makes it
    a second copy of a fact the atlas owns — acceptable only while something
    keeps the copy honest, which is this.

    Without the seam entirely, run 319777413aa84cd3ab9d83ea0291267b returned empty
    from every Shopify source, and `analytics` named the cause: "shop domain not
    provided". A wrong default reproduces that ambiguity while looking configured.

    This rule is about the host being right. It says nothing about the credential —
    that is B6, still unresolved on 4.57.0 (docs/phase-b-plan.md § 4d).
    """
    for item in spec.get("inputs") or []:
        if not isinstance(item, dict) or item.get("name") != "store":
            continue
        default = item.get("default")
        if not default:
            err(path, "`store` input needs a non-empty default — a scheduled fire passes no inputs")
            continue
        known = atlas_admin_hosts()
        if known and default not in known:
            err(
                path,
                f"`store` default {default!r} is not a store-atlas myshopify_domain "
                f"— atlas knows {sorted(known)}",
            )


def check_admin_gene_receives_store(path: Path, spec: dict, nodes: dict, agents: dict) -> None:
    """A node running an Admin-API gene must be told which store.

    `check_workflow_store_matches_atlas` keeps a declared `store` default honest.
    It says nothing about a chromosome that never declares one — which is how this
    defect survived the M1 seam. store-health was fixed and cx-inbox was not, so
    `evidence` ran `wstore-pull-orders` with `since` and `for_threads` only.

    That gene's step 0 is unambiguous: with `store` absent or empty, report
    `shopify_orders: store input not supplied` and fetch nothing. So the node did
    not fail — it completed, validated against its schema, and returned an empty
    order book. `draft` may only assert what `evidence` returns, which means every
    staged reply was grounded on no order at all, and the digest reported a clean
    run. The same shape as run 319777413aa84cd3ab9d83ea0291267b, which "conflated
    the two and made a working credential look broken".

    Keyed on the Admin credential rather than the `*.myshopify.com` egress host:
    see SHOPIFY_ADMIN_CREDENTIAL. A storefront probe legitimately holds a myshopify
    host and must never receive the Admin domain.

    The credential alone is not enough, though — it has to be paired with the
    ability to call the API. A gene granted no tools cannot fetch whatever it is
    told, so every harm in the paragraph above is structurally impossible for it:
    there is no request to misdirect and no payload for a downstream gene to
    ground on. Such a gene holds the credential to be *refused* for lacking it,
    which is how the TAP-5194 cost gate stops a run before it spends. Demanding a
    `store` input there would make the workflow pass a host to a gene that has no
    way to contact it, which is cargo cult rather than a check.
    """
    admin_genes = {
        name
        for name, fm in agents.items()
        if (fm or {}).get("allowed_tools")
        and any(
            (cred or {}).get("key") == SHOPIFY_ADMIN_CREDENTIAL
            for cred in ((fm or {}).get("credentials") or [])
            if isinstance(cred, dict)
        )
    }
    if not admin_genes:
        return
    declared = {
        entry.get("name") for entry in (spec.get("inputs") or []) if isinstance(entry, dict)
    }
    for node_id, node in nodes.items():
        node = node or {}
        if node.get("agent") not in admin_genes:
            continue
        if STORE_INPUT in (node.get("inputs") or {}):
            continue
        detail = (
            f"workflow declares no '{STORE_INPUT}' input"
            if STORE_INPUT not in declared
            else f"workflow declares '{STORE_INPUT}' but the node does not pass it"
        )
        err(
            path,
            f"node '{node_id}' runs Admin-API gene '{node['agent']}' without a "
            f"'{STORE_INPUT}' input — {detail}. The gene reports 'store input not "
            "supplied' and fetches nothing, so the node completes green with an "
            "empty payload and downstream genes ground on it",
        )


def check_workflow_generated_defaults(path: Path, spec: dict) -> None:
    """A workflow carrying a fact inline must carry the current one.

    Genes have no filesystem, so anything a chromosome depends on — a skill pack,
    a provenance measurement — travels in an input `default`. That is a literal
    second copy of a fact something else owns, and it is tolerable only while it
    cannot drift, which is this check's whole job.

    Absence is an error, not a warning. A gene told to apply a taxonomy and given
    nothing does not fail loudly: `wstore-classify` is instructed to "never invent
    a label" and to fall back to a label it also cannot read, so it refuses real
    customer text and the chromosome reports a clean run that classified nothing.

    Stays **offline**, and that is a constraint rather than a happy accident.
    `input_source.render` reads `skills/` and `data/` and nothing else — no
    network, no `c2pa` import, no walk of the sibling asset tree. Regenerating the
    provenance snapshot is a separate, explicit step, for the same reason the
    mapping is explicit: a gene must never silently acquire an input, and a
    validator must never silently re-measure the thing it is validating.
    """
    workflow_name = spec.get("name")
    mapping = WORKFLOW_INPUT_SOURCES.get(workflow_name)
    if not mapping:
        return

    declared = {
        item.get("name"): item
        for item in (spec.get("inputs") or [])
        if isinstance(item, dict)
    }

    for input_name, source in sorted(mapping.items()):
        entry = declared.get(input_name)
        if entry is None:
            err(path, f"missing `{input_name}` input carrying {source[1]}")
            continue
        default = entry.get("default")
        if not default or not str(default).strip():
            err(
                path,
                f"`{input_name}` has no default — this chromosome is scheduled and a "
                f"scheduled fire passes no inputs, so {source[1]} would never reach "
                "the gene",
            )
            continue
        try:
            expected = input_source.render(source)
        except SkillPackError as exc:
            err(path, f"`{input_name}`: {exc}")
            continue
        if str(default).strip() != expected.strip():
            err(
                path,
                f"`{input_name}` default is stale against {source[1]} — "
                f"{input_source.regenerate_hint(source)}",
            )


def check_agent_shape(path: Path, fm: dict) -> None:
    """Frontmatter the AF loader must be able to parse at all."""
    bad = HYPHEN_KEYS & set(fm)
    if bad:
        err(path, f"hyphen-case keys rejected by the AF loader: {sorted(bad)} — use snake_case")
    missing = AGENT_REQUIRED - set(fm)
    if missing:
        err(path, f"missing required fields: {sorted(missing)}")
    # Scout layout: agents are flat `<name>.md` files and the publish script
    # derives the agent name from the filename stem. (The `<name>/AGENTS.md`
    # directory form is the *nlt* layout — mixing them means af_publish
    # discovers nothing and every workflow reports its agents as unpublished.)
    if fm.get("name") != path.stem:
        err(path, f"name '{fm.get('name')}' != filename stem '{path.stem}'")
    for key in ("output_schema", "input_schema"):
        if fm.get(key):
            try:
                json.loads(fm[key])
            except json.JSONDecodeError as exc:
                err(path, f"{key} is not valid JSON: {exc}")
    if fm.get("risk_level") == "high" and not (fm.get("guardrails") or fm.get("completion_criteria")):
        err(path, "risk_level high requires guardrails or completion_criteria")


def check_agent_closed_sets(path: Path, fm: dict) -> None:
    """Enum and guardrail values the platform validates as closed unions."""
    for field, allowed in VALID_ENUMS.items():
        if field in fm and str(fm[field]) not in allowed:
            err(path, f"{field}={fm[field]!r} is not one of {sorted(allowed)} — publish would 422")

    # Not a closed set — see SHARE_SCOPE_GROUP in kit_rules for why this one
    # field needs a pattern branch rather than a membership test.
    scope = str(fm.get("share_scope", "")) if "share_scope" in fm else ""
    if scope and scope not in SHARE_SCOPE_BUILTIN and not SHARE_SCOPE_GROUP.match(scope):
        err(
            path,
            f"share_scope={scope!r} is not one of {sorted(SHARE_SCOPE_BUILTIN)} nor a well-formed "
            "'group:<name>' (lowercase alphanumeric + hyphens, <=64) — publish would 422",
        )

    for guardrail in fm.get("guardrails") or []:
        if not isinstance(guardrail, dict):
            err(path, "guardrails entries must be mappings")
            continue
        gtype = guardrail.get("type")
        if gtype not in VALID_GUARDRAILS:
            err(
                path,
                f"guardrail type {gtype!r} is not in the platform's closed union "
                f"{sorted(VALID_GUARDRAILS)} — publish would 422",
            )
            continue
        if gtype == "extension" and not str(guardrail.get("text", "")).strip():
            err(path, "extension guardrail requires non-empty 'text'")


def check_agent_grants(path: Path, fm: dict) -> None:
    """Trust tagging at the ingest boundary, and least-tools coherence."""
    # Species-three: every ingest gene must emit the trust tag (the quarantine
    # architecture depends on it being set at the boundary, not inferred later).
    caps = fm.get("capabilities") or []
    if any(str(c).startswith("wstore.ingest.") for c in caps):
        schema = fm.get("output_schema") or ""
        if "trust" not in schema:
            err(path, "ingest gene's output_schema must include the 'trust' envelope field")

    grants = fm.get("allowed_tools") or ""
    tools = grants if isinstance(grants, list) else [grants] if grants else []
    targets = fm.get("tool_targets") or {}
    for tool in TARGETED_TOOLS:
        if tool in tools and not targets.get(tool):
            err(path, f"{tool} grant requires a non-empty tool_targets.{tool} allowlist")

    # AF coherence Rule 5, mirrored locally (TAP-5334). Shape A reads its
    # allowlist from `runtime_deps.http_allowlist` and ignores `tool_targets`,
    # so the two rules must not be collapsed: an empty allowlist is deny-all
    # that skips the wire-up, leaving the gene to narrate instead of fetch.
    if HTTP_FETCH_GRANT in tools:
        if HTTP_FETCH_GRANT in targets:
            err(
                path,
                f"tool_targets.{HTTP_FETCH_GRANT} is not a thing — AF rejects it "
                f"('no expansion path'). Use runtime_deps.http_allowlist",
            )
        allowlist = (fm.get("runtime_deps") or {}).get("http_allowlist") or []
        if not allowlist:
            err(
                path,
                f"{HTTP_FETCH_GRANT} grant requires a non-empty "
                "runtime_deps.http_allowlist — empty is deny-all and AF skips "
                "the Shape A wire-up, so the gene gets no fetch tool at all",
            )
        for entry in allowlist:
            if not isinstance(entry, str) or not entry.strip():
                err(path, f"runtime_deps.http_allowlist entry must be a non-empty string: {entry!r}")
            elif any(c in entry for c in HTTP_ALLOWLIST_FORBIDDEN_CHARS) or "://" in entry:
                err(
                    path,
                    f"runtime_deps.http_allowlist entry must be a bare hostname or "
                    f"'*.suffix' — no scheme, path, port, or whitespace: {entry!r}",
                )


def check_credential_injection(path: Path, fm: dict) -> None:
    """A credential for a custom-header API must say so, or it goes out as Bearer.

    TAP-5368 fixed the half of this that was AF's: a gene that declares
    `credentials:` and calls `http_fetch` without auth headers now gets the token
    merged into the request. What it cannot know is *how* the target API wants it.
    The default is `Authorization: Bearer`, and Shopify's Admin API authenticates
    on `X-Shopify-Access-Token` — it ignores Bearer entirely.

    So the fix landing turns "the credential never arrives" into "the credential
    arrives in a header the API does not read", and both present as an ordinary
    401. This repo has now spent one full session distinguishing a 401 that means
    "dead token" from a 401 that means "the plumbing is broken"; that is the cost
    this check exists to avoid paying twice.

    Only fires for a gene that can actually make the request. A credential on a
    gene with no `http_fetch` grant is passed to a subprocess as an env var, where
    `inject` is not consulted at all and demanding it would be noise.
    """
    grants = fm.get("allowed_tools") or ""
    tools = grants if isinstance(grants, list) else [grants] if grants else []
    if HTTP_FETCH_GRANT not in tools:
        return

    for cred in fm.get("credentials") or []:
        if not isinstance(cred, dict):
            err(path, "credentials entries must be mappings")
            continue
        expected = CREDENTIAL_AUTH_HEADERS.get(cred.get("key"))
        if not expected:
            continue
        if cred.get("inject") != INJECT_HEADER or cred.get("header_name") != expected:
            err(
                path,
                f"credential '{cred.get('key')}' needs `inject: {INJECT_HEADER}` and "
                f"`header_name: {expected}` — that API does not accept Bearer, and AF "
                f"auto-injects Bearer by default when a gene omits auth headers "
                f"(TAP-5368). Got inject={cred.get('inject')!r} "
                f"header_name={cred.get('header_name')!r}; the request would 401 and "
                "look exactly like a dead token",
            )


def check_no_prewritten_credential_failure(path: Path, fm: dict) -> None:
    """A gene's body must not hand it a ready-made "my credential failed" sentence.

    `wstore-pull-orders` carried this in its own rule 6, as the worked example for
    canonical source ids:

        shopify_orders: WSTORE_SHOPIFY_ADMIN_TOKEN not vaulted

    On 2026-07-31 it emitted a near-verbatim copy — `...not vaulted or invalid` —
    while that same credential was returning live Shopify data to
    `wstore-pull-analytics` in the same run, and a direct call to `orders.json`
    returned HTTP 200 with an empty list. The store simply had no orders. The
    digest read the false entry and told the owner the measurement system was
    broken.

    The discriminator was exact. Four ingest genes carry an example of this shape;
    `wstore-pull-orders` was the only one whose example named a credential it
    declares `required: true`, and the only one that lied. The others illustrate
    with an optional or undeclared key, so completing the pattern produces a
    sentence about a source that really is unconfigured.

    A gene cannot see its own credentials — they are injected at the tool layer and
    never enter prompt context (OWASP LLM07). So it has no way to *check* the claim
    the example invites it to make, and the claim is unfalsifiable from where it
    stands. Illustrate with a key the gene does not depend on.
    """
    required = {
        cred.get("key")
        for cred in (fm.get("credentials") or [])
        if isinstance(cred, dict) and cred.get("required")
    }
    if not required:
        return
    lines = body(path).splitlines()
    for key in sorted(k for k in required if k):
        for i, line in enumerate(lines):
            if key not in line or not any(t in line.lower() for t in CREDENTIAL_FAILURE_TERMS):
                continue
            # Gated on an observation is the *correct* shape, and the rule must not
            # punish it — `wstore-upsert-product` says "if the Admin API answers
            # 401/403, report ...", which is precisely what this check wants every
            # gene to do. The hazard is the ungated example: a sentence the gene can
            # emit without having seen anything. Read a small window rather than the
            # line alone, because the condition usually sits on the line above.
            window = " ".join(lines[max(0, i - 2) : i + 3])
            if any(status in window for status in OBSERVED_FAILURE_MARKERS):
                continue
            err(
                path,
                f"body illustrates a failure using required credential {key!r} without "
                f"conditioning it on an observed response: {line.strip()[:80]!r} — a gene "
                "cannot see its own credentials, so this is a claim it has no way to check "
                "and will pattern-complete when it has nothing else to report. Gate it on a "
                f"status ({', '.join(OBSERVED_FAILURE_MARKERS)}) or illustrate with an "
                "optional key",
            )
            break


def check_agent_writer_is_trust_aware(path: Path, fm: dict) -> None:
    """A gene that writes must know which envelope it is handling.

    `memory_profile: full` plus `share_scope: domain` is a write into memory
    every other chromosome later recalls as trusted context. A writer whose body
    never mentions the trust envelope cannot tell a cleared item from a blocked
    one, so a quarantined payload persists and is fed back as fact.
    """
    if fm.get("memory_profile") != "full":
        return
    text = body(path).lower()
    if not any(term in text for term in TRUST_ENVELOPE_TERMS):
        err(
            path,
            f"memory_profile 'full' writes to shared memory, but the body never references the "
            f"trust envelope {list(TRUST_ENVELOPE_TERMS)} — it cannot tell a cleared item from a "
            "blocked one",
        )


def check_fleet_group_is_reslug_immune() -> None:
    """The fleet group name must mean the same thing in every stamped store.

    `FLEET_HIVE_GROUP` travels two ways at once: genes name it in frontmatter,
    and this validator family is copied into each stamped repo. Both are
    re-slugged. So a group name containing an identity token is rewritten per
    store — each store joins a private group of one, no cross-store row is ever
    shared, and the stamped validator rewrites its own constant to match, which
    is what makes the failure invisible from inside.

    Probing with a synthetic destination identity is the point: it asks "would
    a *rename* change this name?", which is exactly the property required, and
    it does so without needing a real second store to exist yet.
    """
    try:
        src = render_dna_core.Identity.of(render_dna_core.load_species(SPECIES))
    except (SystemExit, KeyError) as exc:
        err(CORE_DIR / "species" / f"{SPECIES}.yaml", f"cannot read species identity: {exc}")
        return
    probe = render_dna_core.Identity(prefix="probe", slug="probe-store", env_prefix="PROBE")
    renamed = render_dna_core.reslug(FLEET_HIVE_GROUP, src, probe)
    if renamed != FLEET_HIVE_GROUP:
        err(
            CORE_DIR / "genes",
            f"FLEET_HIVE_GROUP {FLEET_HIVE_GROUP!r} contains an identity token — re-slugging rewrites "
            f"it to {renamed!r}, so every stamped store would join a different group and the shared "
            "pool would never receive a cross-store row. Choose a fleet name with no identity token.",
        )


def check_agent_hive_membership(path: Path, fm: dict) -> None:
    """A gene writing to a hive group must be one provisioning actually registers.

    FR-6's acceptance clause. Two ways this goes silently wrong, both checked
    here because neither surfaces at publish time:

    1. **An unregistered group name.** Membership is declared operator-side by
       the provisioning skill's step 6, which knows exactly one group. A gene
       naming any other group is never a member of it, and neither outcome is
       recoverable at runtime: brain's REST save path refuses the write with a
       400, and its propagation path silently downgrades the row to private.
       Either way the fleet never receives it.
    2. **A scope no write path reads.** `share_scope` reaches the wire as
       `agent_scope` only on AF's post-run save, which is gated on
       `memory_profile == "full"` (`orchestrator/steps.py:924-940`). On a
       `readonly`/`none` gene a group scope is inert decoration that reads,
       to anyone auditing the genome, like fleet participation that is not
       happening.
    """
    scope = str(fm.get("share_scope", ""))
    if not scope.startswith("group:"):
        return
    group = scope.partition(":")[2]
    if group != FLEET_HIVE_GROUP:
        err(
            path,
            f"share_scope names hive group {group!r}, but provisioning step 6 declares membership of "
            f"{FLEET_HIVE_GROUP!r} only — a non-member's group write is refused (REST) or downgraded "
            "to private (propagation), so the fleet pool never receives the row",
        )
    if fm.get("memory_profile") != "full":
        err(
            path,
            f"share_scope={scope!r} declares a fleet write, but memory_profile="
            f"{fm.get('memory_profile')!r} means no write path carries it — AF only forwards "
            "share_scope as agent_scope when memory_profile is 'full'",
        )


def check_agent(path: Path) -> dict | None:
    """Check one gene and hand its frontmatter back — the workflow checks need it.

    Returning it here keeps the file parsed exactly once, so a malformed
    frontmatter block is reported once rather than per consumer.
    """
    fm = frontmatter(path)
    if fm is None:
        return None
    check_agent_shape(path, fm)
    check_agent_closed_sets(path, fm)
    check_agent_grants(path, fm)
    check_credential_injection(path, fm)
    check_no_prewritten_credential_failure(path, fm)
    check_agent_writer_is_trust_aware(path, fm)
    check_agent_hive_membership(path, fm)
    check_storefront_probe_targets(path, fm)
    check_admin_gene_allowlist(path, fm)
    if not fm.get("golden_cases"):
        warn(path, "no golden_cases declared")
    check_golden_cases(path, fm)
    return fm


def node_ref_fields(node: dict) -> set[tuple[str, str]]:
    """(node id, dotted field) per `$ref` input — `$scan.safe_payload` -> ('scan', 'safe_payload')."""
    return {
        (value[1:].partition(".")[0], value[1:].partition(".")[2])
        for value in (node.get("inputs") or {}).values()
        if isinstance(value, str) and value.startswith("$")
    }


def node_refs(node: dict) -> set[str]:
    """Node ids this node names in its inputs — `$scan.safe_payload` -> `scan`."""
    return {head for head, _ in node_ref_fields(node)}


def descendants(nodes: dict, root: str) -> set[str]:
    """Every node that transitively depends_on `root`."""
    seen: set[str] = set()
    frontier = {root}
    while frontier:
        frontier = {
            nid for nid, n in nodes.items() if frontier & set((n or {}).get("depends_on") or [])
        } - seen - {root}
        seen |= frontier
    return seen


def capabilities(node: dict, agents: dict) -> list:
    return (agents.get(node.get("agent")) or {}).get("capabilities") or []


def check_node_output_contract(path: Path, node_id: str, node: dict, agents: dict) -> None:
    """A gene's own output_schema is never enforced — only the node's is.

    The orchestrator validates node-level schemas only, so a node without one
    stores whatever the gene said. That is how `adspend`, `social`,
    `pull-tickets`, and `scan` each shipped reporting `complete` while emitting
    prose and doing nothing, four times, each caught only by a human reading the
    raw node output.
    """
    agent = node.get("agent")
    if not agent:
        return
    if (agents.get(agent) or {}).get("output_schema") and not node.get("output_schema"):
        err(
            path,
            f"node '{node_id}' declares no node-level output_schema but its agent '{agent}' "
            "declares one — the orchestrator validates only node-level schemas, so the gene's "
            "prose would be stored as success",
        )


def check_node_wildcard_input(path: Path, node_id: str, node: dict, agents: dict) -> None:
    """`$all_outputs` is the scanner's privilege, not a convenience."""
    if QUARANTINE_CAPABILITY in capabilities(node, agents):
        return
    for key, value in (node.get("inputs") or {}).items():
        if value == WILDCARD_INPUT:
            err(
                path,
                f"node '{node_id}' input '{key}' reads {WILDCARD_INPUT} but its agent does not "
                f"declare '{QUARANTINE_CAPABILITY}' — the wildcard reads around every intended "
                "narrowing; name the inputs it actually needs",
            )


def schema_describes_path(schema: dict, segments: list[str]) -> bool:
    """Walk an output_schema as far as it actually describes `segments`.

    Stops agreeing the moment the schema runs out of `properties` to check —
    a partial schema must not be read as a denial.
    """
    cursor: object = schema
    for segment in segments:
        if not isinstance(cursor, dict):
            return True
        properties = cursor.get("properties")
        if not isinstance(properties, dict):
            return True
        if segment not in properties:
            return False
        cursor = properties[segment]
    return True


def schema_requires_path(schema: dict, segments: list[str]) -> bool:
    """Whether every segment of `segments` is `required`, not merely described.

    Permissive in the same direction as `schema_describes_path`: the moment the
    schema stops describing the path, stop claiming anything about it.
    """
    cursor: object = schema
    for segment in segments:
        if not isinstance(cursor, dict):
            return True
        properties = cursor.get("properties")
        if not isinstance(properties, dict) or segment not in properties:
            return True
        if segment not in (cursor.get("required") or []):
            return False
        cursor = properties[segment]
    return True


def check_node_input_refs(path: Path, node_id: str, node: dict, spec: dict, nodes: dict) -> None:
    """Every `$ref` names something real, and every dotted path exists.

    The platform resolves these at runtime only — its DAG check validates
    `depends_on` names and nothing else — so a mistyped field is a live
    failure rather than a publish error. At `spec_version: 1` it is not even
    that: the ref quietly resolves to an empty string, which reads downstream
    as "the gate cleared nothing" rather than "this reference is wrong".
    """
    # `inputs:` accepts bare names or typed objects, mixed in one list.
    declared = {
        entry.get("name") if isinstance(entry, dict) else entry for entry in (spec.get("inputs") or [])
    }
    for key, value in (node.get("inputs") or {}).items():
        if not isinstance(value, str) or not value.startswith("$"):
            continue
        ref = value[1:]
        head, _, tail = ref.partition(".")
        if head in RESERVED_INPUT_REFS or head in declared or ref in declared:
            continue
        if head not in nodes:
            err(
                path,
                f"node '{node_id}' input '{key}' reads ${ref}, which is neither a node "
                "nor a declared workflow input",
            )
            continue
        upstream = (nodes[head] or {}).get("output_schema")
        if not tail or not isinstance(upstream, dict):
            continue
        if not schema_describes_path(upstream, tail.split(".")):
            err(
                path,
                f"node '{node_id}' input '{key}' reads ${ref}, but node '{head}' declares no "
                f"'{tail}' in its output_schema",
            )
        elif int(spec.get("spec_version") or 1) >= 2 and not schema_requires_path(
            upstream, tail.split(".")
        ):
            # Described but optional is a runtime bomb, not a style nit. At
            # spec_version 2 the orchestrator raises InputRefError on an absent
            # field rather than collapsing it to "" — so a producer that legally
            # omits the key kills the consumer on the day it degrades, which is
            # precisely the day the field mattered. Found on the Phase 5
            # `sources_unavailable` plumbing, where every ingest node described
            # it and none required it.
            err(
                path,
                f"node '{node_id}' input '{key}' reads ${ref}, but node '{head}' does not mark "
                f"'{tail}' required — at spec_version 2 an absent field is a hard InputRefError, "
                f"so '{head}' must always emit it (empty, not missing)",
            )


def check_quarantine_routing(path: Path, nodes: dict, agents: dict) -> None:
    """Downstream of the gate, read the gate — not the sources it judged.

    The species design states the invariant plainly: nothing downstream reads a
    ticket body until it has a verdict. A node that depends on the gate and then
    names one of the gate's own sources directly has the verdict in its DAG and
    the unjudged payload in its inputs.

    "What the gate judged" is its *direct* `depends_on`, not its whole
    ancestry. A gate sitting mid-DAG inherits ancestors that are nothing to do
    with the untrusted payload — cx-inbox's evidence gate transitively descends
    from `classify`, whose output is triage derived from an already-gated
    source — and flagging those is a false positive that would push a reader
    toward rewiring something already correct.
    """
    for gate in [nid for nid, n in nodes.items() if QUARANTINE_CAPABILITY in capabilities(n or {}, agents)]:
        scanned = set((nodes[gate] or {}).get("depends_on") or [])
        for node_id in descendants(nodes, gate):
            read_around = sorted(
                {
                    head
                    for head, field in node_ref_fields(nodes[node_id] or {})
                    if head in scanned and field not in GATE_TRANSPARENT_FIELDS
                }
            )
            if read_around:
                err(
                    path,
                    f"node '{node_id}' depends on quarantine node '{gate}' but reads "
                    f"{read_around} directly — that is the payload '{gate}' judged, unjudged; "
                    f"read it through '{gate}' instead",
                )


def check_script_id(path: Path, node_id: str, node: dict) -> None:
    """A `kind: script` node must name a handler AF has actually registered.

    This is the guard that replaced blocking `kind: script` outright. That block
    was measurably wrong — a `PUT` carrying `kind: script` and
    `script_id: external-job-relay` returned 201 against 4.57.1 — but deleting it
    without replacement would remove the one real hazard here: publish validation
    is schema-only, so it accepts *any* `script_id` string. An invented one is not
    caught until the node executes, which is a live failure rather than a publish
    error, and this repo has already paid for that class of bug once.

    So the axis moves from the kind to the id, and the id comes from the platform's
    own `script_ids` rather than from anyone's memory of the AF filesystem.
    """
    script_id = node.get(SCRIPT_ID_FIELD)
    if not script_id:
        err(
            path,
            f"node '{node_id}' kind='{SCRIPT_KIND}' declares no '{SCRIPT_ID_FIELD}' — "
            f"AF {AF_VERSION} registers {sorted(VALID_SCRIPT_IDS)}",
        )
    elif script_id not in VALID_SCRIPT_IDS:
        err(
            path,
            f"node '{node_id}' {SCRIPT_ID_FIELD}={script_id!r} is not registered in AF "
            f"{AF_VERSION} — it knows {sorted(VALID_SCRIPT_IDS)}. Publish will NOT catch "
            "this (validation is schema-only); the node fails at execution instead",
        )


def check_workflow_node(path: Path, node_id: str, node: dict, nodes: dict, agents: dict) -> None:
    for dep in node.get("depends_on", []):
        if dep not in nodes:
            err(path, f"node '{node_id}' depends_on unknown node '{dep}'")
    agent = node.get("agent")
    if agent and agent not in agents:
        err(path, f"node '{node_id}' references unknown agent '{agent}'")
    kind = node.get("kind")
    if kind is not None and kind not in VALID_NODE_KINDS:
        err(
            path,
            f"node '{node_id}' kind={kind!r} is not in AF {AF_VERSION}'s node_kinds "
            f"{sorted(VALID_NODE_KINDS)} (agentforge/capabilities-manifest.json)",
        )
    elif kind in PATTERN_A_UNAVAILABLE_KINDS:
        err(
            path,
            f"node '{node_id}' kind={kind!r}: not reachable from a Pattern A consumer — "
            "`python` resolves only backend.* callables, and this repo ships no code into "
            "the AF image, so there is nothing it can name",
        )
    elif kind == SCRIPT_KIND:
        check_script_id(path, node_id, node)
    if kind == "transform" and not str(node.get("expression", "")).strip():
        err(path, f"node '{node_id}' kind='transform' requires a non-empty 'expression'")
    check_node_output_contract(path, node_id, node, agents)
    check_node_wildcard_input(path, node_id, node, agents)


def check_scheduled_inputs_have_defaults(path: Path, spec: dict, nodes: dict) -> None:
    """A scheduled fire passes no inputs, so every referenced input needs a default.

    Two locally-sensible decisions that contradict each other across files: an
    input declared without a default so a missing corpus fails loudly at kickoff
    (deliberate, and documented in agent-readiness.yaml), plus a `schedule`
    trigger that can never supply one. The result is a run that dies on
    InputRefError before any node executes, at $0, once a week, silently.

    Only workflows that actually fire on a schedule are in scope. A manually
    invoked workflow may require inputs of its caller — that is `listing-pipeline`
    working as intended, not a defect.
    """
    if not any((t or {}).get("type") == "schedule" for t in (spec.get("triggers") or [])):
        return
    defaults = {
        entry.get("name"): entry.get("default")
        for entry in (spec.get("inputs") or [])
        if isinstance(entry, dict)
    }
    declared = {e.get("name") if isinstance(e, dict) else e for e in (spec.get("inputs") or [])}
    referenced = {head for node in nodes.values() for head, _ in node_ref_fields(node or {})}
    for name in sorted(referenced & declared):
        if defaults.get(name) is None:
            err(
                path,
                f"workflow fires on a schedule and a node references input '{name}', which "
                "declares no default — a scheduled fire passes no inputs, so every run dies on "
                "InputRefError before any node executes; give it a default or drop the trigger",
            )


def check_workflow_goal_and_loops(path: Path, spec: dict, nodes: dict) -> None:
    goal = spec.get("goal")
    if goal is not None:
        verify = goal.get("verify") if isinstance(goal, dict) else None
        if not isinstance(verify, dict) or "kind" not in verify:
            err(path, "goal requires verify with kind (+ expression/path)")
        elif verify["kind"] in {"predicate", "judge"} and "." not in str(verify.get("expression", "")):
            err(path, "goal.verify expression must be '<node>.<field>'")
    for loop_id, loop in (spec.get("loops") or {}).items():
        for member in (loop or {}).get("members", []):
            if member not in nodes:
                err(path, f"loop '{loop_id}' member '{member}' is not a node")
        convergence = str((loop or {}).get("convergence", ""))
        if convergence and "." in convergence and convergence.split(".")[0] not in nodes:
            err(path, f"loop '{loop_id}' convergence references unknown node '{convergence}'")


def check_workflow(path: Path, agents: dict) -> None:
    try:
        spec = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        err(path, f"YAML error: {exc}")
        return
    if not isinstance(spec, dict):
        err(path, "not a mapping")
        return
    check_workflow_store_matches_atlas(path, spec)
    check_workflow_generated_defaults(path, spec)
    nodes = spec.get("nodes")
    if not isinstance(nodes, dict) or not nodes:
        err(path, "missing or empty nodes")
        return
    if spec.get("name") != path.stem:
        err(path, f"name '{spec.get('name')}' != filename '{path.stem}'")
    if spec.get("output") not in nodes:
        err(path, f"output '{spec.get('output')}' is not a node")
    for node_id, node in nodes.items():
        check_workflow_node(path, node_id, node or {}, nodes, agents)
        check_node_input_refs(path, node_id, node or {}, spec, nodes)
    check_quarantine_routing(path, nodes, agents)
    check_workflow_goal_and_loops(path, spec, nodes)
    check_scheduled_inputs_have_defaults(path, spec, nodes)
    check_admin_gene_receives_store(path, spec, nodes, agents)


def check_skill(path: Path) -> None:
    fm = frontmatter(path)
    if fm is None:
        return
    if not fm.get("name") or not fm.get("description"):
        err(path, "skill needs name and description")
    elif fm["name"] != path.parent.name:
        err(path, f"name '{fm['name']}' != directory '{path.parent.name}'")


def check_policy(path: Path) -> None:
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        err(path, f"YAML error: {exc}")
        return
    doc = doc or {}
    # TAP-5402 operator disclosure ledger — not an AF PolicyEngine rules file.
    # Same directory so stamping/carry picks it up; different schema on purpose.
    if path.name == "c2pa-disclosure-exceptions.yaml":
        exceptions = doc.get("exceptions")
        if not isinstance(exceptions, list) or not exceptions:
            err(path, "disclosure exceptions file needs a non-empty 'exceptions' list")
            return
        seen: set[str] = set()
        for entry in exceptions:
            if not isinstance(entry, dict):
                err(path, "each exception must be a mapping")
                continue
            hero = entry.get("path")
            if not hero:
                err(path, "exception missing path")
                continue
            if hero in seen:
                err(path, f"duplicate exception path '{hero}'")
            seen.add(hero)
            if not entry.get("reason"):
                err(path, f"exception '{hero}' missing reason")
            if not entry.get("source_id"):
                err(path, f"exception '{hero}' missing source_id")
        return
    rules = doc.get("rules")
    if not isinstance(rules, list) or not rules:
        err(path, "policy file needs a non-empty 'rules' list")
        return
    seen = set()
    for rule in rules:
        if not isinstance(rule, dict):
            err(path, "each rule must be a mapping")
            continue
        rid = rule.get("rule_id")
        if not rid:
            err(path, "rule missing rule_id")
            continue
        if rid in seen:
            err(path, f"duplicate rule_id '{rid}'")
        seen.add(rid)
        decision = rule.get("decision")
        if decision not in VALID_DECISIONS:
            err(path, f"rule '{rid}': decision must be one of {sorted(VALID_DECISIONS)}, got {decision!r}")
        if decision == "mask" and not rule.get("mask_fields"):
            err(path, f"rule '{rid}': decision 'mask' needs mask_fields")
    check_policy_deny_covers_every_workflow(path, rules)


def check_policy_deny_covers_every_workflow(path: Path, rules: list) -> None:
    """A confine-to-one-chromosome deny must name every workflow it does not permit.

    TAP-5953. These rules come in pairs: a deny on some capability set, and an
    allow on the same set narrowed to the one chromosome that may use it. The
    deny originally carried no `workflow_context`, and an empty condition list
    matches ANY workflow — so the deny also matched inside the permitted
    chromosome, and since deny wins regardless of priority the allow was
    unreachable. Strict enforcement would have blocked the flow the chromosome
    exists to run.

    AF's rule vocabulary has no negation (`workflow_context` is a positive
    fnmatch list), so "everywhere except X" can only be written as an
    enumeration. An enumeration is exactly the thing that rots: add a workflow,
    forget the rules file, and the deny stops matching there. Nothing matching is
    an ALLOW, so the failure mode is silent and open — a new chromosome would
    quietly gain money and broadcast capabilities.

    This closes that at publish time. For every deny/allow pair on the same
    capability set, the union of the deny's contexts and the allow's must cover
    every workflow on disk. The empty string is required separately: the engine
    resolves an absent workflow to `""`, which is the ad-hoc invoke — the caller
    the confinement most wants to stop, and the one an enumeration of *files*
    would never produce.
    """
    on_disk = {p.stem for p in sorted(WORKFLOWS_DIR.glob("*.yaml"))}
    if not on_disk:
        return

    def cap_key(rule: dict) -> tuple:
        return tuple(sorted(rule.get("capabilities") or []))

    allows = {
        cap_key(r): r
        for r in rules
        if isinstance(r, dict) and r.get("decision") == "allow" and r.get("workflow_context")
    }
    for rule in rules:
        if not isinstance(rule, dict) or rule.get("decision") != "deny":
            continue
        paired = allows.get(cap_key(rule))
        if paired is None or not cap_key(rule):
            continue
        rid = rule.get("rule_id")
        contexts = rule.get("workflow_context")
        if not contexts:
            err(
                path,
                f"rule '{rid}' denies what '{paired.get('rule_id')}' allows inside "
                f"{paired['workflow_context']}, but names no workflow_context — an empty "
                "condition matches every workflow, and deny wins over priority, so the "
                "paired allow can never fire",
            )
            continue
        if "" not in contexts:
            err(
                path,
                f"rule '{rid}': workflow_context must include \"\" — the engine resolves an "
                "absent workflow to the empty string, so without it an ad-hoc invoke carrying "
                "these capabilities is not denied",
            )
        uncovered = sorted(on_disk - set(contexts) - set(paired["workflow_context"]))
        if uncovered:
            err(
                path,
                f"rule '{rid}': workflow(s) {uncovered} exist but are named by neither this "
                f"deny nor '{paired.get('rule_id')}' — nothing matching is an ALLOW, so those "
                "chromosomes silently gain these capabilities. Add each to one list or the other",
            )


def check_dna_core() -> None:
    """Shared genes must still render byte-identical from dna-core (design § 8)."""
    try:
        rendered = render_dna_core.render_all(render_dna_core.load_species(SPECIES))
    except SystemExit as exc:
        err(CORE_DIR / "species" / f"{SPECIES}.yaml", f"dna-core render failed: {exc.code}")
        return
    for path, text in sorted(rendered.items()):
        if not path.exists():
            err(path, "shared gene exists in dna-core but is not published")
        elif path.read_text(encoding="utf-8") != text:
            err(path, "drifted from dna-core — run 'python3 scripts/render_dna_core.py' for the diff")


def check_deployment_packs() -> None:
    """Deployment packs must still render byte-identical from this store's intake.

    The sibling of `check_dna_core`, and it exists for a sharper reason: these
    two packs name the hosts a gene may touch and the brand it may speak as.
    Before they were rendered, `--instance` copied them verbatim, so every
    stamped store inherited the previous store's domains — wrong data rather
    than a missing value, and nothing anywhere compared the two.
    """
    try:
        rendered = render_dna_core.render_packs(render_dna_core.load_intake(SPECIES))
    except SystemExit as exc:
        err(render_dna_core.INTAKE_DIR / f"{SPECIES}.yaml", f"pack render failed: {exc.code}")
        return
    for path, text in sorted(rendered.items()):
        if not path.exists():
            err(path, "deployment pack exists in dna-core/packs but is not published")
        elif path.read_text(encoding="utf-8") != text:
            err(path, "drifted from its intake — run 'python3 scripts/render_dna_core.py --write-packs'")


def check_intake_required_slots() -> None:
    """No required intake field may ship UNSET (`render_dna_core.unfilled_required`).

    The rule itself lives beside the schema loader so the stamp and this check
    cannot drift apart — a stamp must never produce a repo its own validator
    rejects, which is only true while both ask the same question.
    """
    intake_path = render_dna_core.INTAKE_DIR / f"{SPECIES}.yaml"
    try:
        intake = render_dna_core.load_intake(SPECIES)
    except SystemExit as exc:
        err(intake_path, f"cannot read intake: {exc.code}")
        return
    for finding in render_dna_core.unfilled_required(intake):
        err(intake_path, finding)


def check_skill_tiers(skills: list[Path]) -> None:
    """Every pack is classified, and exported tiers stay free of species coupling."""
    path = CORE_DIR / "skills.yaml"
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        err(path, f"cannot read skill tier manifest: {exc}")
        return
    tiers = doc.get("skills")
    if not isinstance(tiers, dict) or not tiers:
        err(path, "needs a non-empty 'skills' mapping")
        return

    on_disk = {p.parent.name for p in skills}
    for name in sorted(on_disk - set(tiers)):
        err(path, f"skill '{name}' is unclassified — give it a tier")
    for name in sorted(set(tiers) - on_disk):
        err(path, f"skill '{name}' is classified but absent from skills/")

    prefix = render_dna_core.load_species(SPECIES)["prefix"]
    for skill in skills:
        meta = tiers.get(skill.parent.name)
        if not isinstance(meta, dict):
            continue
        tier = meta.get("tier")
        if tier not in VALID_TIERS:
            err(path, f"skill '{skill.parent.name}': tier must be one of {sorted(VALID_TIERS)}, got {tier!r}")
            continue
        body = skill.read_text(encoding="utf-8")
        if tier in render_dna_core.EXPORTABLE_TIERS:
            leaked = sorted({t for t in (str(prefix), SPECIES) if t in body})
            if leaked:
                err(skill, f"tier '{tier}' is exported to other species but references {leaked}")
        if tier != "deployment" and "UNSET" in body:
            err(skill, f"tier '{tier}' must be fully populated, but contains UNSET")
