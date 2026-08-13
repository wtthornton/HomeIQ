#!/usr/bin/env bash
# TAP-5291: forced-refresh flags must stay opt-in.
#
# The 2026-08-10 measurement found `--pull always --force-recreate` had been
# the DEFAULT in both start-stack entry points, silently turning every stack
# start into a full re-pull. The fix moved them behind STACK_REFRESH=1.
#
# This check enforces two conditions on every non-comment line that carries
# a literal flag:
#   1. it is a refresh-variable assignment (refresh_flags= / $refreshArgs =)
#      — hardcoding the flags onto the compose-up line itself (the exact
#      historical regression) fails here no matter where the line sits;
#   2. the `if ... STACK_REFRESH` conditional opens within the few lines
#      above it — an unconditional assignment fails here.
#
# Usage: check-stack-refresh-optin.sh [file ...]
#   Defaults to scripts/start-stack.sh and scripts/start-stack.ps1.
set -euo pipefail

GUARD_RE='if.*STACK_REFRESH'
ASSIGN_RE='refresh_flags=|\$refreshArgs[[:space:]]*='
WINDOW=3 # lines above an assignment within which the guard must open

fail=0

check_file() {
  local file=$1
  if [[ ! -f "$file" ]]; then
    echo "::error file=$file::start-stack script missing — refresh opt-in unverifiable"
    fail=1
    return
  fi
  while IFS=: read -r ln line; do
    [[ -z "$ln" ]] && continue
    if ! grep -qE "$ASSIGN_RE" <<<"$line"; then
      echo "::error file=$file,line=$ln::forced-refresh flag hardcoded outside the refresh-variable assignment: ${line}"
      fail=1
      continue
    fi
    local start=$((ln > WINDOW ? ln - WINDOW : 1))
    if ! sed -n "${start},${ln}p" "$file" | grep -qE "$GUARD_RE"; then
      echo "::error file=$file,line=$ln::refresh-variable assignment not guarded by an if ... STACK_REFRESH branch: ${line}"
      fail=1
    fi
  done < <(grep -nE -- '--pull always|--force-recreate|"--pull"|"--force-recreate"' "$file" \
             | grep -vE '^[0-9]+:\s*#' || true)
}

files=("$@")
if [[ ${#files[@]} -eq 0 ]]; then
  files=(scripts/start-stack.sh scripts/start-stack.ps1)
fi
for f in "${files[@]}"; do
  check_file "$f"
done

if [[ $fail -ne 0 ]]; then
  echo "FAIL: forced-refresh flags must appear only inside the STACK_REFRESH opt-in branch."
  exit 1
fi
echo "OK: refresh flags are opt-in only in: ${files[*]}"
