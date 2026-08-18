#!/usr/bin/env python3
"""Render dna-core shared gene sources into a species' publishable agent kit.

The pre-PD-6 reuse mechanism named in docs/designs/web-store-dna.md § 8. The
shared genome lives once in `dna-core/genes/` as templates; each species
supplies its prefix, slug, and domain prose in `dna-core/species/<slug>.yaml`.

Default mode is --check: render in memory and diff against the published
genes. scripts/validate.py runs it, so dna-core cannot silently drift from
what is live on AgentForge.

`--export` scaffolds a new *species* — the shared genome with every slot blank.
`--instance` stamps a new *store* of this species — the same genome plus all the
species-owned content `--export` deliberately omits, re-slugged to the new
store's identity and complete enough to validate itself offline (NFR-7).

Run:
  python3 scripts/render_dna_core.py                    # drift check (exit 1 on drift)
  python3 scripts/render_dna_core.py --write            # write rendered genes
  python3 scripts/render_dna_core.py --export DIR --species-name my-species
  python3 scripts/render_dna_core.py --instance DIR --slug s --prefix p --env-prefix E
"""

from __future__ import annotations

import argparse
import difflib
import re
import shutil
import sys
from collections.abc import Callable
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any

import yaml
from kit_rules import (
    CAPABILITIES_SNAPSHOT,
    CREDENTIAL_FAILURE_TERMS,
)

ROOT = Path(__file__).resolve().parent.parent
CORE = ROOT / "dna-core"
GENES_DIR = CORE / "genes"
SPECIES_DIR = CORE / "species"
SKILLS_MANIFEST = CORE / "skills.yaml"
# What one store must supply to be stamped (TAP-5395). Carried into every
# instance so a stamped store can act as the template for the next one.
INTAKE_SCHEMA = CORE / "intake.schema.yaml"
INTAKE_DIR = CORE / "intake"
# Templates for the deployment-tier packs. These are the two files it is wrong
# to copy between stores: `store-atlas` names the hosts a gene may touch, so
# copying it verbatim hands a new store the previous store's domains.
PACKS_DIR = CORE / "packs"
# Which intake section fills which pack. The schema has exactly two sections
# because exactly two packs are populated per storefront (dna-core/skills.yaml).
PACK_SECTIONS = {"store-atlas": "storefront", "brand-voice-pack": "brand"}
SKILLS_DIR = ROOT / "skills"
# The Hydrogen app. One template serves every store: what differs per store is
# `brand.tokens.json` (generated from intake) and `pages.yaml` (narrowed to the
# page set the intake declares), so the components themselves are carried
# byte-for-byte and a stamped store never edits a component to look different.
FRONTEND_DIR = ROOT / "frontend"
# Never walked into: dependencies, build output, and generated router types.
# All are rebuilt by `npm install` + `npm run build` in the stamped repo.
#
# `guides` is upstream Hydrogen skeleton documentation — write-ups about the
# template's own search components, referenced by nothing in the app. It is
# reference material for whoever maintains the template, and that work happens
# in this repo, not in a stamped store. Excluded on those grounds; the fact that
# it also holds the tree's only binaries is a consequence, not the reason. A
# stamp that meets a binary it cannot carry fails loudly below rather than
# dropping it.
#
# `.shopify` is the Shopify CLI's per-checkout state. It names the shop, the
# linked Hydrogen storefront's GID, and the account email — none of which appear
# in any intake, so `revalue` cannot repoint them. Carried, it would bind every
# stamped store to store one's storefront: `hydrogen env pull` or `deploy` run in
# the new repo would target the wrong store, and the tree would ship someone's
# address. `test_stamped_frontend_is_all_git_tracked` enforces the general rule
# this entry is one instance of.
FRONTEND_PRUNE_DIRS = frozenset(
    {"node_modules", "dist", ".react-router", ".cache", ".shopify", "guides"}
)
# Present in a working tree, wrong in a stamp: a live deployment's URL and its
# auth-bypass token, and an incremental typecheck cache. `.env` is excluded by
# the same rule and would carry this store's Storefront credentials to the next.
FRONTEND_SKIP_NAMES = frozenset(
    {"h2_deploy_log.json", "tsconfig.tsbuildinfo", ".DS_Store"}
)
# Emitted per store further down rather than carried, so the carry loop must not
# also copy this store's copies over them.
FRONTEND_PER_STORE = frozenset({"brand.tokens.json", "pages.yaml"})

TMPL_SUFFIX = ".md.tmpl"
PLACEHOLDER = re.compile(r"\{\{([a-z0-9_]+)\}\}")
# Substituted in every template from the manifest's top level.
GLOBAL_KEYS = ("prefix", "slug", "env_prefix")
# What --export writes into every slot. Rendering must refuse to carry it into a
# published gene, or a new species ships the skeleton instead of its own content.
UNSET = "UNSET"
# Skill tiers a new species can take verbatim; see dna-core/skills.yaml.
EXPORTABLE_TIERS = ("core", "domain")
# The only tier allowed to ship UNSET into a stamped instance: these packs are
# populated per storefront, not per species, and the provisioning skill fills
# them from intake. Any other tier carrying UNSET means the instance would
# publish the skeleton, so instance stamping refuses it.
DEPLOYMENT_TIER = "deployment"
# The one tree where a bare UNSET means "this instance is unfinished", and so
# the only one `audit_unset` scans. Everywhere else the token appears in prose
# *about* the rule: `wstore-pull-tickets` explains what an UNSET atlas row means
# for its own behaviour, and the validator family documents the check it
# implements. Counting those would fail the stamp on its own machinery.
#
# Nothing is lost by the narrowing. This is where the tier contract already
# lives (`check_skill_tiers`); unfilled manifest slots fail closed in
# `render_all`; and species genes are copied verbatim from a tree the factory's
# own validator has already passed.
UNSET_AUDITED = "skills"
# The validator family a stamped repo must carry. `check_dna_core` imports these
# by module name, so a repo missing one cannot run its own validator — which is
# the entire content of NFR-7 (PRD Appendix B).
VALIDATOR_FAMILY = (
    "validate.py",
    "kit_rules.py",
    "kit_checks.py",
    "render_dna_core.py",
    # The --instance half, split out when this module crossed 1300 lines. Same
    # rule as brand_tokens.py below: omit it and a stamped repo cannot stamp the
    # next store, because its own render_dna_core imports this on --instance.
    "instance_stamp.py",
    "capabilities_snapshot.py",
    "sync_workflow_inputs.py",
    "input_source.py",
    "skill_pack.py",
    # Imported by this module to emit frontend/brand.tokens.json. Omitting it
    # left a stamped repo whose own validator died on ImportError — a stamp that
    # produces a repo failing its own validator is not a stamp (TAP-5389).
    "brand_tokens.py",
    # Emits PRODUCT.md / DESIGN.md bridges from intake (TAP-5600 / TAP-5605).
    "design_brief.py",
)
# Rule tests that travel with an export. A validator rule with no test can stop
# firing silently, which is the same false green in a different costume — so a
# species that inherits the rules inherits their tests too (TAP-5196).
EXPORT_TESTS = (
    "validate_helpers.py",
    "test_validate_grants.py",
    "test_validate_workflow.py",
    "test_validate_atlas.py",
    "test_validate_golden_cases.py",
    "test_validate_rubrics.py",
    "conftest.py",
)
# Repo-root files that name the store rather than the species. `.gitignore`
# is not in Appendix B's list but is emitted anyway: the provisioning skill
# asserts `.env` is ignored (FR-1), and a repo that has to add the file before
# it can assert that is one portal-fumble away from committing a store token.
INSTANCE_ROOT_FILES = (
    ".mcp.json",
    ".tapps-mcp.yaml",
    ".env.example",
    "AGENTS.md",
    ".gitignore",
)
# Appendix B entries this mode cannot emit yet. Printed on every stamp so a
# stamped repo's gaps are reported by the tool that made them, rather than
# found later by whoever tried to deploy it.
INSTANCE_PENDING: dict[str, str] = {}
# Docs a stamped store carries because its genes are wired to obey them. The
# memory-wiring convention is not reference material: the curator's group scope
# and the librarian's `hive_search` call are only auditable against the routing
# table it states, and a store that ships those genes without it has the
# behaviour and none of the reasoning.
INSTANCE_DOCS = ("docs/memory-wiring.md",)


@dataclass(frozen=True)
class Identity:
    """The three tokens that make kit content belong to one store."""

    prefix: str
    slug: str
    env_prefix: str

    @classmethod
    def of(cls, manifest: dict[str, object]) -> Identity:
        return cls(**{f.name: str(manifest[f.name]) for f in fields(cls)})


# Right-hand bound per identity token, and the whole subtlety of re-slugging.
# Each entry is (bound when substituting, bound when reporting residue):
#
#   prefix      a namespace prefix, always compounded (`wstore-rank`,
#               `wstore.act.product`). `-` and `.` are non-word characters, so
#               a plain `\b` is exactly what it means.
#   env_prefix  heads env var names joined by `_`, which *is* a word character,
#               so `\b` would never fire after it. "Not alphanumeric" catches
#               `WSTORE_TOKEN` and the manifest's bare `WSTORE` in one rule.
#   slug        a complete identifier, never the head of a longer one. It must
#               not be rewritten inside `docs/designs/web-store-dna.md`, which
#               is a document title and not this store — hence the extra
#               "not a hyphen or word character" when substituting.
#
# The two bounds differ only for the slug, and that difference is the design:
# substitution refuses to rewrite a compound identifier, and `residue` reports
# every one it refused. A carry-through is then a printed line rather than a
# stamped repo quietly still calling itself by the factory's name.
TOKEN_BOUNDS = {
    "prefix": (r"\b", r"\b"),
    "env_prefix": (r"(?![A-Za-z0-9])", r"(?![A-Za-z0-9])"),
    "slug": (r"\b(?![-\w])", r"\b"),
}


def reslug_pattern(src: Identity) -> re.Pattern[str]:
    """One alternation over all three tokens, longest first, so none shadows another.

    The ordering is load-bearing and the reason is not obvious. A stamped
    store's slug commonly *begins with* its own prefix, and Python alternation
    takes the first branch that matches at a position rather than the longest
    one. With the prefix listed first, such a slug matched the prefix branch and
    the slug branch became unreachable — so that store could only ever rename
    its slug to `<new prefix>` plus its old suffix, never to an arbitrary name.

    This kit is immune by accident: `wstore` is not a leading substring of
    `web-store`. That is the kind of luck that holds right up until the first
    store tries to stamp the second.

    Note that the examples in this file are written with this species' own
    tokens rather than invented ones. An invented name in a comment is a hazard
    here, because this file is itself stamped: a store that happened to choose
    that name would trip `occupied` for no reason.
    """
    ordered = sorted(TOKEN_BOUNDS, key=lambda name: -len(getattr(src, name)))
    return re.compile(
        "|".join(
            rf"(?P<{name}>\b{re.escape(getattr(src, name))}{TOKEN_BOUNDS[name][0]})"
            for name in ordered
        )
    )


def occupied(text: str, src: Identity, dst: Identity) -> list[str]:
    """Destination tokens this text already uses to mean something else.

    Re-slugging is a rename, and renaming onto a name the corpus already uses
    merges two meanings silently. `wstore-memory-curator` tells its judge that
    no written fact may contain "the customer's email address, name, or city";
    a store that took `city` as its prefix would stamp children whose redaction
    rubric protects two fields and its own name. The first stamp still reads
    correctly, so the corruption only appears a generation later — and the
    corrupted child passes `validate.py`. Refusing the identity up front is the
    only point where this is still cheap to see.

    Every source this scans matters: the check is worth nothing on the files it
    is not run against, which is exactly how the `city` case survived the first
    implementation (the rendered genes bypassed the only caller).
    """
    return [
        token
        for name, (bound, _) in TOKEN_BOUNDS.items()
        if (token := getattr(dst, name)) != getattr(src, name)
        and re.search(rf"\b{re.escape(token)}{bound}", text)
    ]


# Identity tokens become path segments (`agentforge/projects/<slug>/`,
# `policy/<slug>.rules.yaml`) and environment variable names, so their shape is a
# safety property rather than a style rule. Before this existed, `--slug
# ../../ESCAPED` wrote files outside the destination directory: the slug is
# joined into a relative path and that path was never normalised.
TOKEN_SHAPES = {
    "prefix": re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*"),
    "slug": re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*"),
    "env_prefix": re.compile(r"[A-Z][A-Z0-9]*"),
}


def malformed(identity: Identity) -> list[str]:
    """Tokens that are not safe to use as a path segment or an env var name."""
    return [
        f"{name}={getattr(identity, name)!r} is not of the form /{shape.pattern}/"
        for name, shape in TOKEN_SHAPES.items()
        if not shape.fullmatch(getattr(identity, name))
    ]


def leaks_into_exported_packs(dst: Identity, tiers: dict[str, dict[str, str]]) -> list[str]:
    """Tokens a stamped repo's own `check_skill_tiers` would reject.

    That check tests plain substring containment rather than word boundaries,
    because a `core`/`domain` pack has to stay free of species coupling in any
    spelling. `occupied` deliberately uses word boundaries — it asks what
    `reslug` would actually rewrite — so the two rules disagree, and the gap is
    not academic: short prefixes hide inside ordinary English words in these
    packs, and several plausible store names stamped clean and then failed their
    own `validate.py`, which is precisely the NFR-7 promise.

    Where they disagree the stricter rule wins. A stamp must never produce a
    repo that its own validator rejects, so this refuses what that check would.

    No examples are named here on purpose. This file is itself carried into
    every stamp and scanned by `occupied`, so a token quoted in this docstring
    becomes a permanently reserved prefix — the exact trap `reslug_pattern`
    warns about, and one this function's first draft fell into.
    """
    leaked: list[str] = []
    for name, meta in sorted(tiers.items()):
        if meta["tier"] not in EXPORTABLE_TIERS:
            continue
        body = (SKILLS_DIR / name / "SKILL.md").read_text(encoding="utf-8")
        leaked.extend(
            f"{token!r} appears inside skills/{name}/SKILL.md, a {meta['tier']}-tier pack"
            for token in (dst.prefix, dst.slug)
            if token in body
        )
    return leaked


def reads_as_credential_failure(dst: Identity) -> list[str]:
    """An env prefix that turns every mention of a credential into a failure claim.

    `check_no_prewritten_credential_failure` flags any line naming a required
    credential that also carries failure vocabulary, because a gene cannot
    observe that a credential is missing and will reach for a ready-made
    sentence when it has nothing else to report. It matches that vocabulary
    case-insensitively against the whole line — and the credential key is built
    from the env prefix.

    So an env prefix containing one of those terms makes the key its own failure
    term. Every ordinary sentence documenting the operator dependency then reads
    as an assertion that the credential failed, and two genes that are correct
    today start failing the stamped repo's own validator.

    This is the third instance of one pattern: a stamp-time gate and a
    validate-time rule matching the same text by different rules. The gate has
    to be at least as strict as every rule the stamped repo will run.
    """
    lowered = dst.env_prefix.lower()
    return [
        f"env_prefix {dst.env_prefix!r} contains the credential-failure term {term!r}"
        for term in CREDENTIAL_FAILURE_TERMS
        if term in lowered
    ]


def indistinct(identity: Identity) -> list[str]:
    """Tokens this identity uses for more than one role.

    Sorting the alternation longest-first stops a prefix shadowing a slug that
    begins with it, but says nothing about two tokens that are the *same*
    string: `sorted` leaves ties in declaration order, so a store whose slug
    equals its prefix silently loses the slug branch and can only ever stamp
    children whose slug equals their prefix too. There is no rewrite that could
    be correct for such an identity, so it is refused rather than ordered.
    """
    seen: dict[str, int] = {}
    for name in TOKEN_BOUNDS:
        seen[getattr(identity, name)] = seen.get(getattr(identity, name), 0) + 1
    return sorted(token for token, count in seen.items() if count > 1)


def reslug(text: str, src: Identity, dst: Identity) -> str:
    """Rewrite every identity token in `text` from one store's to another's."""
    if src == dst:
        return text
    return reslug_pattern(src).sub(lambda m: getattr(dst, str(m.lastgroup)), text)


def residue(text: str, src: Identity, dst: Identity) -> list[str]:
    """Source identity tokens still present after re-slugging (see TOKEN_BOUNDS).

    Reports the whole identifier the token is part of, so `web-store-dna` reads
    as one carry-through rather than as a bare slug the pattern missed. The
    trailing run stops at `[\\w-]` for the same reason: `\\S*` would swallow the
    surrounding punctuation and report one identifier three different ways.
    """
    found: list[str] = []
    for name, (_, report) in TOKEN_BOUNDS.items():
        token = getattr(src, name)
        if token == getattr(dst, name):
            continue
        found.extend(re.findall(rf"\b{re.escape(token)}{report}[\w-]*", text))
    return found


def _row(item: object, columns: list[str]) -> str:
    """One markdown table row. Every cell but the last is a value, so it is quoted."""
    if not isinstance(item, dict):
        raise KeyError(f"render shape 'rows' needs mappings, got {item!r}")
    cells = [str(item.get(column, UNSET)) for column in columns]
    quoted = [f"`{cell}`" for cell in cells[:-1]] + cells[-1:]
    return "| " + " | ".join(quoted) + " |"


def _as_inline(value: list, spec: dict[str, object]) -> str:
    return ", ".join(str(item) for item in value)


def _as_bullets(value: list, spec: dict[str, object]) -> str:
    return "\n".join(f"- {item}" for item in value)


def _as_numbered(value: list, spec: dict[str, object]) -> str:
    return "\n".join(f"{i}. `{item}`" for i, item in enumerate(value, 1))


def _as_rows(value: list, spec: dict[str, object]) -> str:
    declared = spec.get("columns")
    if not isinstance(declared, list):
        raise KeyError(f"render shape 'rows' needs a 'columns' list, got {declared!r}")
    return "\n".join(_row(item, [str(column) for column in declared]) for item in value)


def _as_map(value: dict, spec: dict[str, object]) -> str:
    return "\n".join(f"- **{key}** — {item}" for key, item in value.items())


def _as_groups(value: dict, spec: dict[str, object]) -> str:
    return "\n\n".join(
        f"**{key}**\n\n" + "\n".join(f"- {item}" for item in members)
        for key, members in value.items()
    )


# shape name -> (container the value must be, noun for the error, renderer).
# A table rather than an if/elif ladder because every entry is the same three
# facts, and the ladder had grown to the point where the type guard for one
# shape sat several branches away from the code it guarded.
SHAPES: dict[str, tuple[type, str, Callable[[Any, dict[str, object]], str]]] = {
    "inline": (list, "list", _as_inline),
    "bullets": (list, "list", _as_bullets),
    "numbered": (list, "list", _as_numbered),
    "rows": (list, "list", _as_rows),
    "map": (dict, "mapping", _as_map),
    "groups": (dict, "mapping", _as_groups),
}


def as_markdown(value: object, spec: dict[str, object]) -> str:
    """One intake value as the markdown its pack slot expects.

    `UNSET` renders as the literal the packs already use, because a gene reading
    it must see "no such target" (store-atlas rule 2) rather than a blank cell
    that looks like an oversight.

    The shape comes from the schema's `render` hint rather than from the value's
    Python type: the same `list` is three adjectives on one line in one slot and
    a bulleted block in another, and guessing from the type would silently pick
    the wrong one.
    """
    if value == UNSET or value is None:
        return f"`{UNSET}`"
    # Before the scalar branch: `str(True)` is `True`, and these render into a
    # document whose other machine-read values are YAML-cased.
    if isinstance(value, bool):
        return "true" if value else "false"
    shape = str(spec.get("render", "scalar"))
    if shape == "scalar":
        return str(value)
    if shape not in SHAPES:
        raise KeyError(f"unknown render shape {shape!r}")
    container, noun, render_shape = SHAPES[shape]
    if not isinstance(value, container):
        raise KeyError(f"render shape {shape!r} needs a {noun}, got {type(value).__name__}")
    return render_shape(value, spec)


def render(template: str, values: dict[str, str]) -> tuple[str, set[str]]:
    """Substitute every {{slot}}. Returns the text and the slots consumed."""
    used: set[str] = set()

    def substitute(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in values:
            raise KeyError(key)
        used.add(key)
        return values[key]

    return PLACEHOLDER.sub(substitute, template), used


def revaluation(source: dict[str, object], target: dict[str, object]) -> dict[str, str]:
    """Map one store's deployment values onto another's.

    Re-slugging fixes the *identity* tokens; this fixes the *deployment* values,
    and both are needed. The atlas is rendered from intake and so is always
    right, but genes and workflows carry the same hosts inline — a WebFetch
    grant names the storefront it may fetch, a workflow's `store` input defaults
    to the Admin host — and copying those verbatim left a stamped store pointing
    at the previous store's shop while its own atlas disagreed. The kit's own
    `check_storefront_probe_targets` and `check_workflow_store_matches_atlas`
    catch it, which is how it was found, but a stamp that produces a repo
    failing its own validator is not a stamp.

    Restricted to hostname and identifier fields: those are narrow, unambiguous
    tokens. Prose fields are deliberately excluded — substituting a brand
    sentence across a gene body is the kind of blunt rewrite that corrupts more
    than it fixes.
    """
    schema = yaml.safe_load(INTAKE_SCHEMA.read_text(encoding="utf-8"))
    mapping: dict[str, str] = {}
    for section in PACK_SECTIONS.values():
        before, after = source.get(section), target.get(section)
        if not isinstance(before, dict) or not isinstance(after, dict):
            continue
        for field, spec in schema[section].items():
            if spec.get("kind") not in ("hostname", "identifier"):
                continue
            old, new = before.get(field), after.get(field)
            if isinstance(old, str) and isinstance(new, str) and old != new and UNSET not in (old, new):
                mapping[old] = new
    return mapping


def revalue(text: str, mapping: dict[str, str]) -> str:
    """Apply a deployment-value map, longest key first so no host shadows another."""
    if not mapping:
        return text
    pattern = "|".join(re.escape(key) for key in sorted(mapping, key=len, reverse=True))
    return re.sub(pattern, lambda m: mapping[m.group(0)], text)


def load_intake(slug: str, path: Path | None = None) -> dict[str, object]:
    """One store's intake values, as declared by dna-core/intake.schema.yaml."""
    source = path or INTAKE_DIR / f"{slug}.yaml"
    if not source.exists():
        sys.exit(f"no intake for {slug}: expected {source}")
    return yaml.safe_load(source.read_text(encoding="utf-8"))


def pack_slots(intake: dict[str, object], section: str) -> dict[str, str]:
    """One intake section as the slot values its pack template reads.

    Scoped to a single section rather than flattened across both, so the
    unused-slot check stays meaningful: a pack that stops reading one of its own
    fields is a real error, while `store-atlas` not reading a brand field is not.

    Fields the schema marks `pack_slot: false` are excluded. They are intake
    facts consumed somewhere other than a pack — `storefront.pages` is read by
    `instance_pages_yaml` to narrow `frontend/pages.yaml` — and without the
    exclusion the unused-slot check reports them as pack defects, which refuses
    the stamp before the code that actually reads them ever runs.

    Section names are dropped from the slot names — a template says
    `{{brand_name}}`, not `{{brand.brand_name}}`.
    """
    schema = yaml.safe_load(INTAKE_SCHEMA.read_text(encoding="utf-8"))
    values = intake.get(section)
    if not isinstance(values, dict):
        sys.exit(f"intake has no '{section}' section")
    return {
        field: as_markdown(values.get(field), spec)
        for field, spec in schema[section].items()
        if spec.get("pack_slot", True)
    }


def unfilled_required(intake: dict[str, object]) -> list[str]:
    """Every `required: true` intake field that is absent or UNSET.

    The missing half of the tier rule. `check_skill_tiers` forbids UNSET above
    `deployment` tier and exempts deployment unconditionally — right for the
    factory, which has no storefront, and wrong for a stamped store. That is how
    a fully unfilled atlas validated clean: `atlas_hosts` skips UNSET rows, so
    the host set came back empty and every consumer of it returned early.

    Counting UNSET in a rendered pack cannot tell the two apart, because UNSET
    is a *correct* value for an optional field — a channel with no account yet
    is honestly UNSET, and inventing a placeholder turns a gene's refusal into a
    wrong publish target. Only the schema knows which is which.

    Lives here rather than in `kit_checks` so the stamp and the stamped repo's
    validator enforce one rule from one place. A stamp must never produce a repo
    its own validator rejects.
    """
    schema = yaml.safe_load(INTAKE_SCHEMA.read_text(encoding="utf-8")) or {}
    findings: list[str] = []
    for key, spec in schema.items():
        if not isinstance(spec, dict):
            continue
        # A field spec declares `kind`; a section is a mapping of field specs.
        fields = {key: spec} if "kind" in spec else spec
        values = intake if "kind" in spec else intake.get(key)
        if not isinstance(values, dict):
            findings.append(f"intake has no '{key}' section")
            continue
        label = "" if "kind" in spec else f"{key}."
        for field, fspec in fields.items():
            if not (isinstance(fspec, dict) and fspec.get("required")):
                continue
            if field not in values:
                findings.append(f"{label}{field} is required by the schema but absent")
            elif str(values[field]).strip() == UNSET:
                findings.append(f"{label}{field} is required by the schema but is UNSET")
    return findings


def pack_templates() -> list[Path]:
    return sorted(PACKS_DIR.glob(f"*{TMPL_SUFFIX}"))


def render_packs(intake: dict[str, object]) -> dict[Path, str]:
    """Render every deployment-tier pack for one store.

    The deployment packs are the two files that are wrong to copy between
    stores: `store-atlas` names the hosts a gene may touch, and copying it
    verbatim hands a new store the previous store's domains. Rendering them from
    intake is what makes `--instance` produce a store rather than a duplicate.
    """
    rendered: dict[Path, str] = {}
    problems: list[str] = []
    for template in pack_templates():
        name = template.name[: -len(TMPL_SUFFIX)]
        section = PACK_SECTIONS.get(name)
        if not section:
            problems.append(f"{template.name}: no intake section maps to this pack")
            continue
        slots = pack_slots(intake, section)
        try:
            text, used = render(template.read_text(encoding="utf-8"), slots)
        except KeyError as exc:
            problems.append(f"{template.name}: intake has no value for slot {{{{{exc.args[0]}}}}}")
            continue
        unused = sorted(set(slots) - used)
        if unused:
            problems.append(f"{template.name}: intake declares slot(s) the pack never uses: {unused}")
        rendered[SKILLS_DIR / name / "SKILL.md"] = text
    if problems:
        sys.exit("deployment pack render failed:\n  " + "\n  ".join(problems))
    return rendered


def load_species(name: str) -> dict[str, object]:
    path = SPECIES_DIR / f"{name}.yaml"
    if not path.exists():
        sys.exit(f"no species manifest: {path.relative_to(ROOT)}")
    data = yaml.safe_load(path.read_text())
    missing = [key for key in GLOBAL_KEYS if key not in data]
    if missing:
        sys.exit(f"{path.name}: missing required key(s) {missing}")
    return data


def gene_templates() -> list[Path]:
    templates = sorted(GENES_DIR.glob(f"*{TMPL_SUFFIX}"))
    if not templates:
        sys.exit(f"no gene templates in {GENES_DIR.relative_to(ROOT)}")
    return templates


def render_gene(template: Path, shared: dict[str, str], slots: dict[str, str]) -> tuple[str, list[str]]:
    """Render one gene. Returns (text, problems); text is empty when problems exist."""
    unfilled = sorted(name for name, value in slots.items() if str(value).strip() == UNSET)
    if unfilled:
        return "", [f"{template.name}: slot(s) still UNSET in the manifest: {unfilled}"]
    try:
        # Slot values may reference the globals themselves (a sibling gene name
        # is prose to the species but mechanical to the renderer).
        resolved = {name: render(value, shared)[0] for name, value in slots.items()}
        text, used = render(template.read_text(), {**shared, **resolved})
    except KeyError as exc:
        return "", [f"{template.name}: manifest has no value for slot {{{{{exc.args[0]}}}}}"]
    unused = sorted(set(slots) - used)
    if unused:
        return "", [f"{template.name}: manifest defines slot(s) the template never uses: {unused}"]
    return text, []


def render_all(species: dict[str, object]) -> dict[Path, str]:
    """Render every gene template. Fails closed on an unfilled, unresolved, or unused slot."""
    shared = {key: str(species[key]) for key in GLOBAL_KEYS}
    unset = sorted(key for key in GLOBAL_KEYS if shared[key].strip() == UNSET)
    if unset:
        sys.exit(f"species manifest has unfilled global(s): {unset}")
    out_dir = ROOT / "agentforge" / "projects" / shared["slug"] / "agents"
    per_gene: dict[str, dict[str, str]] = species.get("genes") or {}  # type: ignore[assignment]

    rendered: dict[Path, str] = {}
    problems: list[str] = []
    for template in gene_templates():
        gene = template.name[: -len(TMPL_SUFFIX)]
        text, issues = render_gene(template, shared, per_gene.get(gene) or {})
        problems.extend(issues)
        if not issues:
            rendered[out_dir / f"{shared['prefix']}-{gene}.md"] = text

    if problems:
        sys.exit("dna-core render failed:\n  " + "\n  ".join(problems))
    return rendered


def check(rendered: dict[Path, str]) -> int:
    drifted = 0
    for path, text in sorted(rendered.items()):
        rel = path.relative_to(ROOT)
        if not path.exists():
            print(f"MISSING  {rel}")
            drifted += 1
            continue
        published = path.read_text()
        if published != text:
            drifted += 1
            print(f"DRIFT    {rel}")
            print(
                "".join(
                    difflib.unified_diff(
                        published.splitlines(keepends=True),
                        text.splitlines(keepends=True),
                        fromfile=f"published/{path.name}",
                        tofile=f"rendered/{path.name}",
                    )
                )
            )
    if drifted:
        print(f"\n{drifted} gene(s) drifted from dna-core.")
        print("Reconcile the template or the species manifest, then --write once the diff is intended.")
        return 1
    print(f"dna-core OK - {len(rendered)} shared gene(s) render byte-identical to the published kit.")
    return 0


def write(rendered: dict[Path, str]) -> int:
    for path, text in sorted(rendered.items()):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        print(f"wrote {path.relative_to(ROOT)}")
    return 0


def manifest_skeleton(species_name: str) -> str:
    """Emit a manifest with every slot UNSET, so a new species sees what it owes."""
    lines = [
        f"# Species manifest for {species_name}, generated by render_dna_core.py --export.",
        "# Every UNSET is a decision this species must make; rendering fails while any remain.",
        "prefix: UNSET",
        f"slug: {species_name}",
        "env_prefix: UNSET",
        "genes:",
    ]
    for template in gene_templates():
        gene = template.name[: -len(TMPL_SUFFIX)]
        slots = sorted(set(PLACEHOLDER.findall(template.read_text())) - set(GLOBAL_KEYS))
        if not slots:
            lines.append(f"  {gene}: {{}}")
            continue
        lines.append(f"  {gene}:")
        lines.extend(f"    {slot}: UNSET" for slot in slots)
    return "\n".join(lines) + "\n"


def policy_skeleton(species_name: str) -> str:
    """A minimal, valid policy file for a new species.

    Carries exactly one rule rather than this genome's set. Capability names are
    species-specific, so copying ours would hand a new species denies that match
    nothing it has — which reads as protection and is not. But an empty `rules`
    list fails the very validator this export ships, so the skeleton has to be
    both non-empty and honestly inapplicable: one deny, on a capability the
    species is told to rename.
    """
    return (
        f"# Policy rules for {species_name}.\n"
        "#\n"
        "# One placeholder rule. It is deliberately NOT a copy of the exporting\n"
        "# genome's rules: capability names are species-specific, and a deny that\n"
        "# matches nothing reads as protection while providing none.\n"
        "#\n"
        "# Semantics worth knowing before you edit:\n"
        "#   * conditions AND together; an empty list matches anything\n"
        "#   * deny always wins, regardless of priority\n"
        "#   * nothing matching = ALLOW, so every restriction must be explicit\n"
        "#\n"
        "# And the part that is easy to miss: an authored rules file is a\n"
        "# SPECIFICATION until the runtime is proven to load and enforce it. Check\n"
        "# what your engine actually does before treating this as a control.\n"
        "rules:\n"
        f"  - rule_id: {species_name}-deny-placeholder\n"
        '    description: "Replace with a real capability for this species."\n'
        f'    capabilities: ["{species_name}.act.placeholder"]\n'
        "    decision: deny\n"
        "    priority: 100\n"
    )


def intake_skeleton(species_name: str) -> str:
    """A per-store intake for a fresh export, filled with replaceable examples.

    It cannot be a UNSET skeleton. `unfilled_required` (TAP-5395) refuses an
    intake whose required fields ship UNSET — deliberately, because a partially
    filled store is worse than none — and the publish gate reads
    `dna-core/intake/<slug>.yaml`, so an export with no intake fails on its first
    run. A skeleton would therefore make a fresh export fail its own gate either
    way, which is the defect this whole issue is about.

    So the export ships an intake that VALIDATES, labelled at the top as example
    data to replace. The colours are a neutral accessible pair rather than any
    brand's: `brand_tokens` enforces WCAG AA on the text pairs, so a placeholder
    palette has to be legible or the stamp refuses it.
    """
    return f"""# Intake for {species_name}, generated by --export.
#
# EVERY VALUE BELOW IS EXAMPLE DATA. Replace all of it before stamping a real
# store. It is filled rather than UNSET because an intake with unfilled required
# fields is refused outright (TAP-5395), so a blank skeleton would leave a fresh
# export unable to pass its own publish gate.
#
# The palette is a neutral accessible pair, not a brand's. The token projection
# enforces WCAG AA on the text-on-background pairs, so whatever you replace it
# with must stay legible or the stamp will refuse it.
slug: {species_name}
prefix: {species_name.split("-")[0]}
env_prefix: {species_name.split("-")[0].upper()}

storefront:
  store_slug: {species_name}
  platform: shopify
  primary_domain: example.com
  myshopify_domain: example.myshopify.com
  admin_host: example.myshopify.com
  head: hydrogen
  # Follows the head: Hydrogen proxies `/api/mcp` itself, so this is the
  # storefront origin and not the `.myshopify.com` one. `ucp_origin` does not
  # follow the head — Hydrogen proxies neither UCP path.
  agent_origin: example.com
  ucp_origin: example.myshopify.com
  status: draft
  plan_display_name: "REPLACE - the plan this store is actually on"
  partner_development: false
  payments_verified: false
  reviews_host: reviews.example.com

brand:
  brand_name: "REPLACE - the brand's name"
  what_we_sell: "REPLACE - one sentence naming what this store sells."
  customer: "REPLACE - one sentence describing who buys it."
  voice_adjectives:
    - REPLACE-adjective-one
    - REPLACE-adjective-two
    - REPLACE-adjective-three
  register: "REPLACE - how the brand writes; sentence length, contractions, formality."
  proof_points:
    - claim: "REPLACE - a claim this brand can actually support"
      source: "REPLACE - where that claim is evidenced"
  banned_phrases:
    company_wide:
      - REPLACE-a-phrase-this-brand-never-uses
  may_mention_competitors: false
  margin_floor: "REPLACE - a percentage or a currency amount, and say which"

tokens:
  bg_primary: '#101418'
  bg_surface: '#161b21'
  bg_elevated: '#1d242c'
  accent_primary: '#4f9cf0'
  accent_secondary: '#7ab6f5'
  text_primary: '#f2f5f8'
  text_secondary: '#9aa7b4'
  border: 'rgba(255,255,255,0.10)'
  error: '#ef4444'
  font_body: 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif'
"""


def export(dest: Path, species_name: str) -> int:
    """Scaffold a new species: shared genome, portable skills, manifest, toolchain.

    The toolchain is not a convenience. A 2026-07-29 export produced 15 files and
    then told the reader to render with `--write` — a command absent from the tree
    it had just created. The receiving project could neither render the genome nor
    gate a publish, and the publish gate carries the rules added because an
    unscoped host-reaching grant shipped three times in this repo (TAP-5196).

    An export therefore ships the same `VALIDATOR_FAMILY` an instance stamp does.
    One list, two consumers: a module added to the renderer cannot be remembered
    in one path and forgotten in the other.
    """
    if dest.exists() and any(dest.iterdir()):
        sys.exit(f"refusing to export into non-empty {dest}")
    tiers: dict[str, dict[str, str]] = yaml.safe_load(SKILLS_MANIFEST.read_text())["skills"]

    shutil.copytree(GENES_DIR, dest / "dna-core" / "genes")
    # Read by the renderer as a module-level constant, and a species that later
    # stamps stores needs the contract anyway.
    shutil.copy2(INTAKE_SCHEMA, dest / "dna-core" / "intake.schema.yaml")

    taken = [name for name, meta in sorted(tiers.items()) if meta["tier"] in EXPORTABLE_TIERS]
    for name in taken:
        shutil.copytree(SKILLS_DIR / name, dest / "skills" / name)

    # The manifest is FILTERED to what actually shipped, not copied verbatim. The
    # validator errors on a pack that is "classified but absent from skills/", so
    # a verbatim copy guaranteed a fresh export failed its own publish gate on the
    # four packs the export deliberately withholds.
    manifest_dest = dest / "dna-core" / "skills.yaml"
    manifest_dest.parent.mkdir(parents=True, exist_ok=True)
    manifest_dest.write_text(
        "# Reuse tiers for the packs this export shipped. The exporting kit's\n"
        "# species- and deployment-tier packs are withheld by design, so they are\n"
        "# absent here too — a pack classified but not present fails the gate.\n"
        + yaml.safe_dump({"skills": {name: tiers[name] for name in taken}}, sort_keys=False),
        encoding="utf-8",
    )

    scripts_dir = dest / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    for name in VALIDATOR_FAMILY:
        shutil.copy2(ROOT / "scripts" / name, scripts_dir / name)

    tests_dir = dest / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)
    for name in EXPORT_TESTS:
        shutil.copy2(ROOT / "tests" / name, tests_dir / name)

    policy = dest / "policy" / f"{species_name}.rules.yaml"
    policy.parent.mkdir(parents=True, exist_ok=True)
    policy.write_text(policy_skeleton(species_name), encoding="utf-8")

    intake = dest / "dna-core" / "intake" / f"{species_name}.yaml"
    intake.parent.mkdir(parents=True, exist_ok=True)
    intake.write_text(intake_skeleton(species_name), encoding="utf-8")

    shutil.copy2(ROOT / "pyproject.toml", dest / "pyproject.toml")

    # The platform capability snapshot describes AgentForge, not this genome, so
    # it is the same file for every species — and rendering reads it to check a
    # gene against what the platform accepts. Absolute, so the destination comes
    # from its position relative to the kit root rather than a direct join.
    snapshot_dest = dest / CAPABILITIES_SNAPSHOT.relative_to(ROOT)
    snapshot_dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(CAPABILITIES_SNAPSHOT, snapshot_dest)

    # `--write` resolves exactly one `<slug>/agents/` directory and exits when it
    # finds none. The manifest already carries the slug, so the export knows it;
    # without this the very next command the export prints cannot run.
    agents_dir = dest / "agentforge" / "projects" / species_name / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    (agents_dir / ".gitkeep").write_text("", encoding="utf-8")

    manifest = dest / "dna-core" / "species" / f"{species_name}.yaml"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(manifest_skeleton(species_name))

    skipped = sorted(set(tiers) - set(taken))
    print(f"exported {len(gene_templates())} gene template(s) and {len(taken)} skill pack(s): {', '.join(taken)}")
    print(f"not exported (species- or deployment-specific): {', '.join(skipped)}")
    print(f"toolchain: {len(VALIDATOR_FAMILY)} script(s), {len(EXPORT_TESTS)} test file(s), 1 policy skeleton")
    # `--species` is spelled out rather than left to its default. The default is
    # this factory's own slug, so an exported tree that omitted it would look for
    # a manifest belonging to a different species and exit — the printed
    # instruction has to be runnable exactly as printed.
    print(f"\nwrote {manifest.relative_to(dest)}. Next, in {dest}:")
    print(f"  1. fill every UNSET in dna-core/species/{species_name}.yaml")
    print(f"  2. python3 scripts/render_dna_core.py --species {species_name} --write")
    print("  3. python3 scripts/validate.py")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--species",
        default=None,
        help="manifest name (default: the single manifest in dna-core/species/)",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true", help="write rendered genes into the species agents dir")
    mode.add_argument("--export", metavar="DIR", help="scaffold a new species repo from the shared genome")
    mode.add_argument("--instance", metavar="DIR", help="stamp a complete instance repo for one store")
    mode.add_argument(
        "--write-packs",
        action="store_true",
        help="render the deployment-tier packs from this store's intake",
    )
    parser.add_argument("--species-name", help="slug for the exported species (required with --export)")
    parser.add_argument("--slug", help="destination store slug (required with --instance)")
    parser.add_argument("--prefix", help="destination gene prefix (required with --instance)")
    parser.add_argument("--env-prefix", help="destination env var prefix (required with --instance)")
    parser.add_argument("--values", metavar="FILE", help="slot values (default: this species' manifest)")
    parser.add_argument("--intake", metavar="FILE", help="store intake (default: dna-core/intake/<slug>.yaml)")
    args = parser.parse_args()

    if args.export:
        if not args.species_name:
            parser.error("--export requires --species-name")
        return export(Path(args.export), args.species_name)

    if args.species is None:
        # Mirror kit_rules._discover_species: a forked/stamped kit carries exactly one
        # species manifest; pinning a default name here is what would stop the fork
        # from running its own renderer (NFR-7).
        manifests = sorted(p.stem for p in SPECIES_DIR.glob("*.yaml"))
        if len(manifests) != 1:
            raise SystemExit(
                f"--species required: found {len(manifests)} manifest(s) in {SPECIES_DIR} "
                f"({', '.join(manifests) or 'none'})"
            )
        args.species = manifests[0]
    source = load_species(args.species)
    if args.write_packs:
        return write(render_packs(load_intake(str(source["slug"]))))
    if args.instance:
        given = (("--slug", args.slug), ("--prefix", args.prefix), ("--env-prefix", args.env_prefix))
        blank = [flag for flag, value in given if not value]
        if blank:
            parser.error(f"--instance requires {', '.join(blank)}")
        # Imported here, not at module scope: instance_stamp imports this module
        # for the identity and rendering primitives, so a top-level import either
        # way round is a cycle. The stamp is one CLI mode out of four, so paying
        # for it only when asked is also the cheaper arrangement.
        import instance_stamp

        return instance_stamp.instance(
            Path(args.instance),
            Identity.of(source),
            Identity(prefix=args.prefix, slug=args.slug, env_prefix=args.env_prefix),
            Path(args.values) if args.values else SPECIES_DIR / f"{args.species}.yaml",
            Path(args.intake) if args.intake else None,
        )

    rendered = render_all(source)
    return write(rendered) if args.write else check(rendered)


if __name__ == "__main__":
    # Re-enter through this module's real name rather than calling the local
    # `main()`. Running the file as a script binds it as `__main__`, and
    # `instance_stamp` imports it as `render_dna_core` — two module objects, two
    # `Identity` classes. `Identity` is a dataclass, so its `__eq__` returns
    # NotImplemented across class objects and falls back to identity, which made
    # `instance_values` refuse every stamp with a message showing two identities
    # that print the same. Importing here means the `main()` that runs and the
    # one `instance_stamp` sees agree on the class.
    from render_dna_core import main as _main

    sys.exit(_main())
