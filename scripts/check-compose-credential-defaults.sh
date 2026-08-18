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

# Four bad shapes, detected directly (case-insensitive names):
#   a) ${CRED_NAME:-nonempty}   — fallback default (a default starting with
#      `${` is a nested interpolation, not a committed value: allowed)
#   b) CRED_NAME=literal        — baked env-list value (values starting
#      with `$` are interpolations: allowed)
#   c) scheme://user:literal@   — credentials baked inside a connection
#      URL: flags an authority that is entirely literal (contains a colon
#      and no interpolation before the @). A URL whose user OR password is
#      interpolated contains `$` and is not flagged — the one unhandled
#      edge is a literal password paired with an interpolated user.
#   d) CRED_NAME: literal       — mapping-style environment blocks
SHAPE_A="\\\$\{[A-Za-z0-9_]*${CRED}[A-Za-z0-9_]*:-[^}\$][^}]*\}"
SHAPE_B="^[[:space:]]*-?[[:space:]]*[A-Za-z0-9_]*${CRED}[A-Za-z0-9_]*=[^\$[:space:]]"
SHAPE_C="[a-z+]+://[^@\$[:space:]]+:[^@\$[:space:]]+@"
SHAPE_D="^[[:space:]]+[A-Za-z0-9_]*${CRED}[A-Za-z0-9_]*:[[:space:]]+[^\$[:space:]]"

fail=0
while IFS=: read -r file ln content; do
  [[ -z "$file" ]] && continue
  # Name from the ASSIGNMENT TARGET only (before the first = or :) — never
  # from the value, which could echo a password substring into the log.
  # `|| true`: a target with no credential-shaped name (URL shapes) must
  # not abort the loop under set -e.
  target=${content%%=*}; target=${target%%:*}
  name=$(grep -oiE "[A-Z0-9_]*${CRED}[A-Z0-9_]*" <<<"$target" | head -1 || true)
  if [[ -n "$name" ]]; then
    [[ "${name^^}" =~ (EXPIRE|EXPIRY|TTL|_FILE|_PATH|HEADER) ]] && continue
    value=$(sed -E 's/^[^=:]*(:-|=|:[[:space:]]+)//' <<<"$content")
    [[ "$value" =~ ^(true|false|[0-9]+)\}?$ ]] && continue
    label="$name"
  else
    label="inside the value — literal credential in a URL or non-credential-named variable"
  fi
  echo "::error file=${file},line=${ln}::committed credential value (${label}) — interpolate from .env with \${VAR:?}"
  fail=1
done < <({ grep -inE "$SHAPE_A" $files /dev/null
           grep -inE "$SHAPE_B" $files /dev/null
           grep -nE  "$SHAPE_C" $files /dev/null
           grep -inE "$SHAPE_D" $files /dev/null; } 2>/dev/null \
          | grep -vE '^[^:]+:[0-9]+:[[:space:]]*#' | sort -u || true)

# TAP-6036: tracked env TEMPLATES (infrastructure/env.*) must not carry
# non-empty credential values either — they are copied to .env verbatim, so
# a baked value is a committed working credential. Same name-level contract:
# print names and locations, never values. An interpolation value (`$...`)
# is allowed; anything else non-empty on a credential-shaped name fails.
env_files=$(git ls-files 'infrastructure/env.*' || true)
if [[ -n "$env_files" ]]; then
  while IFS=: read -r file ln content; do
    [[ -z "$file" ]] && continue
    target=${content%%=*}
    name=$(grep -oiE "[A-Z0-9_]*${CRED}[A-Z0-9_]*" <<<"$target" | head -1 || true)
    [[ -z "$name" ]] && continue
    [[ "${name^^}" =~ (EXPIRE|EXPIRY|TTL|_FILE|_PATH|HEADER) ]] && continue
    value=${content#*=}
    [[ -z "$value" || "$value" == \$* ]] && continue
    [[ "$value" =~ ^(true|false|[0-9]+)$ ]] && continue
    echo "::error file=${file},line=${ln}::committed credential value (${name}) in a tracked env template — leave empty, set locally after copying to .env"
    fail=1
  done < <(grep -inE "^[A-Za-z0-9_]*${CRED}[A-Za-z0-9_]*=" $env_files /dev/null 2>/dev/null \
            | grep -vE '^[^:]+:[0-9]+:[[:space:]]*#' || true)
fi

if [[ $fail -ne 0 ]]; then
  echo "FAIL: committed credential defaults found (names only above; values never printed)."
  exit 1
fi
echo "OK: zero non-empty credential defaults across $(wc -w <<<"$files") tracked compose files and $(wc -w <<<"$env_files") tracked env templates."
