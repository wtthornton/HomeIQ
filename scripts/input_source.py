"""Resolve a generated workflow input to the exact text a gene will receive.

One function, two callers, and that is the entire point. `sync_workflow_inputs.py`
writes the text into a workflow's input `default`; `check_workflow_generated_defaults`
recomputes it and errors if the committed copy has drifted. If those two ever
computed the body differently the check would either pass on a stale default or
fail on a correct one, so they resolve through here and nowhere else.

This started as skill-pack-only. It was generalised when provenance measurement
needed the same generate-and-diff loop: the mechanism was never about skills, it
was about "a fact a gene cannot read for itself, committed, and kept honest".

The two kinds render differently on purpose:

- `SKILL_PACK` goes through `skill_pack.as_prompt_block`, which prepends version,
  `verified_at` and expiry. A judge asked to echo `matrix_version` can only answer
  honestly if that header travels with the body.
- `ARTIFACT` is carried **verbatim**. `data/provenance-snapshot.json` already
  states its own `checked_at`, `c2pa` versions and `trust_list` as fields; adding a
  generated header would be a second copy of those, in a different format, drifting
  independently.
"""

from __future__ import annotations

from pathlib import Path

from kit_rules import ARTIFACT, ROOT, SKILL_PACK
from skill_pack import SkillPackError, as_prompt_block, load_pack


def render(source: tuple[str, str]) -> str:
    """The text for one generated input. Raises `SkillPackError` if unresolvable.

    Reuses `SkillPackError` for a missing artifact rather than adding a second
    exception type: every caller already handles it as "the source could not be
    read, and a gene must never be handed an empty body instead".
    """
    kind, ref = source
    if kind == SKILL_PACK:
        return as_prompt_block(load_pack(ref))
    if kind == ARTIFACT:
        path = ROOT / ref
        try:
            body = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise SkillPackError(f"artifact {ref!r} unreadable at {path}: {exc}") from exc
        if not body.strip():
            raise SkillPackError(f"artifact {ref!r} is empty at {path}")
        return body
    raise SkillPackError(f"unknown input source kind {kind!r} for {ref!r}")


def describe(source: tuple[str, str]) -> str:
    """The `description:` line for a generated input entry.

    Says where the value came from and why it is inlined, because the next reader
    of the workflow file sees a wall of generated text and needs to know not to
    hand-edit it.
    """
    kind, ref = source
    if kind == SKILL_PACK:
        return f"{ref} skill pack, inlined — genes cannot read skills/ at runtime."
    return f"Generated from {ref} — inlined because genes have no filesystem."


def regenerate_hint(source: tuple[str, str]) -> str:
    """How to make a stale default current again, named per source kind."""
    kind, ref = source
    if kind == SKILL_PACK:
        return f"edit skills/{ref}/SKILL.md then run scripts/sync_workflow_inputs.py"
    return f"regenerate {ref}, then run scripts/sync_workflow_inputs.py"


def artifact_path(ref: str) -> Path:
    """Repo-absolute path for an `ARTIFACT` reference."""
    return ROOT / ref
