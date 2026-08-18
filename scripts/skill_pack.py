"""Load a skill pack so it can be handed to a gene as an explicit input.

Genes in this species run with no filesystem access. `allowed_tools` across all
29 is some subset of `''`, `WebFetch`, `WebSearch`, `http_fetch` and the
`tapps-brain` MCP server — none of which can open `skills/*/SKILL.md`. AgentForge
*does* have a mechanism for this (a `skills:` frontmatter key resolved through
its ResourceRegistry, backed by an `AF_EXTERNAL_SKILLS_ROOT` mount), but no gene
in this repo declares that key and the mount is unset, so at runtime the skill
directory does not exist from a gene's point of view.

That matters because several genes are *instructed* to read a pack:

    wstore-judge-disclosure.md:84   "Read the dated `ai-disclosure-matrix` skill
                                     and echo its version in `matrix_version`"

An instruction to read an unreachable file has exactly two outcomes, and both
are bad. The model either hallucinates a `matrix_version` — a judge inventing
the authority it is citing — or it fails closed on every asset, which looks
responsible and certifies nothing. A gate that always blocks is worth as little
as one that always approves; `docs/phase1-gate.md` § 7.1 is the local record of
what a number like that costs.

The repo already solved this once, and this module generalises that solution
rather than inventing a second one. `workflows/agent-readiness.yaml:13-16`:

    `queries` is the store-atlas citation corpus, passed explicitly: the gene
    runs with no filesystem access and cannot read the skill itself

So: read the pack here, where there *is* a filesystem, and pass its text in as
a declared input. The gene stops guessing, and the version it echoes is the
version that was actually loaded.

Two things this module refuses to paper over:

1. **An expired pack is reported, not silently served.** `ai-disclosure-matrix`
   carries `verified_at` / `expires` because the regimes it describes change on
   short notice. The pack's own text tells a judge reading it past expiry to say
   so in its findings — that judge can only comply if expiry travels with the
   content, so `expired` is computed here and passed alongside the body.
2. **An `UNSET`-heavy pack is flagged.** `store-atlas` and `brand-voice-pack` are
   `tier: deployment` in `dna-core/skills.yaml` and ship with `UNSET`
   placeholders by design. Handing one to a gene without saying so is worse than
   handing it nothing: the gene reads placeholders as facts. `unset_count` makes
   that visible to the caller before the pack is spent on an invoke.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml

SKILLS_ROOT = Path(__file__).resolve().parent.parent / "skills"

# Deployment-tier packs ship these until a real deployment fills them in.
UNSET_TOKEN = "UNSET"


class SkillPackError(Exception):
    """The pack is absent or malformed — never degrade to an empty body."""


def _split_frontmatter(text: str, path: Path) -> tuple[dict[str, Any], str]:
    if not text.startswith("---"):
        raise SkillPackError(f"{path}: no YAML frontmatter")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise SkillPackError(f"{path}: frontmatter is not terminated")
    try:
        front = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError as exc:
        raise SkillPackError(f"{path}: frontmatter is not valid YAML: {exc}") from exc
    if not isinstance(front, dict):
        raise SkillPackError(f"{path}: frontmatter is not a mapping")
    return front, parts[2].strip()


def load_pack(
    name: str, skills_root: Path = SKILLS_ROOT, today: date | None = None
) -> dict[str, Any]:
    """Read one skill pack into the payload a gene can be handed.

    Raises `SkillPackError` rather than returning a pack with an empty body. A
    gene told "here is the matrix" and given nothing is strictly worse off than
    a gene told the matrix is missing.
    """
    path = skills_root / name / "SKILL.md"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SkillPackError(f"skill pack {name!r} unreadable at {path}: {exc}") from exc

    front, body = _split_frontmatter(text, path)
    if not body:
        raise SkillPackError(f"skill pack {name!r} has frontmatter but no body")

    expires_raw = front.get("expires")
    expired = False
    if expires_raw:
        reference = today or date.today()
        try:
            expires_on = datetime.strptime(str(expires_raw), "%Y-%m-%d").date()
            expired = expires_on < reference
        except ValueError as exc:
            raise SkillPackError(
                f"skill pack {name!r}: `expires` is not YYYY-MM-DD: {expires_raw}"
            ) from exc

    return {
        "name": front.get("name", name),
        "version": str(front.get("version", "unversioned")),
        "verified_at": str(front.get("verified_at")) if front.get("verified_at") else None,
        "expires": str(expires_raw) if expires_raw else None,
        "expired": expired,
        "unset_count": body.count(UNSET_TOKEN),
        "body": body,
    }


def as_prompt_block(pack: dict[str, Any]) -> str:
    """Render a pack as the text block handed to a gene.

    The header is not decoration. A judge is asked to echo `matrix_version`, and
    the only honest source for that value is the pack that was actually loaded —
    so the version, the expiry state and the placeholder count travel *with* the
    body rather than in a separate argument the model may not connect to it.
    """
    lines = [
        f"### Skill pack: {pack['name']} v{pack['version']}",
        f"verified_at: {pack['verified_at'] or 'unrecorded'}",
        f"expires: {pack['expires'] or 'no expiry declared'}",
    ]
    if pack["expired"]:
        lines.append(
            "STATUS: EXPIRED — past its re-verify date. Say so in your findings; "
            "do not treat its contents as current."
        )
    if pack["unset_count"]:
        lines.append(
            f"STATUS: INCOMPLETE — contains {pack['unset_count']} UNSET placeholder(s). "
            "An UNSET value is an absent fact, never a real one."
        )
    lines.append("")
    lines.append(pack["body"])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("name", help="skill pack directory name, e.g. ai-disclosure-matrix")
    parser.add_argument("--skills-root", type=Path, default=SKILLS_ROOT)
    parser.add_argument(
        "--format", choices=["json", "prompt"], default="prompt",
        help="`prompt` emits the block to paste into a gene input",
    )
    args = parser.parse_args(argv)

    try:
        pack = load_pack(args.name, args.skills_root)
    except SkillPackError as exc:
        print(f"skill pack error: {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps(pack, indent=2, sort_keys=True))
    else:
        print(as_prompt_block(pack))

    if pack["expired"]:
        print(f"WARN {pack['name']} expired {pack['expires']}", file=sys.stderr)
    if pack["unset_count"]:
        print(
            f"WARN {pack['name']} carries {pack['unset_count']} UNSET placeholder(s)",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
