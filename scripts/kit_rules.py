"""Platform-contract constants for the web-store kit validator.

Near-pure data. Most sets here mirror a closed union the AgentForge loader
enforces at publish time — a value outside one of them fails the `PUT` with a
422, so keeping them here turns a round-trip against a live instance into a
local error.

The workflow node vocabulary is the exception, and the reason is instructive:
it used to be a hand-copy of `NodeSpec.kind` from `backend/workflows/models.py`,
an *internal* AF module this repo neither imports nor tracks, and it drifted
twice. AF publishes the same facts at `GET /capabilities/manifest`, so those
values are now read from a committed snapshot of that response
(`agentforge/capabilities-manifest.json`, refreshed by
`scripts/capabilities_snapshot.py`). Reading a file is still offline and still
deterministic; it is just no longer a claim about another repo's source.

Split out of `validate.py` so the contract can be read (and diffed against
the platform) without wading through the checks that consume it.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _discover_species(root: Path) -> str:
    """The slug this kit publishes, read from the repo rather than pinned to one.

    A stamped instance repo carries exactly one project directory, named for its
    own slug. Pinning `web-store` here is precisely what would stop such a repo
    from running its own validator — which NFR-7 requires it to do offline, with
    no reference back to the factory repo.

    Ambiguity is fatal rather than guessed at: two project directories mean the
    caller knows something about intent that this module does not.
    """
    projects = root / "agentforge" / "projects"
    found = (
        sorted(p.name for p in projects.iterdir() if (p / "agents").is_dir())
        if projects.is_dir()
        else []
    )
    if len(found) == 1:
        return found[0]
    if not found:
        raise SystemExit(
            f"no publishable project under {projects}: "
            "expected exactly one <slug>/agents/ directory"
        )
    raise SystemExit(
        f"{len(found)} project directories under {projects} ({', '.join(found)}) "
        "— a kit publishes exactly one"
    )


SPECIES = _discover_species(ROOT)
AGENTS_DIR = ROOT / "agentforge" / "projects" / SPECIES / "agents"
WORKFLOWS_DIR = ROOT / "agentforge" / "projects" / SPECIES / "workflows"
SKILLS_DIR = ROOT / "skills"
POLICY_DIR = ROOT / "policy"
CORE_DIR = ROOT / "dna-core"
# Committed copy of `GET /capabilities/manifest`. See the module docstring.
CAPABILITIES_SNAPSHOT = ROOT / "agentforge" / "capabilities-manifest.json"
# Committed measurement of the catalog heroes' C2PA state, written by
# `scripts/provenance_snapshot.py` and carried into a workflow input.
PROVENANCE_SNAPSHOT = ROOT / "data" / "provenance-snapshot.json"

HYPHEN_KEYS = {
    "allowed-tools",
    "mcp-servers",
    "memory-profile",
    "risk-level",
    "share-scope",
    "tool-targets",
    "agent-type",
    "schema-version",
    "max-budget-usd",
    "failure-mode",
    "brain-profile",
    "golden-cases",
    "output-schema",
    "completion-criteria",
}
AGENT_REQUIRED = {"name", "description", "schema_version", "brain_rationale"}
VALID_DECISIONS = {"allow", "deny", "require_approval", "mask"}
VALID_ASSERTION_KINDS = {"tool_sequence", "output_schema_valid", "guardrails_clean", "rubric"}
# `skills/passk-eval/SKILL.md:25` — judgment gates run 5 trials at threshold 1.0,
# "no exceptions". A judge that fails one time in five is not a gate. Producer and
# gateway genes legitimately sit at 3; copying that number onto a judge is the
# specific mistake `check_golden_cases` now refuses.
JUDGE_TRIALS = 5
JUDGE_PASS_THRESHOLD = 1.0
# Mirror of AgentForge's `normalize_model_family` (backend/models/agent_config.py:529)
# so a same-family rubric is caught here, before the publish. AF refuses one at
# `PUT` with a 422 — but only when `require_cross_family` is set, and only after
# the round trip. Probed against 4.59.1 on 2026-08-07.
MODEL_ALIASES = {
    "claude-opus-4-8": "opus",
    "claude-opus-4-7": "opus",
    "claude-opus-4-6": "opus",
    "claude-sonnet-4-6": "sonnet",
    "claude-haiku-4-5-20251001": "haiku",
    "claude-3-5-sonnet-latest": "sonnet",
    "claude-3-5-haiku-latest": "haiku",
}
# The alias table is a fixed seven entries, NOT a general collapse of Anthropic
# ids — anything absent from it is lower-cased as-is and therefore reads as a
# different family from its own. Probed 2026-08-07 against AF 4.59.1 with an
# agent on `model: sonnet`: `judge_model: claude-sonnet-4-6` is refused 422 as
# same-family, while `claude-sonnet-4-5`, `claude-3-7-sonnet-latest` and
# `sonnet-4-6` all PASS `require_cross_family` while self-family grading. So a
# judge is declared by short alias here, and nothing else.
JUDGE_MODEL_ALIASES = {"opus", "sonnet", "haiku"}
# A rubric is a criterion, not a general quality bar, and an unscoped judge reads
# it as the latter. Measured 2026-08-07 on
# `wstore-judge-disclosure::grounds-verdict-in-supplied-matrix`: the opus judge's
# own rationale said the deduction "does not violate the criterion" and it
# deducted anyway, five trials running, landing 0.83-0.89 against a 0.90 bar. A
# fail carrying no information about the criterion is the same false signal as a
# pass carrying none, and the only other way out of it is lowering the bar.
#
# So every rubric closes by naming its own scope. The clause is a fixed string
# rather than a family of phrasings because `check_rubric_scope` compares against
# it exactly — a rubric that drifts to its own wording stops being checkable.
RUBRIC_SCOPE_CLAUSE = (
    "Score only the properties this criterion names; a defect in anything else "
    "is outside this criterion and is not grounds for a deduction."
)
# A behaviour case is worth 3 trials or it is worth very little — the argument
# `skills/passk-eval/SKILL.md` opens with. `check_golden_cases` enforced the
# trial count only for `role: judge`, so five rubric-carrying cases shipped at
# k=1 and nothing caught it.
BEHAVIOUR_TRIALS = 3
# `skills/passk-eval/SKILL.md` rule 1 — a gene ships at least three golden cases:
# one shape case and at least two behaviour cases, one of which is a trap. Nothing
# enforced the *composition* until now, only per-case shape, which is how 23 of 30
# genes drifted below it and two (`wstore-rank`, `wstore-summarize`) ended up
# shipping a single shape case and no behavioural assertion at all.
#
# Landing the rule as a flat error would fail the kit on those 23 and block every
# publish behind fleet-wide case authoring. So it lands as a ratchet: this table
# freezes each non-compliant gene's counts as measured on 2026-08-07, and
# `check_rule1_composition` errors when a gene drops below its own entry or when a
# gene outside the table misses rule 1. New and edited genes are held to the rule
# immediately; the listed ones may only improve.
#
# Entries are `(total_cases, shape_cases, behaviour_cases)`. A gene that reaches
# full compliance must have its entry deleted — a stale exemption is the same lie
# as a stale `shape_only_because`, so the check refuses one.
#
# Keys are the gene's role with the species prefix stripped — `rank`, not
# `wstore-rank`. This table is copied into every stamped store and re-slugged with
# it, so an identity token in a key would miss on the renamed gene: a fresh
# `bistro-ops` export would hold `bistro-rank` to the full rule and fail its own
# publish gate on debt it inherited unchanged. Same failure shape as
# `check_fleet_group_is_reslug_immune` guards against, caught by
# `test_a_fresh_export_renders_and_passes_its_own_publish_gate`.
RULE1_MIN_TOTAL = 3
RULE1_MIN_SHAPE = 1
RULE1_MIN_BEHAVIOUR = 2
RULE1_BASELINE = {
    # homeiq agents that don't meet rule 1 (at least 3 cases: 1 shape, 2 behaviour)
    # are baselined at their current counts. Entry format: (total, shape, behaviour)
    # Held at 2026-08-17 counts; may improve but cannot regress without explicit removal.
    "classify": (2, 1, 1),  # 1 shape, 1 behaviour (need 2 behaviour)
    "correlate": (1, 0, 1),  # 1 behaviour case only (need 1 shape, 2 behaviour)
    "extract": (2, 1, 1),  # 1 shape, 1 behaviour (need 2 behaviour)
    "kb-librarian": (2, 1, 1),  # 1 shape, 1 behaviour (need 2 behaviour)
    "memory-curator": (3, 0, 3),  # 3 behaviour cases, no shape case (need 1 shape)
    "notify": (3, 0, 3),  # 3 behaviour cases, no shape case (need 1 shape)
}
# The six seeded traps `skills/passk-eval/SKILL.md` requires every phase to carry.
# A case names the one it covers with `trap_for:`, which is repo-local in the same
# way `shape_only_because` is — AF's `GoldenCase` ignores unknown keys (probed
# 2026-08-07, `PUT` returned 201 with the key present), so it costs nothing on the
# wire. Validated when declared; no case declares one yet, so rule 1's trap clause
# is reported as an open gap rather than ratcheted — there is no trap count to
# protect from regression until the first one is authored.
TRAP_IDS = {
    "injection-payload",
    "unsourced-claim",
    "unauthorized-commitment",
    "fabricated-testimonial",
    "consentless-recipient",
    "over-cap-refund",
}
# A gene holding this capability fetches the storefront itself, so its WebFetch
# targets must track the store-atlas `primary_domain`. Platform-API genes hold
# hosts that are legitimately absent from the atlas — see check_storefront_probe_targets.
STOREFRONT_INGEST_CAPABILITY = "wstore.ingest.storefront"
# The discriminator for "this gene talks to the Shopify Admin API", and so for
# "this gene must be told which store". Deliberately the credential and not the
# `*.myshopify.com` egress host: `wstore-probe-storefront` holds a myshopify host
# too, but it is the shopper-facing `primary_domain`, and handing it the Admin
# `myshopify_domain` is precisely the confusion the atlas warns "fails in a way
# that looks like a credential problem". The credential separates the two exactly;
# the hostname pattern does not.
SHOPIFY_ADMIN_CREDENTIAL = "WSTORE_SHOPIFY_ADMIN_TOKEN"
# The input an Admin-API gene reads its target host from.
STORE_INPUT = "store"
# TAP-5368. AF auto-merges a declared credential into a Shape A `http_fetch`
# request when the model omits auth headers, and the default pattern is
# `Authorization: Bearer`. That default is silently wrong for any API that
# authenticates on a custom header, and the symptom — a plain 401 — is
# indistinguishable from a dead token, a missing vault entry, or the structural
# gap this repo spent a day proving. AF ships the coherence check for this as a
# *warning* (TAP-5372); locally it is an error, because we know the exact header
# each of these APIs wants and a warning is what let the last credential defect
# ship green.
#
# Maps credential key -> the header that API authenticates on. A key absent from
# this map takes AF's Bearer default, which is correct for Stripe and GA4.
CREDENTIAL_AUTH_HEADERS = {
    "WSTORE_SHOPIFY_ADMIN_TOKEN": "X-Shopify-Access-Token",
}
# The `inject` pattern that carries a custom header. AF's closed union is
# bearer/basic/header/query/env (backend/models/agent_config.py CredentialRef).
INJECT_HEADER = "header"
# Vocabulary that turns a mention of a credential key into a claim that it failed.
# A gene's body may name its credential freely — `wstore-pull-orders` documents its
# operator dependency, and should. What it must not carry is a ready-made sentence
# asserting the credential is *missing*, because the gene has no way to check that
# (credentials are injected at the tool layer, never in prompt context) and will
# reach for the sentence when it has nothing else to report. See
# check_no_prewritten_credential_failure.
CREDENTIAL_FAILURE_TERMS = ("not vaulted", "not available", "unavailable", "invalid", "missing")
# What turns that claim back into a report. A gene told "if the API answers 401,
# say the credential is not accessible" is doing exactly the right thing — the
# claim is gated on something it actually observed. `wstore-upsert-product` had
# this shape already and the first draft of the rule flagged it, which was the
# rule being wrong rather than the gene.
OBSERVED_FAILURE_MARKERS = ("401", "403")

# Facts a chromosome must carry inline, because genes have no filesystem and
# `AF_EXTERNAL_SKILLS_ROOT` is unset (see docs/phase-b-plan.md § 4a). Maps
# workflow name -> {input name: (source kind, reference)}.
#
# The content lives in the workflow's input `default` rather than as a required
# input because these chromosomes are scheduled and a scheduled fire passes no
# inputs at all. That duplicates a fact something else owns, which is only safe
# while something keeps the copy honest — `check_workflow_generated_defaults`
# does, and `scripts/sync_workflow_inputs.py` regenerates them.
#
# Two source kinds, deliberately not one:
#
#   SKILL_PACK — `skills/<ref>/SKILL.md`, rendered through `skill_pack.py` so the
#                pack's version and expiry travel with its body.
#   ARTIFACT   — a committed file at repo-relative `<ref>`, carried verbatim.
#
# The mapping stays explicit. A gene silently acquiring an input because a
# filename matched is how the unreadable-skill class of defect got in.
SKILL_PACK = "skill_pack"
ARTIFACT = "artifact"
WORKFLOW_INPUT_SOURCES: dict[str, dict[str, tuple[str, str]]] = {
    "cx-inbox": {
        "taxonomy": (SKILL_PACK, "taxonomies"),
        "cx_guardrails": (SKILL_PACK, "cx-guardrails"),
    },
    "store-health": {"kpi_truth": (SKILL_PACK, "kpi-truth")},
    "store-health-fixture": {"kpi_truth": (SKILL_PACK, "kpi-truth")},
    "listing-pipeline": {
        "disclosure_matrix": (SKILL_PACK, "ai-disclosure-matrix"),
        # The measured C2PA state of the 13 catalog heroes. The judge is asked
        # about provenance and, until this existed, given nothing to answer with —
        # so it answered "unverified" and blocked the two channels whose disclosure
        # *mechanism* is embedded provenance, permanently and for a reason no
        # verdict could resolve. Regenerated by scripts/provenance_snapshot.py.
        "provenance": (ARTIFACT, "data/provenance-snapshot.json"),
        # TAP-5667. `wstore-upsert-product` refuses any store absent from the
        # atlas, and with no filesystem it cannot read the pack — so it searched
        # for it instead and spent its whole budget cap before the first Admin
        # call. Registering it here is what makes the copy in the workflow a
        # generated artifact rather than a second hand-maintained source: the
        # atlas is itself rendered from an intake, so an unguarded inline copy
        # would go stale two hops from where anyone was looking.
        "store_atlas": (SKILL_PACK, "store-atlas"),
    },
    # Same judge, same pack, and it was missed when `listing-pipeline` was fixed:
    # `content-calendar`'s `disclosure` node passed `assets` and `channels` with no
    # `matrix`, so every scheduled fire reproduced the run-1 failure measured in
    # docs/phase-b-plan.md § 4a — `matrix_version: unknown`, all four channels
    # blocked identically, $0.216 against $0.074 with the pack supplied.
    #
    # No provenance input here on purpose: this chromosome drafts text only
    # (`wstore-draft-post` holds `allowed_tools: ''` and no schema carries a media
    # field), so there is no asset to have provenance. Handing it a snapshot of
    # someone else's images would invite exactly the guess this work removes.
    "content-calendar": {"disclosure_matrix": (SKILL_PACK, "ai-disclosure-matrix")},
}
# Reuse tiers for skill packs — see dna-core/skills.yaml for what each one means.
VALID_TIERS = {"core", "domain", "species", "deployment"}
# Closed discriminated union in backend/models/agent_config.py — a `type` outside
# this set fails the publish PUT with a 422 union_tag_invalid. Conceptual names
# from the design doc (e.g. "anti-secret") must be expressed as `extension`.
VALID_GUARDRAILS = {
    "anti-mimicry": "target",
    "anti-identity": "identities",
    "anti-pii": "pii_types",
    "non-authoritative": "domains",
    "extension": "text",
}
# Mirrors the validator sets in backend/models/agent_config.py. A value outside
# these fails the publish PUT with a 422 — catching it here turns a round-trip
# against a live platform into a local error.
VALID_ENUMS: dict[str, set[str]] = {
    "category": {"", "data", "expert", "general", "integration", "utility"},
    "role": {"", "aggregator", "gateway", "judge", "planner", "producer", "router"},
    "risk_level": {"high", "low", "medium", "trusted"},
    "memory_profile": {"full", "none", "readonly"},
    "brain_profile": {"agent_brain", "coder", "full", "reviewer"},
    "failure_mode": {"", "best_effort", "required"},
    "agent_type": {"", "expert", "task", "workflow"},
    # Waives only role_escape content-safety rejects at invoke, so a quarantine
    # gene can receive the payload it exists to judge (AF agent_config.py:1112).
    "content_safety": {"", "allow_role_escape"},
}
# `share_scope` is the one memory field that is NOT a closed set, which is why
# it is not in VALID_ENUMS above. The platform accepts three builtins plus a
# dynamic `group:<name>` (AF `agent_config.py:201-202`, validated by
# `_SHARE_SCOPE_GROUP_PATTERN` at `agent_config.py:1081-1092`). Mirroring only
# the builtins here made this validator *stricter than the platform*: it
# rejected `group:nlt-store-fleet` — a value publish accepts — and so blocked the
# fleet-memory wiring AD-4 depends on. Verified against the producer's
# validator, not the design doc, on 2026-08-01.
SHARE_SCOPE_BUILTIN = frozenset({"domain", "hive", "private"})
SHARE_SCOPE_GROUP = re.compile(r"^group:[a-z0-9][a-z0-9-]{0,63}$")
# The one hive group this species' writer genes join, created and populated by
# the provisioning skill's step 6 (`wstore-new-store/provision.py:431-450`).
# A gene that declares `group:<anything-else>` is never a member of it, and
# brain then either refuses the write outright (REST save, HTTP 400) or keeps
# it private with only a warning (propagation path) — the fleet pool never
# receives it either way. Naming the group in one place is what lets the
# validator catch that statically.
#
# The name deliberately carries NO identity token, and that is load-bearing
# rather than cosmetic. This file is itself carried and re-slugged into every
# stamped store, so a group named with this store's prefix (`<prefix>-fleet`,
# the name AD-4 and FR-6 propose) is rewritten per store: store `rank` joins
# `rank-fleet`, store `city` joins `city-fleet`, and the shared pool the whole
# design exists to fill never receives a cross-store row. Nothing reports it —
# brain keeps a non-member write local with a warning, and the stamped
# validator re-slugs this constant too, so it agrees with the broken genes.
# A fleet-wide constant must survive re-slugging; FLEET_GROUP_IS_RESLUG_IMMUNE
# in kit_checks enforces that rather than trusting this comment.
FLEET_HIVE_GROUP = "nlt-store-fleet"
# A grant that reaches a host needs an allowlist. Bash without one is refused by
# the AF loader; WebFetch without one spawns a targetless grant the model cannot
# act on — it narrates its own role instead of fetching, which is how adspend,
# social, and pull-tickets each shipped a gene that reported `complete` while
# ingesting nothing. WebSearch is deliberately absent: an open-web query is the
# instrument itself, not a target that can be enumerated.
#
# TAP-5333 / TAP-5334. `http_fetch` is deliberately NOT here. It was added on
# 2026-07-30 when the credential migration renamed the grant and moved the two
# store-credentialed genes out of the only rule requiring a host allowlist —
# but requiring `tool_targets.http_fetch` was the wrong fix. AF 4.56.2 rejects
# that key outright ("tool_targets has no expansion path for 'http_fetch'"), so
# the rule as written demanded a field the platform refuses. `http_fetch` is
# Shape A and its egress guard is `runtime_deps.http_allowlist`, enforced by
# HTTP_FETCH_GRANT below.
TARGETED_TOOLS = ("Bash", "WebFetch")
# AF Shape A (ADR-013/016). Its allowlist lives in `runtime_deps.http_allowlist`
# and nowhere else: `tool_targets` is never consulted for it, an empty list is
# deny-all that silently skips the wire-up, and entries must be bare hostnames —
# a scheme, path, port, or whitespace fails AF's `validate_http_allowlist`.
# This mirrors AF coherence Rule 5 so the kit fails locally rather than at
# publish, and it is the only egress bound the two Shopify Admin genes have.
HTTP_FETCH_GRANT = "http_fetch"
HTTP_ALLOWLIST_FORBIDDEN_CHARS = "/:@ \t\n"
# The platform's own answer, not our recollection of it. Probed live against
# 4.57.1 on 2026-07-31 and then deleted (both DELETE -> 204): a workflow PUT
# carrying `kind: script` returned 201, and so did one carrying `kind: sql` with
# an unregistered `source`. So publish validation is **schema-only** — it checks
# the kind is in the union and nothing further — and the hand-maintained set was
# wrong in both directions at once: it omitted `sql` entirely, and it rejected
# `script` with a fabricated "publish would 422".
try:
    _SNAPSHOT = json.loads(CAPABILITIES_SNAPSHOT.read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError) as _exc:  # pragma: no cover - bootstrap only
    # The snapshot is committed, so on any real checkout this file is present and
    # this branch is unreachable. It exists for the one case that is not a
    # checkout — the first run in a tree that has never fetched it — where a bare
    # FileNotFoundError traceback names the wrong problem.
    raise SystemExit(
        f"capabilities snapshot unusable at {CAPABILITIES_SNAPSHOT}: {_exc}\n"
        "  refresh it with: make af-capabilities   (needs a reachable AGENTFORGE_URL)"
    ) from _exc
# The AF release the snapshot was taken from. Quoted in validator messages so a
# rejection says which platform version disagreed, rather than asserting a
# timeless truth about a moving target.
AF_VERSION = _SNAPSHOT["af_version"]
VALID_NODE_KINDS = set(_SNAPSHOT["manifest"]["workflow"]["node_kinds"])
# `kind: script` dispatches to a plugin-registered handler by id. Publish does
# **not** check the id — a consumer-invented one fails at execution, not at PUT —
# so this is the axis that actually needs a local guard. Note the registered id
# is `external-job-relay` (hyphens); the AF-side filename `external_job_relay.py`
# uses underscores, and copying the filename is the obvious way to get this wrong.
VALID_SCRIPT_IDS = set(_SNAPSHOT["manifest"]["workflow"]["script_ids"])
SCRIPT_KIND = "script"
SCRIPT_ID_FIELD = "script_id"
# `python` resolves only `backend.*` callables, so a Pattern A consumer — which
# ships no code into the AF image — has nothing it can name there. That is a
# reachability fact about this deployment shape, not a schema fact, which is why
# it stays a local constant while the kinds themselves come from the manifest.
PATTERN_A_UNAVAILABLE_KINDS = {"python"}
# The quarantine gate's capability, and the wildcard that is its privilege
# alone. A scanner that cannot see everything cannot scan; every other consumer
# reading the wildcard reads *around* the verdict, which is how `correlate`
# received a payload `scan` had already blocked.
QUARANTINE_CAPABILITY = "wstore.judge.quarantine"
WILDCARD_INPUT = "$all_outputs"
# The one field a node downstream of the gate may read off a judged source
# directly, rather than through the gate.
#
# The gate judges `items` — attacker-reachable bodies. `sources_unavailable` is
# the ingest gene's report on its own connectivity: `array<string>`, authored by
# the gene rather than by anyone who can leave a review, and never carrying item
# text. Reading it around the gate leaks nothing the gate was protecting.
#
# It is an allowlist of exactly one field, and it stays that way. The reason it
# exists at all is that the Phase 5 soak metric must not be relayed through the
# scanner: `scan` is the gene that narrated instead of scanning on 71
# consecutive runs (D2) while every node reported `complete`. A degradation
# number laundered through that gene is the 91.5% again with extra steps, so
# `availability` reads the ingest nodes at the source and stays deterministic.
# Anything else — `$fetch`, `$fetch.items` — is still a hard error.
GATE_TRANSPARENT_FIELDS = frozenset({"sources_unavailable"})
# Vocabulary that shows a write-capable gene knows which envelope it is
# handling. wstore-memory-curator shipped with none of it — full write, domain
# share scope, and no concept of untrusted input — so an attacker-authored
# review could have reached shared memory and been recalled as trusted context
# by every later run of every chromosome.
TRUST_ENVELOPE_TERMS = ("trust", "quarantine", "safe_items", "safe_payload", "blocked", "untrusted")
# Tokens the input resolver handles before it looks for a node or a workflow
# input. None of them name a node, so a ref check must skip them.
RESERVED_INPUT_REFS = frozenset(
    {"all_outputs", "upstream_outputs", "iteration_index", "loop_transcript", "run_id"}
)
