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
# Extension-less tokens: a bare `<word>:<digits>` with no file extension on
# <word> (e.g. "core-platform:69") cannot be resolved with confidence — it is
# reported as its own row, `<token> . (unresolved path) . no`, rather than
# silently skipped, UNLESS <word> actually resolves to a real file (rare),
# in which case it is verified like any other anchor.
#
# Also compares the handoff's "Pinned SHA <sha>" line against the tree at
# <tree-root>. Three cases:
#   - identical:  pinned sha (prefix match) equals `git rev-parse HEAD`.
#   - ancestor, no anchor files touched: pinned sha is an ancestor of HEAD
#     and `git diff --name-only <pinned>..HEAD` contains none of the files
#     any anchor in this handoff resolved to — the anchors are unaffected by
#     what moved since the pin, so they still describe HEAD accurately.
#   - MISMATCH: neither of the above (not an ancestor, or an ancestor but at
#     least one anchor's file changed since the pin — the anchor can no
#     longer be trusted to describe HEAD without re-verification).
# The case that applied is printed alongside pinned_sha.
#
# Exit 0: every row "yes" and pinned_sha matches (either case above).
# Exit 1: any row "no", or pinned_sha MISMATCHes.
# Exit 2: zero anchor tokens found in the handoff (a check that checks
#         nothing must refuse, not report a false green).

set -euo pipefail

handoff="${1:?usage: check-handoff-anchors.sh <handoff.md> [<tree-root>]}"
tree_root="${2:-.}"

[[ -f "$handoff" ]] || { echo "error: handoff file not found: $handoff" >&2; exit 1; }
[[ -d "$tree_root" ]] || { echo "error: tree root not found: $tree_root" >&2; exit 1; }

token_re='[A-Za-z0-9_./-]+\.[A-Za-z0-9_]+:[0-9]+(-[0-9]+)?'
# Extension-less "path-shaped" token: requires a '/' or '-' in the word so a
# plain word or a timestamp fragment (e.g. "T06:24" in an ISO stamp) cannot
# match — genuine bare anchors in this project are kebab-case dir/service
# names ("core-platform:69") or slash paths, never a single bare word. The
# number side is matched greedily through any dotted continuation so an
# `image:tag` reference like "homeiq/home-assistant:2026.8.3" is captured
# whole rather than truncated at the first dot — a trailing "." after the
# digits marks a version tag, not a line number, and is filtered out below.
bare_token_re='[A-Za-z][A-Za-z0-9_]*[/-][A-Za-z0-9_/-]*:[0-9]+(\.[0-9]+)*(-[0-9]+)?'
ident_re='[A-Z][A-Za-z0-9]*[A-Z][A-Za-z0-9]*|[A-Z][A-Z0-9_]{2,}|[a-zA-Z_][a-zA-Z0-9_]*\(\)'

pinned_sha="$(grep -oE 'Pinned SHA [0-9a-f]{7,40}' "$handoff" | head -1 | awk '{print $3}' || true)"
actual_sha="$(git -C "$tree_root" rev-parse HEAD)"
declare -a anchor_files=()

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

# Strip the tree-root prefix so a resolved path is comparable to
# `git diff --name-only`, whose entries are relative to the repo root.
relpath_under_tree() {
  local p="$1" root="${tree_root%/}"
  if [[ "$p" == "$root/"* ]]; then
    printf '%s' "${p#"$root"/}"
  else
    printf '%s' "$p"
  fi
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
        anchor_files+=("$(relpath_under_tree "$resolved")")
      fi
    fi
    [[ "$found" == "no" ]] && any_no=1
    printf '%s . %s . %s\n' "$token" "${symbol:-<none>}" "$found"
  done < <(grep -oE "$token_re" <<<"$line")

  # Mask out the extension-having tokens already handled above so a
  # dotted token like "compose.yml:743" cannot spuriously re-match as the
  # bare suffix "yml:743" below.
  masked="$line"
  while IFS= read -r t; do
    [[ -z "$t" ]] && continue
    masked="${masked//$t/$(printf '%*s' "${#t}" '')}"
  done < <(grep -oE "$token_re" <<<"$line")

  while read -r token; do
    [[ -z "$token" ]] && continue
    path="${token%%:*}"
    rest="${token#*:}"
    if [[ "$rest" == *.* ]]; then
      continue  # "name:2026.8.3" is an image tag, not a line-number anchor
    fi
    count=$((count + 1))
    if [[ "$rest" == *-* ]]; then
      a="${rest%-*}"; b="${rest#*-}"
    else
      a="$rest"; b="$rest"
    fi

    resolved="$(resolve_path "$path")"
    if [[ -z "$resolved" ]]; then
      any_no=1
      printf '%s . (unresolved path) . no\n' "$token"
      continue
    fi

    # <word> resolved to a real file despite lacking an extension — verify
    # it exactly like an extension-having anchor.
    symbol="$(expected_symbol_for_line "$line" "$token")"
    if [[ -z "$symbol" ]]; then
      symbol="$(bullet_symbol_for "$lineno" "$token")"
    fi
    found="no"
    if [[ -n "$symbol" ]]; then
      body="$(sed -n "${a},${b}p" "$resolved" 2>/dev/null || true)"
      if grep -qF -- "$symbol" <<<"$body"; then
        found="yes"
        anchor_files+=("$(relpath_under_tree "$resolved")")
      fi
    fi
    [[ "$found" == "no" ]] && any_no=1
    printf '%s . %s . %s\n' "$token" "${symbol:-<none>}" "$found"
  done < <(grep -oE "$bare_token_re" <<<"$masked")
done < <(grep -nE "$token_re|$bare_token_re" "$handoff")

if (( count == 0 )); then
  echo "error: zero anchor tokens found in $handoff" >&2
  exit 2
fi

# --- pinned sha: identical / ancestor-unaffected / MISMATCH ---
sha_status="MISMATCH"
sha_case="pinned sha not set or not found"
if [[ -n "$pinned_sha" ]]; then
  if [[ "$actual_sha" == "$pinned_sha"* ]]; then
    sha_status="match"
    sha_case="identical"
  elif git -C "$tree_root" merge-base --is-ancestor "$pinned_sha" "$actual_sha" 2>/dev/null; then
    changed_files="$(git -C "$tree_root" diff --name-only "$pinned_sha".."$actual_sha")"
    touched=""
    for f in "${anchor_files[@]:-}"; do
      [[ -z "$f" ]] && continue
      if grep -qxF -- "$f" <<<"$changed_files"; then
        touched="$f"
        break
      fi
    done
    if [[ -z "$touched" ]]; then
      sha_status="match"
      sha_case="ancestor, no anchor files touched"
    else
      sha_status="MISMATCH"
      sha_case="ancestor but anchor file touched: $touched"
    fi
  else
    sha_case="pinned sha is not HEAD or an ancestor of HEAD"
  fi
fi

echo "pinned_sha: $sha_status ($sha_case)"
[[ "$sha_status" == "MISMATCH" ]] && any_no=1

exit "$any_no"
