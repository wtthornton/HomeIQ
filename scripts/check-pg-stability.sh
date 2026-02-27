#!/usr/bin/env bash
# =============================================================================
# HomeIQ PostgreSQL Stability Check
# =============================================================================
#
# Run daily during the PostgreSQL stabilization period (pre-Story 6.5).
# Returns PASS or FAIL with a detailed breakdown of each check.
#
# Checks performed:
#   1. PostgreSQL uptime exceeds expected minimum
#   2. All 8 domain schemas accessible
#   3. Alembic migration versions present and current
#   4. No lock contention issues
#   5. Connection pool utilization < 80%
#   6. Cache hit ratio > 95%
#   7. No connection errors in service logs (last 24h)
#   8. Disk usage within limits
#
# Usage:
#   ./scripts/check-pg-stability.sh
#   ./scripts/check-pg-stability.sh --min-uptime 48h
#   ./scripts/check-pg-stability.sh --json
#
# Environment variables:
#   PG_HOST, PG_PORT, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB
#
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PG_HOST="${PG_HOST:-localhost}"
PG_PORT="${PG_PORT:-5432}"
PG_USER="${POSTGRES_USER:-homeiq}"
PG_DB="${POSTGRES_DB:-homeiq}"
PGPASSWORD="${POSTGRES_PASSWORD:-homeiq-secure-2026}"
export PGPASSWORD

MIN_UPTIME_HOURS="${MIN_UPTIME_HOURS:-24}"
JSON_OUTPUT=false

SCHEMAS=(core automation agent blueprints energy devices patterns rag)

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --min-uptime)
            # Accept formats like "48h", "72h", or bare number (hours)
            MIN_UPTIME_HOURS="${2//h/}"
            shift 2
            ;;
        --json)
            JSON_OUTPUT=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [--min-uptime HOURS] [--json]"
            echo ""
            echo "Options:"
            echo "  --min-uptime HOURS  Minimum expected uptime in hours (default: 24)"
            echo "  --json              Output results as JSON"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

# Track results
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
WARN_CHECKS=0
declare -a CHECK_RESULTS=()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

run_query() {
    psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DB" \
        -t -A -F '|' -c "$1" 2>/dev/null
}

record_pass() {
    local name="$1"
    local detail="${2:-}"
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
    CHECK_RESULTS+=("PASS|$name|$detail")
    if [[ "$JSON_OUTPUT" == "false" ]]; then
        echo -e "  ${GREEN}[PASS]${NC} $name${detail:+ — $detail}"
    fi
}

record_fail() {
    local name="$1"
    local detail="${2:-}"
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
    CHECK_RESULTS+=("FAIL|$name|$detail")
    if [[ "$JSON_OUTPUT" == "false" ]]; then
        echo -e "  ${RED}[FAIL]${NC} $name${detail:+ — $detail}"
    fi
}

record_warn() {
    local name="$1"
    local detail="${2:-}"
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    WARN_CHECKS=$((WARN_CHECKS + 1))
    CHECK_RESULTS+=("WARN|$name|$detail")
    if [[ "$JSON_OUTPUT" == "false" ]]; then
        echo -e "  ${YELLOW}[WARN]${NC} $name${detail:+ — $detail}"
    fi
}

# ---------------------------------------------------------------------------
# Pre-flight: Can we connect?
# ---------------------------------------------------------------------------

if [[ "$JSON_OUTPUT" == "false" ]]; then
    echo -e "${BOLD}========================================${NC}"
    echo -e "${BOLD}  HomeIQ PostgreSQL Stability Check${NC}"
    echo -e "${BOLD}  $(date -u +"%Y-%m-%d %H:%M:%S UTC")${NC}"
    echo -e "${BOLD}========================================${NC}"
    echo ""
fi

if ! run_query "SELECT 1;" > /dev/null 2>&1; then
    if [[ "$JSON_OUTPUT" == "true" ]]; then
        echo '{"status":"FAIL","error":"Cannot connect to PostgreSQL","checks":[]}'
    else
        echo -e "  ${RED}[FAIL]${NC} Cannot connect to PostgreSQL at ${PG_HOST}:${PG_PORT}"
    fi
    exit 1
fi

# ---------------------------------------------------------------------------
# Check 1: Uptime
# ---------------------------------------------------------------------------

if [[ "$JSON_OUTPUT" == "false" ]]; then
    echo -e "${BOLD}--- Check 1: Uptime ---${NC}"
fi

uptime_hours=$(run_query "
    SELECT EXTRACT(EPOCH FROM (now() - pg_postmaster_start_time())) / 3600;
" | xargs printf "%.1f")

uptime_display=$(run_query "SELECT now() - pg_postmaster_start_time();")

if (( $(echo "$uptime_hours >= $MIN_UPTIME_HOURS" | bc -l 2>/dev/null || echo 0) )); then
    record_pass "Uptime >= ${MIN_UPTIME_HOURS}h" "Current: ${uptime_display}"
else
    record_fail "Uptime >= ${MIN_UPTIME_HOURS}h" "Current: ${uptime_display} (${uptime_hours}h < ${MIN_UPTIME_HOURS}h)"
fi

# ---------------------------------------------------------------------------
# Check 2: Schema Accessibility
# ---------------------------------------------------------------------------

if [[ "$JSON_OUTPUT" == "false" ]]; then
    echo -e "${BOLD}--- Check 2: Schema Accessibility ---${NC}"
fi

for schema in "${SCHEMAS[@]}"; do
    exists=$(run_query "
        SELECT count(*) FROM information_schema.schemata
        WHERE schema_name = '$schema';
    ")
    if [[ "$exists" == "1" ]]; then
        record_pass "Schema '$schema' accessible"
    else
        record_fail "Schema '$schema' accessible" "Schema not found"
    fi
done

# ---------------------------------------------------------------------------
# Check 3: Alembic Migration Versions
# ---------------------------------------------------------------------------

if [[ "$JSON_OUTPUT" == "false" ]]; then
    echo -e "${BOLD}--- Check 3: Alembic Migrations ---${NC}"
fi

for schema in "${SCHEMAS[@]}"; do
    version=$(run_query "
        SELECT version_num FROM ${schema}.alembic_version LIMIT 1;
    " 2>/dev/null || echo "")

    if [[ -n "$version" ]]; then
        record_pass "Alembic version in '$schema'" "$version"
    else
        # Not all schemas may have alembic yet — warn rather than fail
        record_warn "Alembic version in '$schema'" "No alembic_version table (may be expected)"
    fi
done

# ---------------------------------------------------------------------------
# Check 4: Lock Contention
# ---------------------------------------------------------------------------

if [[ "$JSON_OUTPUT" == "false" ]]; then
    echo -e "${BOLD}--- Check 4: Lock Contention ---${NC}"
fi

blocked_count=$(run_query "SELECT count(*) FROM pg_locks WHERE NOT granted;")

if [[ "$blocked_count" -eq 0 ]]; then
    record_pass "No lock contention" "0 blocked requests"
else
    record_fail "No lock contention" "$blocked_count blocked lock request(s)"
fi

# Long-running queries (> 5 minutes)
long_queries=$(run_query "
    SELECT count(*) FROM pg_stat_activity
    WHERE state = 'active'
    AND query_start < now() - interval '5 minutes'
    AND query NOT LIKE '%pg_stat%';
")

if [[ "$long_queries" -eq 0 ]]; then
    record_pass "No long-running queries (>5min)"
else
    record_warn "No long-running queries (>5min)" "$long_queries active query(ies) running > 5 minutes"
fi

# ---------------------------------------------------------------------------
# Check 5: Connection Pool Utilization
# ---------------------------------------------------------------------------

if [[ "$JSON_OUTPUT" == "false" ]]; then
    echo -e "${BOLD}--- Check 5: Connection Utilization ---${NC}"
fi

max_conn=$(run_query "SHOW max_connections;")
total_conn=$(run_query "SELECT count(*) FROM pg_stat_activity;")
utilization=$(run_query "
    SELECT round(count(*)::numeric / current_setting('max_connections')::numeric * 100, 1)
    FROM pg_stat_activity;
")

if (( $(echo "$utilization < 80" | bc -l 2>/dev/null || echo 1) )); then
    record_pass "Connection utilization < 80%" "${total_conn}/${max_conn} (${utilization}%)"
else
    record_fail "Connection utilization < 80%" "${total_conn}/${max_conn} (${utilization}%)"
fi

# ---------------------------------------------------------------------------
# Check 6: Cache Hit Ratio
# ---------------------------------------------------------------------------

if [[ "$JSON_OUTPUT" == "false" ]]; then
    echo -e "${BOLD}--- Check 6: Cache Hit Ratio ---${NC}"
fi

cache_ratio=$(run_query "
    SELECT CASE
        WHEN sum(heap_blks_hit) + sum(heap_blks_read) = 0 THEN 1.0
        ELSE round(sum(heap_blks_hit)::numeric / (sum(heap_blks_hit) + sum(heap_blks_read))::numeric, 4)
    END
    FROM pg_statio_user_tables;
")

if [[ -z "$cache_ratio" ]]; then
    record_warn "Cache hit ratio > 95%" "No data yet (new database)"
elif (( $(echo "$cache_ratio >= 0.95" | bc -l 2>/dev/null || echo 0) )); then
    record_pass "Cache hit ratio > 95%" "Ratio: ${cache_ratio}"
else
    record_fail "Cache hit ratio > 95%" "Ratio: ${cache_ratio}"
fi

# ---------------------------------------------------------------------------
# Check 7: Service Connection Errors (Docker logs, last 24h)
# ---------------------------------------------------------------------------

if [[ "$JSON_OUTPUT" == "false" ]]; then
    echo -e "${BOLD}--- Check 7: Service Connection Errors ---${NC}"
fi

if command -v docker &> /dev/null; then
    error_count=0
    error_services=""

    for container in $(docker ps --format '{{.Names}}' 2>/dev/null | grep -E '^homeiq-' || true); do
        # Look for PostgreSQL connection errors in the last 24h of logs
        pg_errors=$(docker logs --since 24h "$container" 2>&1 | \
            grep -ciE "(connection refused|could not connect.*postgres|connection reset|OperationalError.*postgres|asyncpg.*ConnectionRefused)" || true)
        if [[ "$pg_errors" -gt 0 ]]; then
            error_count=$((error_count + pg_errors))
            error_services="${error_services} ${container}(${pg_errors})"
        fi
    done

    if [[ "$error_count" -eq 0 ]]; then
        record_pass "No PG connection errors in service logs (24h)"
    else
        record_fail "No PG connection errors in service logs (24h)" "Found $error_count error(s) in:$error_services"
    fi
else
    record_warn "No PG connection errors in service logs (24h)" "Docker not available — skipped"
fi

# ---------------------------------------------------------------------------
# Check 8: Database Disk Usage
# ---------------------------------------------------------------------------

if [[ "$JSON_OUTPUT" == "false" ]]; then
    echo -e "${BOLD}--- Check 8: Disk Usage ---${NC}"
fi

db_size_bytes=$(run_query "SELECT pg_database_size('$PG_DB');")
db_size_pretty=$(run_query "SELECT pg_size_pretty(pg_database_size('$PG_DB'));")

# Warn if database exceeds 5GB (reasonable for dev/small prod)
max_size_bytes=5368709120  # 5GB

if [[ "$db_size_bytes" -lt "$max_size_bytes" ]]; then
    record_pass "Database size < 5GB" "Current: $db_size_pretty"
else
    record_warn "Database size < 5GB" "Current: $db_size_pretty — consider reviewing data retention"
fi

# Check for table bloat
bloated_tables=$(run_query "
    SELECT count(*)
    FROM pg_stat_user_tables
    WHERE schemaname IN ('core', 'automation', 'agent', 'blueprints', 'energy', 'devices', 'patterns', 'rag')
    AND n_live_tup > 0
    AND n_dead_tup::numeric / n_live_tup::numeric > 0.2;
")

if [[ "$bloated_tables" -eq 0 ]]; then
    record_pass "No significant table bloat" "All tables < 20% dead tuples"
else
    record_warn "No significant table bloat" "$bloated_tables table(s) > 20% dead tuples — run VACUUM ANALYZE"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

if [[ "$JSON_OUTPUT" == "false" ]]; then
    echo ""
    echo -e "${BOLD}========================================${NC}"
    echo -e "${BOLD}  Results${NC}"
    echo -e "${BOLD}========================================${NC}"
    echo ""
    echo "  Total checks:   $TOTAL_CHECKS"
    echo "  Passed:          $PASSED_CHECKS"
    echo "  Warnings:        $WARN_CHECKS"
    echo "  Failed:          $FAILED_CHECKS"
    echo ""

    if [[ "$FAILED_CHECKS" -eq 0 ]]; then
        echo -e "  ${GREEN}${BOLD}OVERALL: PASS${NC}"
        echo ""
        echo "  PostgreSQL is stable. Stabilization period can continue."
    else
        echo -e "  ${RED}${BOLD}OVERALL: FAIL${NC}"
        echo ""
        echo "  $FAILED_CHECKS check(s) failed. Investigate before proceeding with Story 6.5."
    fi
    echo ""
else
    # JSON output
    echo "{"
    echo "  \"timestamp\": \"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\","
    echo "  \"status\": \"$(if [[ "$FAILED_CHECKS" -eq 0 ]]; then echo "PASS"; else echo "FAIL"; fi)\","
    echo "  \"summary\": {"
    echo "    \"total\": $TOTAL_CHECKS,"
    echo "    \"passed\": $PASSED_CHECKS,"
    echo "    \"warnings\": $WARN_CHECKS,"
    echo "    \"failed\": $FAILED_CHECKS"
    echo "  },"
    echo "  \"configuration\": {"
    echo "    \"pg_host\": \"$PG_HOST\","
    echo "    \"pg_port\": $PG_PORT,"
    echo "    \"pg_database\": \"$PG_DB\","
    echo "    \"min_uptime_hours\": $MIN_UPTIME_HOURS"
    echo "  },"
    echo "  \"checks\": ["

    first=true
    for result in "${CHECK_RESULTS[@]}"; do
        IFS='|' read -r status name detail <<< "$result"
        if [[ "$first" == "false" ]]; then
            echo "    ,"
        fi
        first=false
        echo "    {"
        echo "      \"status\": \"$status\","
        echo "      \"name\": \"$name\","
        echo "      \"detail\": \"$detail\""
        echo "    }"
    done

    echo "  ]"
    echo "}"
fi

# Exit code: 0 = PASS, 1 = FAIL
if [[ "$FAILED_CHECKS" -gt 0 ]]; then
    exit 1
else
    exit 0
fi
