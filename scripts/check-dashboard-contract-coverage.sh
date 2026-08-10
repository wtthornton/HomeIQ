#!/usr/bin/env bash
#
# check-dashboard-contract-coverage.sh — fail when the health dashboard calls an
# API path that scripts/verify-dashboard-contract.sh does not assert.
#
# The contract sweep itself needs the whole stack running, so it cannot gate a
# pull request. This check can: it compares the API paths referenced in the SPA
# source against the contract table, so adding a fetch to a new endpoint fails
# the build until that endpoint gets an expected status. That is the regression
# this guards — a route silently joining the dashboard's fan-out and then
# rendering red in production with nothing to catch it.
#
# Paths are compared by their first two segments, because the contract asserts
# collection endpoints (/api/v1/alerts) while the SPA also calls item endpoints
# (/api/v1/alerts/{id}/acknowledge) that share their routing and ownership.
#
# Usage: scripts/check-dashboard-contract-coverage.sh
# Exit status: 0 when every referenced path prefix is covered, 1 otherwise.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="${REPO_ROOT}/domains/core-platform/health-dashboard/src"
CONTRACT="${REPO_ROOT}/scripts/verify-dashboard-contract.sh"

if [[ ! -d "$SRC" ]]; then
    printf 'Dashboard source not found at %s\n' "$SRC" >&2
    exit 1
fi

# Two leading segments of a path, e.g. /api/v1/alerts/x -> /api/v1
# (three for /api/v1/* so ownership is distinguishable).
prefix_of() {
    local path="$1"
    if [[ "$path" == /api/v1/* ]]; then
        printf '%s\n' "$(echo "$path" | cut -d/ -f1-4)"
    else
        printf '%s\n' "$(echo "$path" | cut -d/ -f1-3)"
    fi
}

# Paths the contract already asserts.
mapfile -t contract_paths < <(
    sed -n '/^read -r -d .. CONTRACT <</,/^EOF$/p' "$CONTRACT" |
        grep -oE '^/[a-zA-Z0-9/_.-]+' | sort -u
)

declare -A covered=()
for path in "${contract_paths[@]}"; do
    covered["$(prefix_of "$path")"]=1
done

# Strip TypeScript comments so prose cannot read as a call site. A JSDoc block
# that names a removed endpoint in backticks is indistinguishable from a live
# literal to a plain grep, which is what turned api.ts's AIAutomationApiClient
# note into three phantom endpoints. Quote-aware, so a path in real code is
# never mistaken for the start of a comment.
strip_ts_comments() {
    python3 - "$@" <<'PY'
import sys


def strip(src):
    out = []
    i, n = 0, len(src)
    while i < n:
        ch = src[i]
        if ch in "'\"`":
            out.append(ch)
            i += 1
            while i < n:
                c = src[i]
                if c == "\\" and i + 1 < n:
                    out.append(src[i:i + 2])
                    i += 2
                    continue
                out.append(c)
                i += 1
                if c == ch:
                    break
            continue
        if src.startswith("//", i):
            while i < n and src[i] != "\n":
                i += 1
            continue
        if src.startswith("/*", i):
            end = src.find("*/", i + 2)
            i = n if end < 0 else end + 2
            continue
        out.append(ch)
        i += 1
    return "".join(out)


for path in sys.argv[1:]:
    with open(path, encoding="utf-8", errors="replace") as fh:
        sys.stdout.write(strip(fh.read()))
        sys.stdout.write("\n")
PY
}

# Files whose API references count as calls the app makes. Excluded by path, not
# by matched text: the previous `grep -rh | grep -v` filtered the matches
# themselves, so no test or mock file was ever actually skipped.
mapfile -t src_files < <(
    find "$SRC" -type f \( -name '*.ts' -o -name '*.tsx' \) \
        -not -path '*/mocks/*' \
        -not -path '*/tests/*' \
        -not -path '*/__tests__/*' |
        sort
)

# Paths the SPA actually calls. Template segments (${id}) are dropped.
mapfile -t referenced < <(
    strip_ts_comments "${src_files[@]}" |
        grep -oE "['\"\`]/(api|ws|rag-service|ai-automation|setup-service|log-aggregator|weather|websocket-ingestion)[a-zA-Z0-9/_.-]*" |
        tr -d "'\"\`" | sort -u
)

# Known gaps, recorded 2026-08-01. The contract was enumerated from the
# endpoints exercised during the red-to-green triage, which turned out to be a
# subset of what the SPA calls. These path families have no asserted status yet.
#
# This is a ratchet, not an exemption: the list is fixed, so any *new* endpoint
# fails the build immediately, while the existing backlog is closed one entry at
# a time. Deleting an entry here after adding it to the CONTRACT table is the
# intended direction of travel. See TAP-5413 follow-up.
KNOWN_GAPS=(
    /ai-automation
    /api/pattern
    /api/sports
    /api/v1
    /api/v1/entities
    /api/v1/hygiene
    /log-aggregator/api
    /rag-service
    /setup-service
    /weather/current-weather
    /websocket-ingestion
)
declare -A known=()
for prefix in "${KNOWN_GAPS[@]}"; do
    known["$prefix"]=1
done

uncovered=()
still_missing=()
for path in "${referenced[@]}"; do
    prefix="$(prefix_of "$path")"
    if [[ -n "${covered[$prefix]:-}" ]]; then
        continue
    fi
    if [[ -n "${known[$prefix]:-}" ]]; then
        still_missing+=("$prefix")
        continue
    fi
    uncovered+=("${path}  (prefix ${prefix})")
done

if (( ${#still_missing[@]} > 0 )); then
    mapfile -t still_missing < <(printf '%s\n' "${still_missing[@]}" | sort -u)
    printf 'Known gaps still open: %d (see KNOWN_GAPS)\n' "${#still_missing[@]}"
fi

printf 'Contract entries : %d\n' "${#contract_paths[@]}"
printf 'Source references: %d\n' "${#referenced[@]}"

if (( ${#uncovered[@]} > 0 )); then
    printf '\nEndpoints called by the dashboard but absent from the contract:\n'
    printf '  - %s\n' "${uncovered[@]}"
    printf '\nAdd each to the CONTRACT table in scripts/verify-dashboard-contract.sh\n'
    printf 'with the status it is expected to return.\n'
    exit 1
fi

if (( ${#still_missing[@]} > 0 )); then
    printf '\nRESULT: no new uncovered endpoints (%d known gap(s) still open)\n' \
        "${#still_missing[@]}"
else
    printf '\nRESULT: every dashboard API path is covered by the contract\n'
fi
