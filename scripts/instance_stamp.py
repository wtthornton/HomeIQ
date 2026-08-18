"""Stamp a complete, self-validating instance repo for one store (FR-2).

Split out of `render_dna_core.py`, which had grown to 1348 lines around two
genuinely different jobs. That module renders the *species* genome — the shared
genes every store of this species inherits. This one stamps a *store*: the same
genome plus the species-owned content, re-slugged to a new identity and complete
enough to validate itself offline (NFR-7).

The seam is not cosmetic. Species rendering is a pure template fill; stamping is
a file-tree transform with a collision scan, a refusal ladder, and a contract to
emit a repo that passes its own validator. Keeping them in one file put a CC=24
function next to the template renderer and pushed the whole module under the
quality gate.

## Import direction

This module imports `render_dna_core`, never the reverse at module scope —
`render_dna_core.main` defers its import of this module into the function body
to break the cycle. Attribute access (`core.reslug`) rather than
`from render_dna_core import reslug` is the house style here; `kit_checks.py`
does the same, and it keeps the one-directional dependency visible at every
call site.

## Why this module must be in VALIDATOR_FAMILY

A stamped repo carries its own validator, and `check_dna_core` imports that
family by module name. A module omitted from the family stamps a repo whose own
validator dies on ImportError — a stamp that produces a repo failing its own
validator is not a stamp. That exact defect already happened once with
`brand_tokens.py` (TAP-5389), which is why the constant carries a comment saying
so. This module is registered there for the same reason.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import brand_tokens
import design_brief
import render_dna_core as core
import yaml
from kit_rules import (
    ARTIFACT,
    CAPABILITIES_SNAPSHOT,
    POLICY_DIR,
    SKILLS_DIR,
    WORKFLOW_INPUT_SOURCES,
)

# `FRONTEND_DIR` is render_dna_core's, not kit_rules'.
FRONTEND_DIR = core.FRONTEND_DIR


def inlined_artifacts() -> set[str]:
    """Committed files a chromosome carries inline, per the kit's own contract.

    A stamped repo whose workflows inline an artifact it does not carry fails
    its first `validate.py` on a regenerated default that cannot be recomputed.
    """
    return {
        ref
        for sources in WORKFLOW_INPUT_SOURCES.values()
        for kind, ref in sources.values()
        if kind == ARTIFACT
    }


def instance_values(
    path: Path, src: core.Identity, dst: core.Identity
) -> tuple[dict[str, object], str, list[str]]:
    """The slot values for one store, the manifest text it ships, and any collision.

    Parsed from the re-slugged text rather than re-slugged after parsing, so the
    manifest a stamped repo carries and the genes rendered from it cannot
    disagree — that repo's own drift check reads this same file back.

    The collision scan runs here rather than in the caller because this text
    reaches the stamp by two routes that both skip the file copier: it is
    emitted as the instance manifest, and its slot values are rendered into the
    eight shared genes. Those nine files are precisely where the prose most
    worth protecting lives.
    """
    raw = path.read_text(encoding="utf-8")
    stamped = core.reslug(raw, src, dst)
    data = yaml.safe_load(stamped)
    missing = [key for key in core.GLOBAL_KEYS if key not in data]
    if missing:
        sys.exit(f"{path.name}: missing required key(s) {missing}")
    declared = core.Identity.of(data)
    if declared != dst:
        sys.exit(
            f"{path.name} re-slugs to {declared}, but --instance was asked for {dst}.\n"
            "  Slot values are authored in the source store's identity and the flags name "
            "the destination; a values file declaring a third identity would stamp neither."
        )
    return data, stamped, core.occupied(raw, src, dst)


def frontend_sources() -> list[Path]:
    """Every Hydrogen template file a stamped store carries, sorted.

    Walked rather than globbed so the prune set can stop `node_modules` before
    it is descended into; a glob would enumerate ~40k files to discard them.
    """
    found: list[Path] = []
    for path in sorted(FRONTEND_DIR.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(FRONTEND_DIR)
        if core.FRONTEND_PRUNE_DIRS.intersection(rel.parts):
            continue
        if path.name in core.FRONTEND_SKIP_NAMES or rel.as_posix() in core.FRONTEND_PER_STORE:
            continue
        # `.env` holds this store's Storefront tokens; `.env.example` is a
        # template and is carried like any other tracked file.
        if path.name == ".env" or path.name.startswith(".env."):
            continue
        found.append(path)

    # The stamp is a text transform: every carried file is re-slugged and
    # re-valued for the destination store. A binary cannot go through that, and
    # silently dropping one would stamp a store missing an asset nobody notices
    # until the page renders. Refuse instead, and make the two ways forward
    # explicit.
    unreadable = []
    for path in found:
        try:
            path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            unreadable.append(str(path.relative_to(core.ROOT)))
    if unreadable:
        sys.exit(
            "instance stamp refused - frontend files the text transform cannot "
            "carry:\n  " + "\n  ".join(unreadable)
            + "\n  Either add the containing directory to FRONTEND_PRUNE_DIRS if a "
            "stamped store does not need it, or give instance_files a byte-copy "
            "channel. Do not let the stamp drop it silently."
        )
    return found


def instance_pages_yaml(intake: dict[str, object]) -> str:
    """The store's `frontend/pages.yaml`, narrowed to the pages it declares.

    `storefront.pages` is optional. Absent or UNSET means "every page the kit
    ships" — the honest default, because a store that has not chosen a page set
    wants the template's, not an empty storefront. When it *is* declared, the
    named pages are kept in the kit's order and everything else is dropped,
    which is what lets two stores share every component and still render
    different page sets.
    """
    text = (FRONTEND_DIR / "pages.yaml").read_text(encoding="utf-8")
    storefront = intake.get("storefront")
    declared = storefront.get("pages") if isinstance(storefront, dict) else None
    if not isinstance(declared, list) or not declared:
        # Returned verbatim so the file keeps its comments; safe_dump drops them.
        return text

    doc = yaml.safe_load(text)
    available = {page["name"] for page in doc["pages"]}
    unknown = sorted(set(declared) - available)
    if unknown:
        sys.exit(
            "instance stamp refused - storefront.pages names pages the kit does "
            f"not ship: {', '.join(unknown)}\n  available: {', '.join(sorted(available))}\n"
            "  A page named here but absent from frontend/pages.yaml would stamp a "
            "store whose route set silently lacks it."
        )
    doc["pages"] = [page for page in doc["pages"] if page["name"] in set(declared)]
    return yaml.safe_dump(doc, sort_keys=False)


def retitle_home(text: str, intake: dict[str, object]) -> str:
    """Retitle the home page for the destination store.

    `revaluation` deliberately covers only hostname and identifier fields, on the
    grounds that substituting brand prose wholesale corrupts more than it fixes.
    That is right, and it leaves this one field unhandled: the home `title` *is*
    the store's name, so a stamp that carried it verbatim would title every new
    store's home page after the store it came from.

    Rewritten as a line edit rather than a YAML round-trip, because `pages.yaml`
    is emitted verbatim when the intake declares no page subset — reserialising
    it would drop every comment in the file and break the FR-2 self-test's
    byte-identical guarantee. A store whose brand already matches is untouched,
    which is what keeps an identity stamp a no-op.

    Only `title` moves. The `copy` slots are taglines: template defaults a
    stamped store edits itself, not something to machine-translate into a
    sentence the brand never said.
    """
    brand = intake.get("brand")
    name = brand.get("brand_name") if isinstance(brand, dict) else None
    if not isinstance(name, str) or not name:
        return text

    lines = text.splitlines(keepends=True)
    in_home = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("- route:"):
            in_home = False
        if stripped == "name: home":
            in_home = True
        elif in_home and stripped.startswith("title:"):
            indent = line[: len(line) - len(line.lstrip())]
            lines[i] = f"{indent}title: {name}\n"
            break
    return "".join(lines)


class _Tree:
    """The stamped tree under construction, plus the identity-collision scan.

    A class rather than a nest of closures because the four phases below all
    need the same four things (destination map, collision findings, both
    identities, the deployment-value map), and threading those through as
    parameters obscured which phase actually wrote what.

    `taken` is the collision scan's accumulator. Every route into the tree
    reports into this one dict so the stamp can refuse once, at the end, naming
    every token at fault rather than the first one found.
    """

    def __init__(self, src: core.Identity, dst: core.Identity, repoint: dict[str, str]) -> None:
        self.src = src
        self.dst = dst
        self.repoint = repoint
        self.files: dict[Path, str] = {}
        self.taken: dict[str, str] = {}

    def named(self, path: Path) -> str:
        """Repo-relative where possible, so one message does not mix both forms."""
        try:
            return str(path.relative_to(core.ROOT))
        except ValueError:
            return str(path)

    def put(self, dest: Path, text: str) -> None:
        """Place already-rendered text. No collision scan: nothing was copied."""
        self.files[dest] = text

    def carry(self, source: Path, dest: Path, scan: bool = True) -> None:
        """Copy one file, re-slugged and re-valued for the destination store.

        `scan` is False for the destination's own intake: that file is *supposed*
        to contain the destination identity, so running the collision check over
        it reports every token the operator just chose.
        """
        body = source.read_text(encoding="utf-8")
        if scan:
            for token in core.occupied(body, self.src, self.dst):
                self.taken.setdefault(token, self.named(source))
        self.files[dest] = core.revalue(core.reslug(body, self.src, self.dst), self.repoint)


def _carry_project(tree: _Tree) -> None:
    """Species-owned agents and workflows, plus the capabilities snapshot.

    The shared genome arrives already rendered; everything else in the agents
    directory is species-owned content `--export` deliberately omits.
    """
    source_project = core.ROOT / "agentforge" / "projects" / tree.src.slug
    project = Path("agentforge") / "projects" / tree.dst.slug
    rendered = {
        f"{tree.src.prefix}-{t.name[: -len(core.TMPL_SUFFIX)]}.md" for t in core.gene_templates()
    }
    for gene in sorted((source_project / "agents").glob("*.md")):
        if gene.name not in rendered:
            tree.carry(gene, project / "agents" / core.reslug(gene.name, tree.src, tree.dst))
    for workflow in sorted((source_project / "workflows").glob("*.yaml")):
        tree.carry(
            workflow, project / "workflows" / core.reslug(workflow.name, tree.src, tree.dst)
        )
    tree.carry(CAPABILITIES_SNAPSHOT, CAPABILITIES_SNAPSHOT.relative_to(core.ROOT))


def _carry_packs_and_policy(tree: _Tree, intake: dict[str, object]) -> None:
    """Skill packs and policy rules.

    Deployment packs are rendered from the destination store's own intake, not
    copied. Copying them is what handed a new store the previous store's domains
    and brand — wrong data rather than a missing value.
    """
    for target, text in core.render_packs(intake).items():
        tree.put(
            Path("skills") / target.parent.name / target.name,
            core.reslug(text, tree.src, tree.dst),
        )
    for pack in sorted(SKILLS_DIR.glob("*/SKILL.md")):
        if pack.parent.name in core.PACK_SECTIONS:
            continue
        tree.carry(
            pack, Path("skills") / core.reslug(pack.parent.name, tree.src, tree.dst) / pack.name
        )
    for rules in sorted(POLICY_DIR.glob("*.yaml")):
        tree.carry(rules, Path("policy") / core.reslug(rules.name, tree.src, tree.dst))


def _carry_toolchain(
    tree: _Tree,
    intake: dict[str, object],
    manifest: str,
    intake_path: Path | None,
) -> None:
    """Everything that makes the stamped repo able to validate itself (NFR-7)."""
    for name in core.VALIDATOR_FAMILY:
        tree.carry(core.ROOT / "scripts" / name, Path("scripts") / name)
    for template in core.gene_templates():
        tree.carry(template, Path("dna-core") / "genes" / template.name)
    tree.carry(core.SKILLS_MANIFEST, core.SKILLS_MANIFEST.relative_to(core.ROOT))
    tree.carry(core.CORE / "README.md", Path("dna-core") / "README.md")
    # Carried so a stamped store can stamp the next one: the schema names what
    # its own intake must supply, and a store that cannot state that is not a
    # factory (FR-1 step 1 clones an instance repo as the template).
    tree.carry(core.INTAKE_SCHEMA, core.INTAKE_SCHEMA.relative_to(core.ROOT))
    for template in core.pack_templates():
        tree.carry(template, Path("dna-core") / "packs" / template.name)

    # The file, not a re-dump, when one exists: comments carry the provenance
    # anchors that make an intake auditable, and yaml.safe_dump drops them.
    written = intake_path or core.INTAKE_DIR / f"{tree.dst.slug}.yaml"
    destination = Path("dna-core") / "intake" / f"{tree.dst.slug}.yaml"
    if written.exists():
        tree.carry(written, destination, scan=False)
    else:
        tree.put(destination, yaml.safe_dump(intake, sort_keys=False))
    tree.put(Path("dna-core") / "species" / f"{tree.dst.slug}.yaml", manifest)

    for ref in sorted(inlined_artifacts()):
        tree.carry(core.ROOT / ref, Path(ref))
    for name in core.INSTANCE_ROOT_FILES:
        tree.carry(core.ROOT / name, Path(name))
    for name in core.INSTANCE_DOCS:
        tree.carry(core.ROOT / name, Path(name))


def _carry_frontend(tree: _Tree, intake: dict[str, object]) -> None:
    """The Hydrogen app, this store's page set, and its brand tokens."""
    # The shared half: the app itself, carried component-for-component.
    # Re-slugging applies here as everywhere else, so a store's own name
    # replaces the source store's in copy and comments.
    for source in frontend_sources():
        tree.carry(source, source.relative_to(core.ROOT))

    # The page set this store renders. Narrowed from the kit's by the intake,
    # so two stores diverge here without either editing a component.
    #
    # Re-valued as well as re-slugged, exactly like `carry`. Page titles and copy
    # slots hold the source store's brand prose — a stamp that only re-slugged
    # would hand the new store a page set still headlined with store one's name.
    tree.put(
        Path("frontend/pages.yaml"),
        core.revalue(
            core.reslug(retitle_home(instance_pages_yaml(intake), intake), tree.src, tree.dst),
            tree.repoint,
        ),
    )

    # The store-specific half. The app is shared and stamped from the kit; the
    # token file is generated from THIS store's intake, which is what makes one
    # template serve every store without a code edit (FR-3). A token set that
    # misses the schema's contrast floor refuses the stamp rather than producing
    # a repo that renders unreadable — same rule as `unfilled_required`: a stamp
    # that emits a broken repo is not a stamp.
    try:
        tokens = brand_tokens.build_tokens(intake, brand_tokens.load_schema_tokens())
    except brand_tokens.TokenError as exc:
        sys.exit(f"instance stamp refused - unusable brand tokens:\n  {exc}")
    for warning in tokens["warnings"]:
        print(f"  brand tokens: {warning}")
    tree.put(Path("frontend/brand.tokens.json"), json.dumps(tokens["tokens"], indent=2) + "\n")

    # Impeccable / UI-agent briefs. Intake stays source of truth; these are
    # stamped bridges so polish sessions do not invent purple/glass defaults
    # (TAP-5600, TAP-5605).
    try:
        briefs = design_brief.build_briefs(intake)
    except design_brief.BriefError as exc:
        sys.exit(f"instance stamp refused - unusable design brief:\n  {exc}")
    tree.put(Path("PRODUCT.md"), briefs["PRODUCT.md"])
    tree.put(Path("DESIGN.md"), briefs["DESIGN.md"])


def instance_files(
    values: Path,
    src: core.Identity,
    dst: core.Identity,
    intake: dict[str, object],
    intake_path: Path | None = None,
) -> dict[Path, str]:
    """Every file a stamped instance repo contains, keyed by repo-relative path.

    PRD Appendix B, less INSTANCE_PENDING. Building the whole tree in memory
    before writing anything is what lets the self-test diff a stamp against the
    checked-in kit without touching the filesystem.
    """
    repoint = core.revaluation(core.load_intake(src.slug), intake)
    data, manifest, clashes = instance_values(values, src, dst)

    tree = _Tree(src, dst, repoint)
    tree.files = {
        path.relative_to(core.ROOT): text for path, text in core.render_all(data).items()
    }
    tree.taken = dict.fromkeys(clashes, tree.named(values))

    _carry_project(tree)
    _carry_packs_and_policy(tree, intake)
    _carry_toolchain(tree, intake, manifest, intake_path)
    _carry_frontend(tree, intake)

    if tree.taken:
        sys.exit(
            "instance stamp refused - the requested identity is already in use as prose:\n  "
            + "\n  ".join(
                f"{token!r} already appears in {where}" for token, where in sorted(tree.taken.items())
            )
            + "\n  Re-slugging is a rename; renaming onto a word the kit already uses corrupts it "
            "on every later stamp taken from this store. Choose a different token."
        )
    return tree.files


def audit_unset(
    files: dict[Path, str], tiers: dict[str, dict[str, str]]
) -> tuple[list[str], int]:
    """Split UNSET across the emitted skill packs by tier (see UNSET_AUDITED).

    Returns (fatal findings, UNSET count legitimately left for provisioning).
    """
    fatal: list[str] = []
    deferred = 0
    for path, text in sorted(files.items()):
        count = text.count(core.UNSET)
        if not count or path.parts[0] != core.UNSET_AUDITED:
            continue
        tier = tiers.get(path.parent.name, {}).get("tier")
        if tier == core.DEPLOYMENT_TIER:
            deferred += count
            continue
        fatal.append(f"{path}: {count} UNSET slot(s) in a {tier!r}-tier pack")
    return fatal, deferred


def _refuse_bad_identity(src: core.Identity, dst: core.Identity, tiers: dict) -> None:
    """Every identity check that must fail before any file is rendered."""
    if bad := core.malformed(dst):
        sys.exit(
            "refusing to stamp a malformed identity:\n  "
            + "\n  ".join(bad)
            + "\n  These tokens become directory names and environment variable names."
        )
    for label, identity in (("this kit", src), ("the requested store", dst)):
        if repeated := core.indistinct(identity):
            sys.exit(
                f"{label} uses {', '.join(repr(t) for t in repeated)} for more than one of "
                "prefix/slug/env_prefix.\n  No rewrite can be correct for such an identity: "
                "the duplicated token would be replaced by whichever role is matched first, "
                "and the store could then only stamp children sharing the same defect."
            )
    rejected = core.leaks_into_exported_packs(dst, tiers) + core.reads_as_credential_failure(dst)
    if rejected:
        sys.exit(
            "instance stamp refused - the requested identity would fail the stamped repo's "
            "own validator:\n  " + "\n  ".join(rejected) + "\n  Choose a different token."
        )


def _sync_workflow_inputs(dest: Path) -> None:
    """Regenerate the stamped tree's generated workflow input defaults.

    The carried workflows still hold the source store's defaults: `revaluation`
    maps only hostname/identifier fields, while the inlined atlas carries prose
    facts (`head`, `plan`) a blind rewrite must not touch. Regenerate them from
    the stamped tree's own packs with the stamped tree's own script — the same
    one its `validate.py` checks against.
    """
    sync = subprocess.run(
        [sys.executable, "scripts/sync_workflow_inputs.py"],
        cwd=dest,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    # Exit 1 means "rewrote something", which is the expected first-stamp path.
    if sync.returncode not in (0, 1):
        sys.exit(f"instance stamp failed - workflow input sync:\n{sync.stderr}")


def instance(
    dest: Path,
    src: core.Identity,
    dst: core.Identity,
    values: Path,
    intake_path: Path | None = None,
) -> int:
    """Stamp a complete, self-validating instance repo for one store (FR-2)."""
    if dest.exists() and any(dest.iterdir()):
        sys.exit(f"refusing to stamp into non-empty {dest}")

    tiers = yaml.safe_load(core.SKILLS_MANIFEST.read_text(encoding="utf-8"))["skills"]
    _refuse_bad_identity(src, dst, tiers)

    intake = core.load_intake(dst.slug, intake_path)
    if unfilled := core.unfilled_required(intake):
        sys.exit(
            "instance stamp refused - the intake would fail the stamped repo's own "
            "validator:\n  " + "\n  ".join(unfilled) + "\n  A required field has no correct "
            "UNSET; fill it in the intake before stamping."
        )
    files = instance_files(values, src, dst, intake, intake_path)
    fatal, deferred = audit_unset(files, tiers)
    if fatal:
        sys.exit("instance stamp failed:\n  " + "\n  ".join(fatal))

    for rel, text in sorted(files.items()):
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")

    _sync_workflow_inputs(dest)

    print(f"stamped {len(files)} file(s) into {dest}")
    print(f"  identity: slug {dst.slug}, prefix {dst.prefix}, env_prefix {dst.env_prefix}")
    carried = sorted({token for text in files.values() for token in core.residue(text, src, dst)})
    if carried:
        print(f"  carried through unchanged: {', '.join(carried)}")
    if deferred:
        print(f"  {deferred} UNSET slot(s) in deployment-tier packs - filled at provisioning")
    for entry, why in sorted(core.INSTANCE_PENDING.items()):
        print(f"  not emitted: {entry} - {why}")
    return 0
