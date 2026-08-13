#!/usr/bin/env bash
# TAP-5291: forced-refresh flags must stay opt-in.
#
# The 2026-08-10 measurement found `--pull always --force-recreate` had been
# the DEFAULT in both start-stack entry points, silently turning every stack
# start into a full re-pull. The fix moved them behind STACK_REFRESH=1.
#
# Branch-aware static check (comments stripped before matching):
#   - Only the exact sanctioned guard opens an opt-in branch:
#       sh : if [[ "${STACK_REFRESH:-0}" == "1" ]]; then
#       ps1: if ($env:STACK_REFRESH -eq "1") {
#     A loosened conditional (e.g. -ne "__never__") is NOT recognized, so
#     flags inside it are flagged. Known limit: a textually identical guard
#     with different runtime semantics cannot exist, so this closes the
#     guard-neutering class as far as a static check can.
#   - A literal flag is legal only on a refresh-variable assignment line
#     INSIDE that branch (sh: until its matching fi, nesting-aware;
#     ps1: until brace depth returns to zero).
#
# Usage: check-stack-refresh-optin.sh [file ...]
#   Defaults to scripts/start-stack.sh and scripts/start-stack.ps1.
set -euo pipefail

fail=0

check_sh() {
  awk '
    { line = $0; sub(/#.*$/, "", line) }
    in_guard && line ~ /^[[:space:]]*if[[:space:]]/ { nest++ }
    !in_guard && line ~ /if[[:space:]]+\[\[[[:space:]]+"\$\{STACK_REFRESH:-0\}"[[:space:]]+==[[:space:]]+"1"[[:space:]]+\]\]/ {
      in_guard = 1; nest = 0; next
    }
    in_guard && line ~ /^[[:space:]]*fi([;[:space:]]|$)/ {
      if (nest > 0) nest--; else in_guard = 0
      next
    }
    line ~ /--pull always|--force-recreate/ {
      if (!in_guard || line !~ /refresh_flags=/) {
        printf "::error file=%s,line=%d::forced-refresh flag outside the sanctioned STACK_REFRESH branch: %s\n", FILENAME, FNR, $0
        bad = 1
      }
    }
    END { exit bad }
  ' "$1"
}

check_ps1() {
  awk '
    { line = $0; sub(/#.*$/, "", line) }
    !in_guard && line ~ /if[[:space:]]*\(\$env:STACK_REFRESH[[:space:]]+-eq[[:space:]]+"1"\)[[:space:]]*\{/ {
      in_guard = 1
      depth = gsub(/\{/, "{", line) - gsub(/\}/, "}", line)
      next
    }
    in_guard {
      depth += gsub(/\{/, "{", line) - gsub(/\}/, "}", line)
      if (depth <= 0) { in_guard = 0 }
    }
    line ~ /--pull|--force-recreate/ {
      if (!in_guard || line !~ /\$refreshArgs[[:space:]]*=/) {
        printf "::error file=%s,line=%d::forced-refresh flag outside the sanctioned STACK_REFRESH branch: %s\n", FILENAME, FNR, $0
        bad = 1
      }
    }
    END { exit bad }
  ' "$1"
}

check_file() {
  local file=$1
  if [[ ! -f "$file" ]]; then
    echo "::error file=$file::start-stack script missing — refresh opt-in unverifiable"
    fail=1
    return
  fi
  case "$file" in
    *.ps1) check_ps1 "$file" || fail=1 ;;
    *)     check_sh "$file" || fail=1 ;;
  esac
}

files=("$@")
if [[ ${#files[@]} -eq 0 ]]; then
  files=(scripts/start-stack.sh scripts/start-stack.ps1)
fi
for f in "${files[@]}"; do
  check_file "$f"
done

if [[ $fail -ne 0 ]]; then
  echo "FAIL: forced-refresh flags must appear only as refresh-variable assignments inside the STACK_REFRESH opt-in branch."
  exit 1
fi
echo "OK: refresh flags are opt-in only in: ${files[*]}"
