#!/usr/bin/env bash
# TAP-5291: documented auto-trigger workflows must be enabled at the API level.
#
# On 2026-08-10, 18 of 19 documented workflows were `disabled_manually` at the
# GitHub API level while their trigger blocks looked correct — nothing reported
# it. This check asserts every workflow in the README auto-trigger table
# (.github/workflows/README.md, "What runs automatically") reports state
# `active` via the GitHub API. `dependabot-auto-merge` is exempt: documented
# as deliberately off. The set is DERIVED from the README table (backticked
# names; the `ci-*` row expands via glob), so editing the table changes what
# is enforced. Scope note: the check is one-directional — it does not flag
# undocumented workflows that happen to auto-trigger.
#
# State source: `gh api` by default (needs GITHUB_TOKEN with actions:read).
# For testing, inject WORKFLOW_STATES_TSV with "path<TAB>state" lines.
set -euo pipefail

EXEMPT="dependabot-auto-merge"
README=".github/workflows/README.md"

# Rows of the auto-trigger table: everything between the "What runs
# automatically" heading and the next heading. Only the FIRST column names
# workflows (trigger cells carry backticked branches/paths); a cell may
# name several (e.g. docker-build, docker-test).
mapfile -t rows < <(awk -F'|' '/^## What runs automatically/{grab=1; next}
                               /^#/{grab=0}
                               grab && /^\|/ {print $2}' "$README" \
                     | grep -oE '`[^`]+`' | tr -d '`' \
                     | awk '!seen[$0]++')

documented=()
for row in "${rows[@]}"; do
  if [[ "$row" == *"*"* ]]; then
    # Glob row (e.g. ci-*): expand against the real workflow files.
    for f in .github/workflows/${row}.yml; do
      [[ -e "$f" ]] || continue
      documented+=("$(basename "$f" .yml)")
    done
  elif [[ -n "$row" ]]; then
    documented+=("$row")
  fi
done

if [[ ${#documented[@]} -eq 0 ]]; then
  echo "::error file=$README::could not parse any workflow names from the auto-trigger table"
  exit 1
fi

if [[ -n "${WORKFLOW_STATES_TSV:-}" ]]; then
  states="$WORKFLOW_STATES_TSV"
else
  states=$(gh api "repos/${GITHUB_REPOSITORY:-wtthornton/HomeIQ}/actions/workflows" \
             --paginate -q '.workflows[] | [.path, .state] | @tsv')
fi

fail=0
checked=0
skipped=0
for name in "${documented[@]}"; do
  if [[ "$name" == "$EXEMPT" ]]; then
    skipped=$((skipped + 1))
    continue
  fi
  checked=$((checked + 1))
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
echo "OK: ${checked} documented auto-trigger workflows active (${skipped} exempt: ${EXEMPT})."
