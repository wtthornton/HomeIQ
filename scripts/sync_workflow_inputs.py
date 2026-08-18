"""Write committed facts into the workflow inputs that must carry them inline.

Genes have no filesystem. `AF_EXTERNAL_SKILLS_ROOT` is unset, no gene declares
`skills:`, and nothing publishes `skills/` — so a gene instructed to "read the
taxonomies skill" reads nothing (`docs/phase-b-plan.md` § 4a). The same is true of
anything else on disk: a judge asked whether a PNG still carries its C2PA manifest
cannot open the PNG. The content has to travel as workflow input.

For an on-demand chromosome the caller can supply it. For a **scheduled** one it
cannot: a scheduled fire passes no inputs at all, so the content must live in the
input's `default`. That is a literal second copy of a fact something else owns, and
the only thing making it safe is that it is generated here and verified by
`check_workflow_generated_defaults` on every `validate.py` run. Change the source,
run this, commit both.

## Why not a build step at publish time

The kit's `af_publish.py` is upstream and not ours to fork, and a transform that
runs only at publish makes the repo's YAML disagree with what is deployed — the
same drift in a less visible place. Generating into the file keeps the published
artifact and the reviewed artifact identical.

## What it does not do

It does not decide which facts a workflow needs, and it does not *produce* them —
it only carries them. `data/provenance-snapshot.json` is written by
`scripts/provenance_snapshot.py`, which is a deliberate, separate step precisely so
that `validate.py` can stay offline and never touch `c2pa` or the asset tree.

The mapping is `WORKFLOW_INPUT_SOURCES` in `kit_rules.py`, deliberately explicit: a
gene silently acquiring an input because a filename matched is how the
unreadable-skill class of defect got in.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import input_source
from kit_rules import WORKFLOW_INPUT_SOURCES, WORKFLOWS_DIR
from skill_pack import SkillPackError

# Matches the `default: |` block scalar this script writes, so a re-run replaces
# the previous body rather than appending to it.
BLOCK_INDENT = " " * 6


def render_default(source: tuple[str, str]) -> str:
    """A YAML block scalar carrying the source's body, indented for an input entry."""
    lines = [
        f"{BLOCK_INDENT}{line}".rstrip()
        for line in input_source.render(source).splitlines()
    ]
    return "    default: |\n" + "\n".join(lines) + "\n"


def input_block(name: str, source: tuple[str, str]) -> str:
    """One `inputs:` entry, generated whole.

    `type: string` and `required: false` are fixed, and that is a real constraint
    rather than an oversight: the value must be a `default` (a scheduled fire
    passes nothing), and a block scalar carries text. So a JSON artifact travels as
    inlined JSON-in-a-string rather than as structured YAML. Genes read text, so
    that costs nothing at the gene; it does mean nothing downstream can `$ref` into
    the structure.
    """
    return (
        f"  - name: {name}\n"
        f"    type: string\n"
        f"    required: false\n"
        f'    description: "{input_source.describe(source)}"\n'
        f"{render_default(source)}"
    )


def existing_entry_span(lines: list[str], input_name: str) -> tuple[int, int] | None:
    """Line span of an existing `- name: <input_name>` entry, or None.

    Ends at the next list item or the next top-level key, so a multi-line block
    scalar default is replaced whole rather than leaving an orphaned tail.
    """
    start = None
    for i, line in enumerate(lines):
        if line.strip() == f"- name: {input_name}":
            start = i
            break
    if start is None:
        return None
    for j in range(start + 1, len(lines)):
        stripped = lines[j].lstrip()
        if stripped.startswith("- name:"):
            return start, j
        if lines[j] and not lines[j][0].isspace() and not lines[j].startswith("#"):
            return start, j
    return start, len(lines)


def inputs_span(lines: list[str]) -> tuple[int, int]:
    """Line span of the `inputs:` block. Raises if the workflow has none."""
    start = next(i for i, line in enumerate(lines) if line.rstrip() == "inputs:")
    for j in range(start + 1, len(lines)):
        if lines[j] and not lines[j][0].isspace() and not lines[j].startswith("#"):
            return start, j
    return start, len(lines)


def sync_workflow(
    path: Path, mapping: dict[str, tuple[str, str]], *, check_only: bool
) -> list[str]:
    """Rewrite stale generated input defaults in place. Returns the names touched.

    Text surgery rather than a YAML round-trip on purpose: these workflow files
    carry more explanatory comment than spec, and `yaml.safe_dump` would discard
    every one of them.
    """
    import yaml

    text = path.read_text(encoding="utf-8")
    spec = yaml.safe_load(text)
    declared = {
        item.get("name"): item
        for item in (spec.get("inputs") or [])
        if isinstance(item, dict)
    }

    stale = []
    for input_name, source in sorted(mapping.items()):
        expected = input_source.render(source)
        current = (declared.get(input_name) or {}).get("default")
        if current is None or str(current).strip() != expected.strip():
            stale.append(input_name)

    if not stale or check_only:
        return stale

    lines = text.splitlines()
    for input_name in stale:
        block = input_block(input_name, mapping[input_name]).rstrip("\n").splitlines()
        span = existing_entry_span(lines, input_name)
        if span:
            lines[span[0]:span[1]] = block
        else:
            _, end = inputs_span(lines)
            lines[end:end] = block

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    # Re-parse: a bad block scalar must fail here, not at publish.
    yaml.safe_load(path.read_text(encoding="utf-8"))
    return stale


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true",
                        help="report drift and exit non-zero; write nothing")
    args = parser.parse_args(argv)

    total_stale = 0
    for workflow_name, mapping in sorted(WORKFLOW_INPUT_SOURCES.items()):
        path = WORKFLOWS_DIR / f"{workflow_name}.yaml"
        if not path.is_file():
            print(f"missing workflow: {path}", file=sys.stderr)
            return 2
        try:
            stale = sync_workflow(path, mapping, check_only=args.check)
        except SkillPackError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        if stale:
            total_stale += len(stale)
            if args.check:
                print(f"STALE {path.name}: {', '.join(stale)}", file=sys.stderr)

    if total_stale:
        # Exit 1 on the run that *fixed* things too. That reads wrong at first and
        # is deliberate: the files on disk changed, so anything downstream holding
        # a copy (a publish already staged, a diff already reviewed) is stale. A
        # caller that wants "did anything change" gets it from the exit code; one
        # that wants "is everything current" runs --check twice.
        verb = "out of sync" if args.check else "rewritten"
        print(f"\n{total_stale} generated input default(s) {verb}.", file=sys.stderr)
        return 1
    print("all generated workflow inputs match their sources.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
