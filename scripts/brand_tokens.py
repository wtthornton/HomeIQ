#!/usr/bin/env python3
"""Project a store's intake `tokens` block into the front end's `brand.tokens.json`.

TAP-5389. One template parameterised per store is the whole cost model, so the
front end must read every colour and face from this file and never from code.
That makes the file the single point where a store can render itself unreadable,
which is why this module does more than copy keys across.

The intake schema states that `text_primary` and `text_secondary` "must clear
WCAG AA against `bg_primary`", and that a token which only passes AA Large is
"a caption nobody can read". Nothing enforced it. A stamped store whose brand
happens to pair a mid grey with a mid background would have produced a
technically valid token file and an illegible storefront, and the failure would
have surfaced as a human squinting at a deployed site rather than as a build
error. So the contrast rule is checked here, at stamp time, against the same
thresholds the schema names.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
INTAKE_SCHEMA = REPO_ROOT / "dna-core" / "intake.schema.yaml"
DEFAULT_OUTPUT = REPO_ROOT / "frontend" / "brand.tokens.json"

# WCAG 2.2 SC 1.4.3. Normal-size text needs 4.5:1; 3.0:1 is the large-text
# allowance the schema explicitly refuses for body and caption colours.
AA_NORMAL = 4.5
# Pairs the schema requires to be legible, as (foreground, background). Failing
# one of these is an error: the schema says so, and the store renders unreadable.
CONTRAST_PAIRS = (
    ("text_primary", "bg_primary"),
    ("text_secondary", "bg_primary"),
    # The label on a filled primary action — the checkout button, the hero call
    # to action, the consent banner's accept and reject. The schema states it
    # "must clear WCAG AA against `accent_primary`", and nothing enforced that
    # until a contrast audit measured the storefront and found white sitting on
    # this store's amber at 2.98:1 and 4.17:1 across the gradient's two stops:
    # below AA, on the button a shopper has to press to buy anything. Checked
    # here so the next store cannot ship it, rather than being found by a
    # human squinting at a deployment.
    #
    # Graded against `accent_primary` rather than against `gradient`: a
    # gradient is not a colour this module can measure, and the flat accent is
    # both the declared fallback and, for the usual accent-to-lighter-accent
    # ramp, its darker end.
    ("text_on_accent", "accent_primary"),
)
# Pairs the schema does not mandate but that carry text in practice. The schema
# describes `accent_primary` as the colour of "buttons, active states, price" —
# and a price is text, so an accent below AA is a legibility problem even though
# no rule names it. Warned rather than failed, because inventing a requirement
# the contract does not state would block stores over a judgement call.
#
# Store zero is exactly this case: its style guide records 4.6:1 for
# `accent_primary`, but that figure is measured against `#0a0e13` — a darker
# ground than its own `bg_primary` of `#0f1419`. On the background the tokens
# actually ship, the same colour measures 4.44:1 and misses AA.
ADVISORY_CONTRAST_PAIRS = (("accent_primary", "bg_primary"),)
HEX_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
RGB_RE = re.compile(r"^rgba?\(([^)]+)\)$", re.IGNORECASE)


class TokenError(ValueError):
    """A token set that would produce an unusable storefront."""


def load_schema_tokens() -> dict[str, dict[str, Any]]:
    """Return the `tokens` block of the intake schema — the contract."""
    schema = yaml.safe_load(INTAKE_SCHEMA.read_text(encoding="utf-8"))
    return schema["tokens"]


def parse_color(value: str) -> tuple[float, float, float] | None:
    """Return 0-255 RGB for a hex or rgb()/rgba() colour, else None.

    Returning None rather than raising is deliberate: the schema allows "a CSS
    color function", and this module must not reject a valid colour form it
    simply cannot measure. An unmeasurable colour skips the contrast check with
    a warning instead of failing the stamp.
    """
    value = value.strip()
    if HEX_RE.match(value):
        digits = value[1:]
        if len(digits) == 3:
            digits = "".join(c * 2 for c in digits)
        return tuple(int(digits[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]

    match = RGB_RE.match(value)
    if not match:
        return None
    parts = [p.strip() for p in match.group(1).replace("/", ",").split(",")]
    try:
        channels = [float(p.rstrip("%")) for p in parts[:3]]
    except ValueError:
        return None
    if len(channels) < 3:
        return None
    return channels[0], channels[1], channels[2]


def relative_luminance(rgb: tuple[float, float, float]) -> float:
    """WCAG relative luminance for an sRGB triple."""
    channels = []
    for raw in rgb:
        c = raw / 255.0
        channels.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    red, green, blue = channels
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast_ratio(foreground: str, background: str) -> float | None:
    """Return the WCAG contrast ratio, or None when either colour is unmeasurable."""
    fg, bg = parse_color(foreground), parse_color(background)
    if fg is None or bg is None:
        return None
    light, dark = sorted((relative_luminance(fg), relative_luminance(bg)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


def check_required(tokens: dict[str, Any], schema: dict[str, dict[str, Any]]) -> list[str]:
    """Return one message per required token that is absent or blank."""
    problems = []
    for name, spec in schema.items():
        if not spec.get("required"):
            continue
        value = tokens.get(name)
        if value is None or not str(value).strip():
            problems.append(f"required token {name!r} is missing — see intake.schema.yaml")
    return problems


def check_contrast(tokens: dict[str, Any]) -> tuple[list[str], list[str]]:
    """Return (errors, warnings) for the schema's stated legibility pairs."""
    errors: list[str] = []
    warnings: list[str] = []
    for foreground, background in CONTRAST_PAIRS:
        if foreground not in tokens or background not in tokens:
            continue  # absence is check_required's finding, not this one's
        ratio = contrast_ratio(str(tokens[foreground]), str(tokens[background]))
        if ratio is None:
            warnings.append(
                f"{foreground} on {background}: contrast not measurable "
                "(non-hex colour form) — verify by hand"
            )
        elif ratio < AA_NORMAL:
            errors.append(
                f"{foreground} on {background} is {ratio:.2f}:1, below WCAG AA "
                f"{AA_NORMAL}:1 — the schema refuses the large-text allowance here"
            )

    for foreground, background in ADVISORY_CONTRAST_PAIRS:
        if foreground not in tokens or background not in tokens:
            continue
        ratio = contrast_ratio(str(tokens[foreground]), str(tokens[background]))
        if ratio is not None and ratio < AA_NORMAL:
            warnings.append(
                f"{foreground} on {background} is {ratio:.2f}:1, below WCAG AA "
                f"{AA_NORMAL}:1 — not a schema requirement, but this token carries "
                "price text, so do not render prices in it at normal size"
            )
    return errors, warnings


def build_tokens(intake: dict[str, Any], schema: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Return the token payload for a store, or raise on an unusable set.

    Optional tokens are emitted only when the store supplied them, so the front
    end can fall back rather than read an empty string as a font stack.
    """
    tokens = intake.get("tokens") or {}
    if not isinstance(tokens, dict):
        msg = "intake `tokens` must be a mapping"
        raise TokenError(msg)

    problems = check_required(tokens, schema)
    errors, warnings = check_contrast(tokens)
    problems.extend(errors)
    if problems:
        raise TokenError("; ".join(problems))

    payload = {name: tokens[name] for name in schema if tokens.get(name)}
    if unknown := sorted(set(tokens) - set(schema)):
        # Not fatal, but silently dropping them would let a store think it had
        # set something the front end never reads.
        warnings.append(f"tokens not in the schema were dropped: {unknown}")
    return {"tokens": payload, "warnings": warnings}


def main(argv: list[str] | None = None) -> int:
    """Write a store's brand.tokens.json; exit non-zero on an unusable token set."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--intake", type=Path, required=True, help="dna-core/intake/<slug>.yaml")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    intake = yaml.safe_load(args.intake.read_text(encoding="utf-8"))
    try:
        result = build_tokens(intake, load_schema_tokens())
    except TokenError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    for warning in result["warnings"]:
        print(f"warn: {warning}", file=sys.stderr)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result["tokens"], indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(result['tokens'])} token(s) to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
