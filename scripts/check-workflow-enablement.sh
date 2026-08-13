#!/usr/bin/env bash
# TAP-5291: documented auto-trigger workflows must be enabled at the API level.
#
# On 2026-08-10, 18 of 19 documented workflows were `disabled_manually` at the
# GitHub API level while their trigger blocks looked correct — nothing reported
# it. This check asserts every workflow in the README auto-trigger table
# (.github/workflows/README.md "What runs automatically") reports state
# `active` via the GitHub API. `dependabot-auto-merge` is exempt: documented
# as deliberately off.
#
# State source: `gh api` by default (needs GITHUB_TOKEN with actions:read).
# For testing, inject WORKFLOW_STATES_TSV with "path<TAB>state" lines.
set -euo pipefail

EXEMPT="dependabot-auto-merge"

# The documented auto-trigger set: every ci-*.yml (the domain-group row)
# plus the named rows of the README table.
documented=()
for f in .github/workflows/ci-*.yml; do
  documented+=("$(basename "$f" .yml)")
done
documented+=(quality-gate test integration-tests codeql-analysis docker-build
             docker-test compose-parse docker-security-scan agentic-pr-review)

if [[ -n "${WORKFLOW_STATES_TSV:-}" ]]; then
  states="$WORKFLOW_STATES_TSV"
else
  states=$(gh api "repos/${GITHUB_REPOSITORY:-wtthornton/HomeIQ}/actions/workflows" \
             --paginate -q '.workflows[] | [.path, .state] | @tsv')
fi

fail=0
for name in "${documented[@]}"; do
  [[ "$name" == "$EXEMPT" ]] && continue
  state=$(printf '%s\n' "$states" \
            | awk -F'\t' -v p=".github/workflows/${name}.yml" '$1 == p {print $2}')
  if [[ -z "$state" ]]; then
    echo "::error file=.github/workflows/${name}.yml::documented workflow not found via the GitHub API"
    fail=1
  elif [[ "$state" != "active" ]]; then
    echo "::error file=.github/workflows/${name}.yml::documented auto-trigger workflow is '${state}', expected 'active'"
    fail=1
  fi
done

if [[ $fail -ne 0 ]]; then
  echo "FAIL: documented workflows disabled at the API level (state != active)."
  echo "Re-enable via the Actions UI or: gh workflow enable <name>"
  exit 1
fi
echo "OK: all ${#documented[@]} documented auto-trigger workflows active (${EXEMPT} exempt)."
