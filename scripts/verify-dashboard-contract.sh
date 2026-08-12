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
#   CONTRACT_TIMEOUT     per-request timeout in seconds (default 10). Was
#                        temporarily 15 while /api/v1/real-time-metrics sat at
#                        ~10.0s waiting out a downstream aiohttp timeout; that
#                        endpoint now runs its fan-out under a 1.5s budget
#                        (TAP-5439), so the default is back at 10.
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
#
# NON-GET COVERAGE (TAP-5434). The sweep issues GETs only, and that is
# deliberate rather than a gap left open. The dashboard's POST/PUT/DELETE
# families are all state-mutating — restart/start/stop a container, resolve or
# acknowledge an alert, apply a hygiene fix, rewrite an entity's name or labels.
# A sweep that exercised them for real would restart services and mutate live
# Home Assistant metadata on every CI run, so their bodies are out of scope by
# design.
#
# They are still covered, by asserting `405` on a GET: that proves the route is
# registered and method-guarded while changing nothing. A 404 there means the
# route vanished, which is exactly the regression worth catching. What a 405 row
# does NOT check is request/response shape — that belongs in service-level tests.
#
# WHAT IS DELIBERATELY ABSENT. Rows are only added for endpoints observed
# behaving correctly. Roughly twenty frontend families are live defects today
# (energy 5xx, the memory brain's absent schema, ai-automation's missing
# `patterns` table, websocket-ingestion down, /api/v1/events/search and
# /api/v1/integrations/{service}/config with no route). They are deliberately
# NOT listed: asserting them at 200 would make this gate red for reasons it
# cannot fix, and asserting their current 5xx would freeze today's breakage into
# the contract. They are tracked as defects instead. Add the row when the defect
# is fixed, not before.
#
# ABSOLUTE-URL CALL SITES (TAP-5434). The bundle once held six fetches built on
# `import.meta.env.VITE_*_URL || 'http://localhost:PORT'`, unprobeable here
# because they bypass nginx entirely. Neither VITE_ var was set anywhere in the
# repo, so the fallback was always what shipped — and it named the browser's own
# localhost, not the server's. All six are now gone.
#
# Five were unreachable: SynergiesTab and the AnalyticsDashboard it owned lost
# their nav entry and registry slot in 9c170ff2 (2026-02-26, app consolidation)
# and were never lazy-loaded by Dashboard again. Both files are deleted, which
# is why no /api/v1/synergies or /api/v1/blueprint-opportunities row appears
# below despite ai-pattern-service answering those paths 200 today.
#
# The sixth, ConventionComplianceCard's naming audit, was live and misrouted:
# host port 8019 belongs to device-health-monitor, while device-intelligence
# publishes on 8028. It only ever 404'd because the service it reached has no
# such route — a path collision would have returned someone else's 200. It now
# goes through the /device-intelligence/ location and has a row.
#
# The two remaining localhost literals in the bundle (3001, 8501) are external
# UI hrefs, not fetches, so nothing here can probe them.
read -r -d '' CONTRACT <<'EOF'
/api/health	200	http	admin-api
/api/v1/health	200	http	admin-api
/api/v1/health/services	200	http	admin-api
/api/v1/health/services/data-api	200	http	admin-api; single-service route added in TAP-5433, DataSourcesPanel calls it
/api/v1/health/groups	200	http	admin-api
/api/v1/health/dependencies	200	http	admin-api
/api/v1/health/metrics	200	http	admin-api
/api/v1/stats	200	http	admin-api
/api/v1/stats?period=24h	200	http	admin-api; the parameterised form the dashboard actually issues
/api/v1/config	200	http	admin-api; the real route behind the /api/v1/configuration mock
/api/v1/real-time-metrics	200	http	admin-api
/api/v1/docker/containers	200	http	admin-api
/api/v1/docker/api-keys	200	http	admin-api
/api/v1/docker/containers/admin-api/stats	200	http	admin-api; only compose-managed names resolve, others are a deliberate 400
/api/v1/docker/containers/admin-api/logs?tail=10	200	http	admin-api; returns mock text while the docker socket is unreadable, but the route is live
/api/v1/alerts	200	http	data-api
/api/v1/alerts/active	200	http	data-api
/api/v1/alerts/summary	200	http	data-api
/api/v1/analytics	200	http	data-api
/api/v1/analytics?range=1h	200	http	data-api; the parameterised form the dashboard issues
/api/v1/energy/current	200	http	data-api
/api/v1/events	200	http	data-api
/api/v1/events/{EVENT_ID}	200	http	data-api; id resolved at runtime from /api/v1/events
/api/v1/events/stats?period=24h	200	http	data-api
/api/v1/events/search	404	http	data-api; POST-only (frontend sends POST+CSRF, verified 200 live TAP-5446) — a GET probe falls into /events/{event_id} with id="search" and 404s, which proves the events router is mounted; nginx CSRF-gates non-GET so this sweep stays GET-only
/api/v1/integrations	200	http	data-api; shared integration router (TAP-5447), lists .env.{service} files from infrastructure/service-configs
/api/v1/integrations/websocket/config	200	http	data-api; ConfigForm's route — needs the seeded .env.websocket in infrastructure/service-configs (see its README); unknown services 404 by design
/api/v1/ha/game-status/VGK	200	http	data-api; TAP-5448 — answers no_game when sports_data holds no rows for the team, which is the honest empty state
/api/v1/ha/game-context/VGK	200	http	data-api; TAP-5448 — same no_game semantics as game-status
/api/devices	200	http	data-api
/api/devices/{DEVICE_ID}	200	http	data-api; id resolved at runtime from /api/devices
/api/entities	200	http	data-api
/api/entities/{ENTITY_ID}	200	http	data-api; id resolved at runtime from /api/entities
/api/integrations	200	http	data-api
/api/integrations?limit=10	200	http	data-api
/api/integrations/hue/analytics	200	http	data-api; sub-path survives the prefix proxy_pass, contrary to a static read of nginx.conf
/api/integrations/hue/performance?period=7d	200	http	data-api; same sub-path check as /analytics
/api/areas	200	http	data-api; explicit location, else the /api/ catch-all rewrites it to admin-api
/api/labels	200	http	data-api; same catch-all fix as /api/areas
/api/v1/ha-proxy/states	200	http	admin-api; needs /api/v1/ha/ to keep its trailing slash
/api/v1/evaluations	200	http	data-api; EvaluationStore now resolves the Postgres DSN from env
/api/v1/services	200	http	data-api owns it per openapi.json, not admin-api
/api/v1/integrations	200	http	data-api owns it per openapi.json, not admin-api
/api/v1/activity	200|404	http	data-api; 404 with a "No ... available" detail is a valid empty state
/api/v1/activity/history?hours=24&limit=10	200	http	data-api
/api/sports/teams	200	http	data-api via the /api/sports -> /api/v1/sports rewrite
/api/v1/sports/games/live	200	http	data-api
/api/v1/sports/games/history?team=BAL	200	http	data-api; BAL is a static NFL team id, not environment state
/api/v1/sports/schedule/BAL	200	http	data-api; client method added in TAP-5433, route existed and was unreachable
/api/v1/memories/metrics	200	http	admin-api; was 422 until TAP-5433 moved it above the /{memory_id} route
/rag-service/health	200	http	rag-service via variable proxy_pass (re-resolves DNS)
/rag-service/api/v1/metrics	200	http	rag-service; the only /api/v1/metrics the dashboard actually calls
/ai-automation/health	200	http	ai-automation via variable proxy_pass (re-resolves DNS)
/ai-automation/api/analysis/schedule	200	http	ai-automation; the /api segment was missing from the client until TAP-5433
/ai-automation/api/suggestions/list	200	http	ai-automation; same missing /api segment
/ai-automation/api/suggestions/usage/stats	200	http	ai-automation; client had it as /suggestions/usage-stats, a different segmentation
/setup-service/health	200	http	ha-setup-service via variable proxy_pass
/log-aggregator/api/v1/logs?limit=10	200	http	log-aggregator
/log-aggregator/api/v1/logs/search?q=error	200	http	log-aggregator
/weather/current-weather	200	http	weather-api via variable proxy_pass
/device-intelligence/api/naming/audit?limit=500	200	http	device-intelligence via variable proxy_pass; nginx injects X-API-Key, which this service wants instead of Bearer
/ws	101	ws	websocket-ingestion; admin-api registers no WebSocket route
/api/v1/docker/containers/admin-api/restart	405	http	405 (method-guarded) POST route; a GET proves it exists without restarting anything
/api/v1/docker/containers/admin-api/start	405	http	405 (method-guarded) POST route
/api/v1/docker/containers/admin-api/stop	405	http	405 (method-guarded) POST route; never exercised for real in a sweep
/api/v1/docker/api-keys/openai	405	http	405 (method-guarded) PUT route
/api/v1/docker/api-keys/openai/test	405	http	405 (method-guarded) POST route
/api/v1/services/data-api/restart	405	http	405 (method-guarded) POST route; this is what the frontend calls, not bare /api/v1/services
/api/v1/entities/{ENTITY_ID}/name	405	http	405 (method-guarded) PUT route; mutates HA metadata, never swept for real
/api/v1/entities/{ENTITY_ID}/aliases	405	http	405 (method-guarded) PUT route
/api/v1/entities/{ENTITY_ID}/labels	405	http	405 (method-guarded) PUT route
/api/v1/entities/bulk-label	405	http	405 (method-guarded) POST route
/api/v1/alerts/sample-id/acknowledge	405	http	405 (method-guarded) POST route; the id is never dereferenced on a GET
/api/v1/alerts/sample-id/resolve	405	http	405 (method-guarded) POST route
/api/v1/hygiene/issues/sample-key/status	405	http	405 (method-guarded) PUT route; 404 before this run added the nginx /api/v1/hygiene location
/api/v1/hygiene/issues/sample-key/actions/apply	405	http	405 (method-guarded) POST route; same nginx fix
/api/v1/health/integrations	404	http	404 (decided) not a route; HACSStatusCheck repointed to /api/integrations
/api/statistics	404	http	404 (decided) no such route on either backend; dead ControlPanel link removed
/api/v1/configuration	404	http	404 (decided) test-mock only; admin-api's real route is /api/v1/config
/api/v1/data-sources	404	http	404 (decided) never built; panel is mock-driven
/api/v1/memory/status	404	http	404 (decided) test-mock only; admin-api exposes /api/v1/memories/metrics
/api/v1/rag/status	404	http	404 (decided) test-mock only; rag-service health is /rag-service/health
/api/v1/sports	404	http	404 (decided) bare path unused; app calls /api/v1/sports/games/* (TAP-5411)
/api/v1/ha/status	404	http	404 (decided) no such route; data-api exposes /api/v1/ha/game-status/{team}
/api/v1/energy	404	http	404 (decided) bare prefix is not a route; the app calls /api/v1/energy/* leaves
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

fetch_body() {
    if [[ -n "$KEY" ]]; then
        curl -s -m "$TIMEOUT" -H "Authorization: Bearer $KEY" "$1"
    else
        curl -s -m "$TIMEOUT" "$1"
    fi
}

# Resolve sample ids for the parameterised rows. Hardcoding a device or event id
# would make this contract valid only on the machine it was written on, so the
# ids are looked up at runtime and substituted into {DEVICE_ID}-style tokens. An
# id that cannot be resolved marks its rows SKIP rather than dropping them
# silently, so lost coverage is always visible rather than reading as a pass.
first_field() { grep -o "\"$2\":\"[^\"]*\"" <<< "$1" | head -1 | cut -d'"' -f4; }

DEVICE_ID="$(first_field "$(fetch_body "${BASE_URL}/api/devices?limit=1")" device_id)"
ENTITY_ID="$(first_field "$(fetch_body "${BASE_URL}/api/entities?limit=1")" entity_id)"
EVENT_ID="$(first_field "$(fetch_body "${BASE_URL}/api/v1/events?limit=1")" id)"

total=0
pass=0
skipped=0
declare -a deviations=()
declare -a skips=()

printf 'Dashboard contract sweep — %s\n' "$BASE_URL"
printf 'Auth: %s · pace: %ss/request\n\n' \
    "$([[ -n "$KEY" ]] && echo 'Bearer (client-supplied)' || echo 'none (nginx-injected)')" "$PACE"
printf '%-34s %-9s %-9s %s\n' 'ENDPOINT' 'EXPECT' 'ACTUAL' 'RESULT'
printf '%s\n' '--------------------------------------------------------------------'

first=1
while IFS=$'\t' read -r path expected kind rationale; do
    [[ -z "$path" ]] && continue
    total=$(( total + 1 ))

    path="${path//\{DEVICE_ID\}/$DEVICE_ID}"
    path="${path//\{ENTITY_ID\}/$ENTITY_ID}"
    path="${path//\{EVENT_ID\}/$EVENT_ID}"

    # An unsubstituted token means the lookup above found no sample record.
    if [[ "$path" == *'{'*'}'* ]]; then
        skipped=$(( skipped + 1 ))
        skips+=("${path} — no sample id available to substitute")
        printf '%-46s %-9s %-9s %s\n' "$path" "$expected" '-' 'SKIP'
        continue
    fi

    (( first )) && first=0 || sleep "$PACE"

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
        printf '%-46s %-9s %-9s %s\n' "$path" "$expected" "$actual" 'PASS'
    else
        deviations+=("${path} expected ${expected}, got ${actual} — ${rationale}")
        printf '%-46s %-9s %-9s %s\n' "$path" "$expected" "$actual" 'FAIL'
    fi
done <<< "$CONTRACT"

fail=$(( total - pass - skipped ))

printf '\n'
if (( fail > 0 )); then
    printf 'Deviations:\n'
    for d in "${deviations[@]}"; do
        printf '  - %s\n' "$d"
    done
    printf '\n'
fi

if (( skipped > 0 )); then
    printf 'Skipped (coverage lost, not passed):\n'
    for s in "${skips[@]}"; do
        printf '  - %s\n' "$s"
    done
    printf '\n'
fi

printf 'RESULT: %d/%d endpoints at expected status, %d deviations, %d skipped\n' \
    "$pass" "$total" "$fail" "$skipped"

(( fail == 0 ))
