#!/usr/bin/env bash
# check-handoff-anchors.sh — verify a session-handoff.md's path:line anchors
# against the tree they claim to describe.
#
# Usage: check-handoff-anchors.sh <handoff.md> [<tree-root>]
#
# Anchor token: a substring matching <path>:<line> or <path>:<a>-<b>, where
# <path> is a bare filename or a relative path ending in a file extension
# (e.g. "recipes.py:339-404", "core-platform/compose.yml:743"). Extracted
# directly from the handoff text with one regex.
#
# Path resolution: <tree-root>/<path> is tried first (paths are meant to be
# relative to the tree root). This project's handoffs often write only the
# bare filename (e.g. "host_files.py:97-132" for
# libs/homeiq-ha/src/homeiq_ha/agent/host_files.py), so on a miss we fall
# back to the first file under <tree-root> whose path ends with "/<path>"
# (`find -path "*/<path>"`). A path that resolves to no file at all is a
# "no" row.
#
# Expected-symbol rule (what the token is claimed to point at):
#   1. Same line as the token: the backtick-quoted `word` closest to the
#      token — preferring one that appears BEFORE the token in reading
#      order, else the first one after.
#   2. If the line has no backtick token: the same preference (before, then
#      after) applied to identifier-shaped words on that line — CamelCase
#      (>=2 uppercase letters), ALL_CAPS_CONST, or a `name()` call.
#   3. If the token's own line yields nothing: widen to the enclosing
#      bullet — walk backward to the nearest line starting with "-" (after
#      trimming leading whitespace), then scan forward from there through
#      the token's line, taking the first backtick or identifier match.
#      (In this project bullets are single unwrapped lines, so step 3
#      rarely differs from steps 1-2; it exists for wrapped bullets.)
#
# "Found": sed -n '<a>,<b>p' <resolved-path> contains the expected symbol as
# a literal substring. A token with no derivable expected symbol cannot be
# verified and counts as "no".
#
# Also compares the handoff's "Pinned SHA <sha>" line against
# `git -C <tree-root> rev-parse HEAD` (prefix match), printing
# "pinned_sha: match|MISMATCH".
#
# Exit 0: every row "yes" and pinned_sha matches.
# Exit 1: any row "no", or pinned_sha mismatches.
# Exit 2: zero anchor tokens found in the handoff (a check that checks
#         nothing must refuse, not report a false green).

set -euo pipefail

handoff="${1:?usage: check-handoff-anchors.sh <handoff.md> [<tree-root>]}"
tree_root="${2:-.}"

[[ -f "$handoff" ]] || { echo "error: handoff file not found: $handoff" >&2; exit 1; }
[[ -d "$tree_root" ]] || { echo "error: tree root not found: $tree_root" >&2; exit 1; }

token_re='[A-Za-z0-9_./-]+\.[A-Za-z0-9_]+:[0-9]+(-[0-9]+)?'
ident_re='[A-Z][A-Za-z0-9]*[A-Z][A-Za-z0-9]*|[A-Z][A-Z0-9_]{2,}|[a-zA-Z_][a-zA-Z0-9_]*\(\)'

# --- pinned sha ---
pinned_sha="$(grep -oE 'Pinned SHA [0-9a-f]{7,40}' "$handoff" | head -1 | awk '{print $3}' || true)"
actual_sha="$(git -C "$tree_root" rev-parse HEAD)"
sha_status="MISMATCH"
if [[ -n "$pinned_sha" && "$actual_sha" == "$pinned_sha"* ]]; then
  sha_status="match"
fi

# Return the backtick or identifier match closest to (preferring before)
# position $2 in string $1, restricted to matches found via regex $3.
nearest_match() {
  local line="$1" before="$2" regex="$3"
  local best=""
  while IFS= read -r m; do
    [[ -z "$m" ]] && continue
    best="$m"
  done < <(grep -oE "$regex" <<<"$before")
  if [[ -n "$best" ]]; then
    printf '%s' "$best"
    return
  fi
  local after="${line#"$before"}"
  grep -oE "$regex" <<<"$after" | head -1
}

expected_symbol_for_line() {
  local line="$1" token="$2"
  local before="${line%%"$token"*}"
  local sym
  sym="$(nearest_match "$line" "$before" '`[^`]+`')"
  sym="${sym//\`/}"
  if [[ -n "$sym" ]]; then
    printf '%s' "$sym"
    return
  fi
  nearest_match "$line" "$before" "$ident_re"
}

bullet_symbol_for() {
  local lineno="$1" token="$2"
  local start="$lineno"
  while (( start > 1 )); do
    local prev
    prev="$(sed -n "$((start - 1))p" "$handoff")"
    local trimmed="${prev#"${prev%%[![:space:]]*}"}"
    [[ "$trimmed" == -* ]] && break
    start=$((start - 1))
  done
  local ln
  for ((ln = start; ln <= lineno; ln++)); do
    local bl
    bl="$(sed -n "${ln}p" "$handoff")"
    local cand
    cand="$(grep -oE '`[^`]+`' <<<"$bl" | head -1 || true)"
    cand="${cand//\`/}"
    if [[ -z "$cand" ]]; then
      cand="$(grep -oE "$ident_re" <<<"$bl" | head -1 || true)"
    fi
    if [[ -n "$cand" ]]; then
      printf '%s' "$cand"
      return
    fi
  done
}

resolve_path() {
  local path="$1"
  if [[ -f "$tree_root/$path" ]]; then
    printf '%s' "$tree_root/$path"
    return
  fi
  find "$tree_root" -type f -path "*/$path" 2>/dev/null | head -1
}

any_no=0
count=0

while IFS= read -r rawline; do
  lineno="${rawline%%:*}"
  line="${rawline#*:}"
  while read -r token; do
    [[ -z "$token" ]] && continue
    count=$((count + 1))
    path="${token%%:*}"
    rest="${token#*:}"
    if [[ "$rest" == *-* ]]; then
      a="${rest%-*}"; b="${rest#*-}"
    else
      a="$rest"; b="$rest"
    fi

    symbol="$(expected_symbol_for_line "$line" "$token")"
    if [[ -z "$symbol" ]]; then
      symbol="$(bullet_symbol_for "$lineno" "$token")"
    fi

    resolved="$(resolve_path "$path")"
    found="no"
    if [[ -n "$resolved" && -n "$symbol" ]]; then
      body="$(sed -n "${a},${b}p" "$resolved" 2>/dev/null || true)"
      if grep -qF -- "$symbol" <<<"$body"; then
        found="yes"
      fi
    fi
    [[ "$found" == "no" ]] && any_no=1
    printf '%s . %s . %s\n' "$token" "${symbol:-<none>}" "$found"
  done < <(grep -oE "$token_re" <<<"$line")
done < <(grep -nE "$token_re" "$handoff")

echo "pinned_sha: $sha_status"
[[ "$sha_status" == "MISMATCH" ]] && any_no=1

if (( count == 0 )); then
  echo "error: zero anchor tokens found in $handoff" >&2
  exit 2
fi

exit "$any_no"
