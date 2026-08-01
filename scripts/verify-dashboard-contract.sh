#!/usr/bin/env bash
#
# verify-dashboard-contract.sh — assert every endpoint the health-dashboard bundle
# references resolves to its expected HTTP status through the nginx proxy.
#
# This is the gate for the dashboard red-to-green work (TAP-5413). It encodes the
# *target* contract: the status each endpoint must return once the routing, auth,
# and phantom-endpoint work is complete. Running it against an unremediated stack
# reports the current split rather than the target.
#
# Usage:
#   scripts/verify-dashboard-contract.sh [BASE_URL]
#
#   BASE_URL             defaults to http://localhost:13000 (host-port override;
#                        the documented default 3000 is taken by another stack).
#
# Environment:
#   DASHBOARD_API_KEY    optional bearer token. Send it while the bundle still
#                        carries a credential; leave unset once nginx injects one.
#   CONTRACT_PACE        seconds between requests (default 1.1). admin-api rate
#                        limits at 60 req/min with burst 20 — an unpaced sweep
#                        produces false 429s.
#   CONTRACT_TIMEOUT     per-request timeout in seconds (default 10).
#
# Exit status: 0 when every endpoint matches its expected status, 1 otherwise.

set -uo pipefail

BASE_URL="${1:-http://localhost:13000}"
BASE_URL="${BASE_URL%/}"
PACE="${CONTRACT_PACE:-1.1}"
TIMEOUT="${CONTRACT_TIMEOUT:-10}"
KEY="${DASHBOARD_API_KEY:-}"

# path <TAB> expected-status <TAB> kind <TAB> rationale
#
# expected-status may list several acceptable codes separated by `|` where more
# than one is genuinely correct (an endpoint whose dataset may legitimately be
# empty). kind: http = plain GET; ws = WebSocket upgrade handshake.
#
# A `404 (decided)` row is an endpoint this dashboard deliberately does not
# serve. Each was resolved against the owning service's openapi.json and against
# the shipped bundle; none is referenced by application code. They are asserted
# rather than deleted so that re-introducing a call to a non-existent route
# fails this gate instead of silently painting a panel red.
read -r -d '' CONTRACT <<'EOF'
/api/health	200	http	admin-api
/api/v1/health	200	http	admin-api
/api/v1/health/services	200	http	admin-api
/api/v1/health/groups	200	http	admin-api
/api/v1/stats	200	http	admin-api
/api/v1/alerts/active	200	http	data-api
/api/v1/alerts/summary	200	http	data-api
/api/v1/analytics	200	http	data-api
/api/v1/energy/current	200	http	data-api
/api/v1/metrics	200	http	data-api
/api/v1/real-time-metrics	200	http	admin-api
/api/metrics/realtime	200	http	admin-api
/api/v1/docker/containers	200	http	admin-api
/api/v1/docker/api-keys	200	http	admin-api
/api/devices	200	http	data-api
/api/entities	200	http	data-api
/api/integrations	200	http	data-api
/api/v1/events	200	http	data-api
/api/areas	200	http	data-api; explicit location, else the /api/ catch-all rewrites it to admin-api
/api/labels	200	http	data-api; same catch-all fix as /api/areas
/api/v1/ha-proxy/states	200	http	admin-api; needs /api/v1/ha/ to keep its trailing slash
/api/v1/evaluations	200	http	data-api; EvaluationStore now resolves the Postgres DSN from env
/api/v1/services	200	http	data-api owns it per openapi.json, not admin-api
/api/v1/integrations	200	http	data-api owns it per openapi.json, not admin-api
/api/v1/activity	200|404	http	data-api; 404 with a "No ... available" detail is a valid empty state
/rag-service/health	200	http	rag-service via variable proxy_pass (re-resolves DNS)
/ai-automation/health	200	http	ai-automation via variable proxy_pass (re-resolves DNS)
/ws	101	ws	websocket-ingestion; admin-api registers no WebSocket route
/api/v1/health/integrations	404	http	404 (decided) not a route; HACSStatusCheck repointed to /api/integrations
/api/statistics	404	http	404 (decided) no such route on either backend; dead ControlPanel link removed
/api/v1/configuration	404	http	404 (decided) test-mock only; admin-api's real route is /api/v1/config
/api/v1/data-sources	404	http	404 (decided) never built; panel is mock-driven
/api/v1/memory/status	404	http	404 (decided) test-mock only; admin-api exposes /api/v1/memories/metrics
/api/v1/rag/status	404	http	404 (decided) test-mock only; rag-service health is /rag-service/health
/api/v1/sports	404	http	404 (decided) bare path unused; app calls /api/v1/sports/games/* (TAP-5411)
/api/v1/ha/status	404	http	404 (decided) no such route; data-api exposes /api/v1/ha/game-status/{team}
EOF

probe_http() {
    local url="$1"
    if [[ -n "$KEY" ]]; then
        curl -s -o /dev/null -w '%{http_code}' -m "$TIMEOUT" \
            -H "Authorization: Bearer $KEY" "$url"
    else
        curl -s -o /dev/null -w '%{http_code}' -m "$TIMEOUT" "$url"
    fi
}

probe_ws() {
    local url="$1"
    local -a auth=()
    [[ -n "$KEY" ]] && auth=(-H "Authorization: Bearer $KEY")
    curl -s -o /dev/null -w '%{http_code}' -m "$TIMEOUT" \
        -H 'Connection: Upgrade' \
        -H 'Upgrade: websocket' \
        -H 'Sec-WebSocket-Version: 13' \
        -H 'Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==' \
        "${auth[@]}" "$url"
}

total=0
pass=0
declare -a deviations=()

printf 'Dashboard contract sweep — %s\n' "$BASE_URL"
printf 'Auth: %s · pace: %ss/request\n\n' \
    "$([[ -n "$KEY" ]] && echo 'Bearer (client-supplied)' || echo 'none (nginx-injected)')" "$PACE"
printf '%-34s %-9s %-9s %s\n' 'ENDPOINT' 'EXPECT' 'ACTUAL' 'RESULT'
printf '%s\n' '--------------------------------------------------------------------'

first=1
while IFS=$'\t' read -r path expected kind rationale; do
    [[ -z "$path" ]] && continue
    (( first )) && first=0 || sleep "$PACE"
    total=$(( total + 1 ))

    if [[ "$kind" == "ws" ]]; then
        actual="$(probe_ws "${BASE_URL}${path}")"
    else
        actual="$(probe_http "${BASE_URL}${path}")"
    fi

    # `expected` may list several acceptable codes separated by `|`.
    matched=0
    while IFS= read -r code; do
        [[ "$actual" == "$code" ]] && { matched=1; break; }
    done < <(tr '|' '\n' <<< "$expected")

    if (( matched )); then
        pass=$(( pass + 1 ))
        printf '%-34s %-9s %-9s %s\n' "$path" "$expected" "$actual" 'PASS'
    else
        deviations+=("${path} expected ${expected}, got ${actual} — ${rationale}")
        printf '%-34s %-9s %-9s %s\n' "$path" "$expected" "$actual" 'FAIL'
    fi
done <<< "$CONTRACT"

fail=$(( total - pass ))

printf '\n'
if (( fail > 0 )); then
    printf 'Deviations:\n'
    for d in "${deviations[@]}"; do
        printf '  - %s\n' "$d"
    done
    printf '\n'
fi

printf 'RESULT: %d/%d endpoints at expected status, %d deviations\n' "$pass" "$total" "$fail"

(( fail == 0 ))
