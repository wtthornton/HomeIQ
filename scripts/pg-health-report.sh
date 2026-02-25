#!/usr/bin/env bash
# =============================================================================
# HomeIQ PostgreSQL Health Report
# =============================================================================
#
# Connects to PostgreSQL and outputs a comprehensive health report covering:
#   - Connection count & status
#   - Table sizes per domain schema
#   - Slow queries (via pg_stat_statements)
#   - Cache hit ratio
#   - Index usage
#   - Table bloat (dead tuples)
#   - Lock contention
#   - Database-wide statistics
#
# Usage:
#   ./scripts/pg-health-report.sh
#   ./scripts/pg-health-report.sh postgresql://user:pass@host:5432/db
#   PG_HOST=postgres PG_PORT=5432 ./scripts/pg-health-report.sh
#
# Prerequisites:
#   - psql client installed (or run via: docker exec homeiq-postgres ...)
#   - pg_stat_statements extension enabled (see init-monitoring.sql)
#
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PG_URL="${1:-}"
PG_HOST="${PG_HOST:-localhost}"
PG_PORT="${PG_PORT:-5432}"
PG_USER="${POSTGRES_USER:-homeiq}"
PG_DB="${POSTGRES_DB:-homeiq}"
PGPASSWORD="${POSTGRES_PASSWORD:-homeiq-secure-2026}"
export PGPASSWORD

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

run_query() {
    local query="$1"
    if [[ -n "$PG_URL" ]]; then
        psql "$PG_URL" -t -A -F '|' -c "$query" 2>/dev/null
    else
        psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DB" \
            -t -A -F '|' -c "$query" 2>/dev/null
    fi
}

section() {
    echo ""
    echo -e "${BOLD}${BLUE}==== $1 ====${NC}"
    echo ""
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

ok() {
    echo -e "${GREEN}[OK]${NC} $1"
}

fail() {
    echo -e "${RED}[FAIL]${NC} $1"
}

# ---------------------------------------------------------------------------
# Connectivity check
# ---------------------------------------------------------------------------

echo -e "${BOLD}========================================${NC}"
echo -e "${BOLD}  HomeIQ PostgreSQL Health Report${NC}"
echo -e "${BOLD}  $(date -u +"%Y-%m-%d %H:%M:%S UTC")${NC}"
echo -e "${BOLD}========================================${NC}"

section "1. Connectivity"

if pg_version=$(run_query "SELECT version();"); then
    ok "Connected to PostgreSQL"
    echo "  Version: $pg_version"
else
    fail "Cannot connect to PostgreSQL at ${PG_HOST}:${PG_PORT}"
    echo "  Check PG_HOST, PG_PORT, POSTGRES_USER, POSTGRES_PASSWORD environment variables."
    exit 1
fi

uptime_result=$(run_query "SELECT now() - pg_postmaster_start_time() AS uptime;")
echo "  Uptime: $uptime_result"

# ---------------------------------------------------------------------------
# 2. Connection Stats
# ---------------------------------------------------------------------------

section "2. Connection Statistics"

max_conn=$(run_query "SHOW max_connections;")
active_conn=$(run_query "SELECT count(*) FROM pg_stat_activity WHERE state = 'active';")
idle_conn=$(run_query "SELECT count(*) FROM pg_stat_activity WHERE state = 'idle';")
total_conn=$(run_query "SELECT count(*) FROM pg_stat_activity;")

echo "  Max connections:    $max_conn"
echo "  Total connections:  $total_conn"
echo "  Active:             $active_conn"
echo "  Idle:               $idle_conn"

utilization=$(run_query "SELECT round(count(*)::numeric / current_setting('max_connections')::numeric * 100, 1) FROM pg_stat_activity;")
echo "  Utilization:        ${utilization}%"

if (( $(echo "$utilization > 80" | bc -l 2>/dev/null || echo 0) )); then
    warn "Connection utilization > 80% — consider increasing max_connections"
else
    ok "Connection utilization within safe range"
fi

echo ""
echo "  Connections by user/state:"
run_query "
    SELECT usename, state, count(*)
    FROM pg_stat_activity
    GROUP BY usename, state
    ORDER BY count(*) DESC;
" | while IFS='|' read -r user state cnt; do
    printf "    %-20s %-12s %s\n" "${user:-<unknown>}" "${state:-<none>}" "$cnt"
done

# ---------------------------------------------------------------------------
# 3. Schema Sizes
# ---------------------------------------------------------------------------

section "3. Domain Schema Sizes"

printf "  %-15s %-15s %s\n" "SCHEMA" "SIZE" "TABLES"
printf "  %-15s %-15s %s\n" "------" "----" "------"

for schema in core automation agent blueprints energy devices patterns rag; do
    size=$(run_query "
        SELECT COALESCE(pg_size_pretty(sum(pg_total_relation_size(quote_ident(schemaname) || '.' || quote_ident(tablename)))), '0 bytes')
        FROM pg_tables WHERE schemaname = '$schema';
    ")
    table_count=$(run_query "SELECT count(*) FROM pg_tables WHERE schemaname = '$schema';")
    printf "  %-15s %-15s %s\n" "$schema" "$size" "$table_count"
done

total_size=$(run_query "SELECT pg_size_pretty(pg_database_size('$PG_DB'));")
echo ""
echo "  Total database size: $total_size"

# ---------------------------------------------------------------------------
# 4. Table Sizes (Top 20)
# ---------------------------------------------------------------------------

section "4. Largest Tables (Top 20)"

printf "  %-20s %-30s %s\n" "SCHEMA" "TABLE" "SIZE"
printf "  %-20s %-30s %s\n" "------" "-----" "----"

run_query "
    SELECT schemaname, tablename,
           pg_size_pretty(pg_total_relation_size(quote_ident(schemaname) || '.' || quote_ident(tablename)))
    FROM pg_tables
    WHERE schemaname IN ('core', 'automation', 'agent', 'blueprints', 'energy', 'devices', 'patterns', 'rag')
    ORDER BY pg_total_relation_size(quote_ident(schemaname) || '.' || quote_ident(tablename)) DESC
    LIMIT 20;
" | while IFS='|' read -r schema table size; do
    printf "  %-20s %-30s %s\n" "$schema" "$table" "$size"
done

# ---------------------------------------------------------------------------
# 5. Cache Hit Ratio
# ---------------------------------------------------------------------------

section "5. Cache Hit Ratio"

cache_result=$(run_query "
    SELECT
        sum(heap_blks_read) AS heap_read,
        sum(heap_blks_hit) AS heap_hit,
        CASE
            WHEN sum(heap_blks_hit) + sum(heap_blks_read) = 0 THEN 1.0
            ELSE round(sum(heap_blks_hit)::numeric / (sum(heap_blks_hit) + sum(heap_blks_read))::numeric, 4)
        END AS ratio
    FROM pg_statio_user_tables;
")

IFS='|' read -r heap_read heap_hit ratio <<< "$cache_result"
echo "  Heap blocks read: ${heap_read:-0}"
echo "  Heap blocks hit:  ${heap_hit:-0}"
echo "  Hit ratio:        ${ratio:-N/A}"

if [[ -n "$ratio" ]] && (( $(echo "${ratio} < 0.9" | bc -l 2>/dev/null || echo 0) )); then
    warn "Cache hit ratio < 90% — consider increasing shared_buffers"
else
    ok "Cache hit ratio is healthy"
fi

# Index cache hit ratio
idx_cache=$(run_query "
    SELECT
        CASE
            WHEN sum(idx_blks_hit) + sum(idx_blks_read) = 0 THEN 1.0
            ELSE round(sum(idx_blks_hit)::numeric / (sum(idx_blks_hit) + sum(idx_blks_read))::numeric, 4)
        END
    FROM pg_statio_user_indexes;
")
echo "  Index hit ratio:  ${idx_cache:-N/A}"

# ---------------------------------------------------------------------------
# 6. Slow Queries (Top 10)
# ---------------------------------------------------------------------------

section "6. Slow Queries (Top 10 by mean execution time)"

has_pgss=$(run_query "SELECT count(*) FROM pg_extension WHERE extname = 'pg_stat_statements';")

if [[ "$has_pgss" == "1" ]]; then
    run_query "
        SELECT
            round(mean_exec_time::numeric, 2) AS mean_ms,
            calls,
            rows,
            left(regexp_replace(query, E'\\\\s+', ' ', 'g'), 80) AS query_preview
        FROM pg_stat_statements
        WHERE query NOT LIKE '%pg_stat%'
        ORDER BY mean_exec_time DESC
        LIMIT 10;
    " | while IFS='|' read -r mean calls rows query; do
        echo "  Mean: ${mean}ms | Calls: $calls | Rows: $rows"
        echo "    Query: $query"
        echo ""
    done

    over_500=$(run_query "
        SELECT count(*) FROM pg_stat_statements
        WHERE mean_exec_time > 500
        AND query NOT LIKE '%pg_stat%';
    ")
    if [[ "$over_500" -gt 0 ]]; then
        warn "$over_500 query pattern(s) with mean execution time > 500ms"
    else
        ok "No queries with mean execution time > 500ms"
    fi
else
    warn "pg_stat_statements extension not enabled — slow query data unavailable"
    echo "  Enable by adding to postgresql.conf: shared_preload_libraries = 'pg_stat_statements'"
fi

# ---------------------------------------------------------------------------
# 7. Index Usage
# ---------------------------------------------------------------------------

section "7. Unused or Low-Usage Indexes"

run_query "
    SELECT schemaname, tablename, indexname, idx_scan
    FROM pg_stat_user_indexes
    WHERE schemaname IN ('core', 'automation', 'agent', 'blueprints', 'energy', 'devices', 'patterns', 'rag')
    AND idx_scan < 10
    ORDER BY idx_scan ASC
    LIMIT 20;
" | while IFS='|' read -r schema table index scans; do
    echo "  $schema.$table.$index — $scans scans"
done

unused_count=$(run_query "
    SELECT count(*)
    FROM pg_stat_user_indexes
    WHERE schemaname IN ('core', 'automation', 'agent', 'blueprints', 'energy', 'devices', 'patterns', 'rag')
    AND idx_scan = 0;
")
if [[ "$unused_count" -gt 0 ]]; then
    warn "$unused_count index(es) with zero scans — candidates for removal"
else
    ok "All indexes are being used"
fi

# ---------------------------------------------------------------------------
# 8. Table Bloat
# ---------------------------------------------------------------------------

section "8. Table Bloat (Dead Tuples)"

run_query "
    SELECT schemaname, relname, n_live_tup, n_dead_tup,
           CASE WHEN n_live_tup = 0 THEN 0
                ELSE round(n_dead_tup::numeric / n_live_tup::numeric * 100, 2)
           END AS dead_pct
    FROM pg_stat_user_tables
    WHERE schemaname IN ('core', 'automation', 'agent', 'blueprints', 'energy', 'devices', 'patterns', 'rag')
    AND n_dead_tup > 0
    ORDER BY n_dead_tup DESC
    LIMIT 10;
" | while IFS='|' read -r schema table live dead pct; do
    echo "  $schema.$table — Live: $live, Dead: $dead (${pct}%)"
done

bloated=$(run_query "
    SELECT count(*)
    FROM pg_stat_user_tables
    WHERE schemaname IN ('core', 'automation', 'agent', 'blueprints', 'energy', 'devices', 'patterns', 'rag')
    AND n_live_tup > 0
    AND n_dead_tup::numeric / n_live_tup::numeric > 0.2;
")
if [[ "$bloated" -gt 0 ]]; then
    warn "$bloated table(s) with >20% dead tuples — consider running VACUUM ANALYZE"
else
    ok "Table bloat within acceptable range"
fi

# ---------------------------------------------------------------------------
# 9. Lock Contention
# ---------------------------------------------------------------------------

section "9. Lock Contention"

blocked=$(run_query "SELECT count(*) FROM pg_locks WHERE NOT granted;")
if [[ "$blocked" -gt 0 ]]; then
    warn "$blocked blocked lock request(s) detected"
    run_query "
        SELECT pid, usename, left(query, 60), state, mode
        FROM pg_locks
        JOIN pg_stat_activity USING (pid)
        WHERE NOT pg_locks.granted
        LIMIT 5;
    " | while IFS='|' read -r pid user query state mode; do
        echo "  PID: $pid | User: $user | Mode: $mode | State: $state"
        echo "    Query: $query"
    done
else
    ok "No lock contention detected"
fi

# ---------------------------------------------------------------------------
# 10. Replication / WAL
# ---------------------------------------------------------------------------

section "10. WAL & Checkpoint Stats"

wal_size=$(run_query "SELECT pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), '0/0'));")
echo "  Total WAL generated: ${wal_size:-N/A}"

checkpoint_stats=$(run_query "
    SELECT checkpoints_timed, checkpoints_req,
           round(checkpoint_write_time::numeric / 1000, 2) AS write_s,
           round(checkpoint_sync_time::numeric / 1000, 2) AS sync_s
    FROM pg_stat_bgwriter;
")
IFS='|' read -r cp_timed cp_req cp_write cp_sync <<< "$checkpoint_stats"
echo "  Timed checkpoints:    ${cp_timed:-N/A}"
echo "  Requested checkpoints: ${cp_req:-N/A}"
echo "  Checkpoint write time: ${cp_write:-N/A}s"
echo "  Checkpoint sync time:  ${cp_sync:-N/A}s"

if [[ -n "$cp_req" && -n "$cp_timed" && "$cp_timed" -gt 0 ]]; then
    req_pct=$(run_query "SELECT round(${cp_req}::numeric / (${cp_timed} + ${cp_req})::numeric * 100, 1);")
    if (( $(echo "${req_pct} > 20" | bc -l 2>/dev/null || echo 0) )); then
        warn "${req_pct}% of checkpoints are requested — consider increasing max_wal_size"
    else
        ok "Checkpoint balance is healthy (${req_pct}% requested)"
    fi
fi

# ---------------------------------------------------------------------------
# 11. Alembic Migration Status
# ---------------------------------------------------------------------------

section "11. Alembic Migration Versions"

for schema in core automation agent blueprints energy devices patterns rag; do
    version=$(run_query "
        SELECT version_num
        FROM ${schema}.alembic_version
        LIMIT 1;
    " 2>/dev/null || echo "no-table")

    if [[ "$version" == "no-table" || -z "$version" ]]; then
        echo "  $schema: (no alembic_version table)"
    else
        echo "  $schema: $version"
    fi
done

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

section "Summary"

echo -e "  Database:        $PG_DB"
echo -e "  Total size:      $total_size"
echo -e "  Connections:     $total_conn / $max_conn (${utilization}%)"
echo -e "  Cache hit ratio: ${ratio:-N/A}"
echo -e "  Blocked locks:   $blocked"
echo -e "  Uptime:          $uptime_result"
echo ""
echo -e "${BOLD}Report complete.${NC}"
