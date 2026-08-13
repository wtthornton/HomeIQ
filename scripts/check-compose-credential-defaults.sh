#!/usr/bin/env bash
# TAP-5993: no tracked compose file may carry a non-empty default for a
# credential-bearing variable.
#
# A `${VAR:-realvalue}` default (or a baked literal) means the working
# credential is committed and world-readable on this PUBLIC repo, and a
# dropped env key silently downgrades the service onto it. Required form:
# `${VAR:?...}` or `${VAR}` — a missing key fails loudly.
#
# Name-level by design: findings print variable NAMES and locations, never
# values. Non-credential names containing TOKEN/KEY as a substring (expiry
# windows, file paths, booleans, numerics) are excluded.
set -euo pipefail

CRED='(PASSWORD|SECRET|TOKEN|API_KEY|CREDENTIAL)'

files=$(git ls-files 'domains/*/compose.yml' 'docker-compose*.yml' 'domains/*/*/docker-compose*.yml' 'simulation/docker-compose*.yml')

# Two bad shapes, detected directly:
#   a) ${CRED_NAME:-nonempty}  — fallback default (a default starting with
#      `${` is a nested interpolation, not a committed value: allowed)
#   b) CRED_NAME=literal       — baked value (values starting with `$` are
#      interpolations: allowed)
SHAPE_A="\\\$\{[A-Z0-9_]*${CRED}[A-Z0-9_]*:-[^}\$][^}]*\}"
SHAPE_B="^[[:space:]]*-?[[:space:]]*[A-Z0-9_]*${CRED}[A-Z0-9_]*=[^\$[:space:]]"

fail=0
while IFS=: read -r file ln content; do
  [[ -z "$file" ]] && continue
  name=$(grep -oE "[A-Z0-9_]*${CRED}[A-Z0-9_]*" <<<"$content" | head -1)
  [[ "$name" =~ (EXPIRE|EXPIRY|TTL|_FILE|_PATH|HEADER) ]] && continue
  value=$(sed -E 's/^[^=]*(:-|=)//' <<<"$content")
  [[ "$value" =~ ^(true|false|[0-9]+)\}?$ ]] && continue
  echo "::error file=${file},line=${ln}::non-empty credential default for ${name} — use \${${name}:?} and set the value in .env"
  fail=1
done < <({ grep -nE "$SHAPE_A" $files; grep -nE "$SHAPE_B" $files; } 2>/dev/null \
          | grep -vE '^[^:]+:[0-9]+:[[:space:]]*#' | sort -u || true)

if [[ $fail -ne 0 ]]; then
  echo "FAIL: committed credential defaults found (names only above; values never printed)."
  exit 1
fi
echo "OK: zero non-empty credential defaults across $(wc -w <<<"$files") tracked compose files."
