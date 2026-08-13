#!/usr/bin/env bash
# preflight-env.sh — fail loudly when a required env key is absent or empty
# (TAP-5902: the 2026-08-01 migration dropped 55 populated keys and nothing
# noticed for ten days).
#
# Modes:
#   preflight-env.sh                 check ROOT_ENV (default .env) against env.required
#   preflight-env.sh --ci            no .env needed: validate the manifest itself
#                                    (syntax, and every key documented in
#                                    infrastructure/env.example)
#
# Key-name discipline: this script never prints a value. It greps for presence
# and non-emptiness only, so its output is safe for logs and CI.
#
# Exit codes: 0 ok · 1 missing/empty required keys (named) · 2 usage/manifest error

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MANIFEST="${PREFLIGHT_MANIFEST:-$ROOT/env.required}"
ENV_FILE="${PREFLIGHT_ENV_FILE:-$ROOT/.env}"
EXAMPLE="${PREFLIGHT_EXAMPLE:-$ROOT/infrastructure/env.example}"

[[ -f "$MANIFEST" ]] || { echo "preflight: manifest not found: $MANIFEST" >&2; exit 2; }

mode="${1:-check}"

# Parse manifest rows: KEY<TAB>kind<TAB>reason (comments/blank skipped).
manifest_rows() {
  grep -vE '^[[:space:]]*(#|$)' "$MANIFEST"
}

if ! manifest_rows | awk -F'\t' 'NF < 2 || ($2 != "required" && $2 != "conditional") {bad=1} END {exit bad}'; then
  echo "preflight: malformed manifest row(s) in $MANIFEST (want KEY<TAB>required|conditional<TAB>reason)" >&2
  exit 2
fi

if [[ "$mode" == "--ci" ]]; then
  # CI has no .env: assert the manifest is coherent with the committed template
  # so a key rename can't silently strand the manifest.
  [[ -f "$EXAMPLE" ]] || { echo "preflight --ci: template not found: $EXAMPLE" >&2; exit 2; }
  undocumented=0
  while IFS=$'\t' read -r key _kind _reason; do
    if ! grep -qE "^#?[[:space:]]*${key}=" "$EXAMPLE"; then
      echo "preflight --ci: manifest key not documented in env.example: $key" >&2
      undocumented=1
    fi
  done < <(manifest_rows)
  [[ "$undocumented" -eq 0 ]] && echo "preflight --ci: manifest coherent ($(manifest_rows | wc -l) keys)"
  exit "$undocumented"
fi

[[ -f "$ENV_FILE" ]] || { echo "preflight: env file not found: $ENV_FILE (copy infrastructure/env.example to .env)" >&2; exit 1; }

missing=()
warned=()
while IFS=$'\t' read -r key kind _reason; do
  # Present AND non-empty, without ever echoing the value.
  if grep -qE "^${key}=..*" "$ENV_FILE"; then
    continue
  fi
  if [[ "$kind" == "required" ]]; then
    missing+=("$key")
  else
    warned+=("$key")
  fi
done < <(manifest_rows)

if ((${#warned[@]} > 0)); then
  echo "preflight: conditional keys absent or empty (their feeds run in standby): ${warned[*]}" >&2
fi

if ((${#missing[@]} > 0)); then
  echo "preflight: REQUIRED keys absent or empty in $ENV_FILE: ${missing[*]}" >&2
  echo "preflight: restore them from a backup at key-name level — see docs/operations/env-restore.md" >&2
  exit 1
fi

echo "preflight: all required env keys present and non-empty"
