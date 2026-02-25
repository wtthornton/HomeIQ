-- HomeIQ PostgreSQL Monitoring Setup
-- Run automatically on first boot via /docker-entrypoint-initdb.d/02-monitoring.sql
-- Depends on: 01-schemas.sql (domain schemas must exist first)
--
-- All statements are idempotent (CREATE IF NOT EXISTS / CREATE OR REPLACE).

-- =============================================================================
-- Enable pg_stat_statements extension
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- =============================================================================
-- Monitoring schema
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS monitoring;

-- =============================================================================
-- View: Active connections per database / user / state
-- =============================================================================

CREATE OR REPLACE VIEW monitoring.active_connections AS
SELECT
    datname,
    usename,
    state,
    count(*) AS connection_count
FROM pg_stat_activity
GROUP BY datname, usename, state;

-- =============================================================================
-- View: Table sizes across all domain schemas
-- =============================================================================

CREATE OR REPLACE VIEW monitoring.table_sizes AS
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(quote_ident(schemaname) || '.' || quote_ident(tablename))) AS total_size,
    pg_total_relation_size(quote_ident(schemaname) || '.' || quote_ident(tablename)) AS total_bytes
FROM pg_tables
WHERE schemaname IN ('core', 'automation', 'agent', 'blueprints', 'energy', 'devices', 'patterns', 'rag')
ORDER BY total_bytes DESC;

-- =============================================================================
-- View: Slow queries (top 50 by mean execution time)
-- =============================================================================

CREATE OR REPLACE VIEW monitoring.slow_queries AS
SELECT
    query,
    calls,
    round(total_exec_time::numeric, 2) AS total_exec_time_ms,
    round(mean_exec_time::numeric, 2) AS mean_exec_time_ms,
    round(min_exec_time::numeric, 2) AS min_exec_time_ms,
    round(max_exec_time::numeric, 2) AS max_exec_time_ms,
    rows
FROM pg_stat_statements
WHERE query NOT LIKE '%pg_stat%'
ORDER BY mean_exec_time DESC
LIMIT 50;

-- =============================================================================
-- View: Index usage across domain schemas (low-scan indices may be unused)
-- =============================================================================

CREATE OR REPLACE VIEW monitoring.index_usage AS
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname IN ('core', 'automation', 'agent', 'blueprints', 'energy', 'devices', 'patterns', 'rag')
ORDER BY idx_scan ASC;

-- =============================================================================
-- View: Cache hit ratio (heap reads vs hits)
-- =============================================================================

CREATE OR REPLACE VIEW monitoring.cache_stats AS
SELECT
    sum(heap_blks_read) AS heap_read,
    sum(heap_blks_hit) AS heap_hit,
    CASE
        WHEN sum(heap_blks_hit) + sum(heap_blks_read) = 0 THEN 1.0
        ELSE round(sum(heap_blks_hit)::numeric / (sum(heap_blks_hit) + sum(heap_blks_read))::numeric, 4)
    END AS ratio
FROM pg_statio_user_tables;

-- =============================================================================
-- View: Table bloat estimate (dead tuples waiting for vacuum)
-- =============================================================================

CREATE OR REPLACE VIEW monitoring.table_bloat AS
SELECT
    schemaname,
    relname AS tablename,
    n_live_tup,
    n_dead_tup,
    CASE
        WHEN n_live_tup = 0 THEN 0.0
        ELSE round(n_dead_tup::numeric / n_live_tup::numeric * 100, 2)
    END AS dead_pct,
    last_vacuum,
    last_autovacuum,
    last_analyze,
    last_autoanalyze
FROM pg_stat_user_tables
WHERE schemaname IN ('core', 'automation', 'agent', 'blueprints', 'energy', 'devices', 'patterns', 'rag')
ORDER BY n_dead_tup DESC;

-- =============================================================================
-- View: Lock contention (currently held locks)
-- =============================================================================

CREATE OR REPLACE VIEW monitoring.lock_contention AS
SELECT
    pg_stat_activity.pid,
    pg_stat_activity.usename,
    pg_stat_activity.query,
    pg_stat_activity.state,
    pg_locks.locktype,
    pg_locks.mode,
    pg_locks.granted,
    pg_stat_activity.query_start,
    now() - pg_stat_activity.query_start AS duration
FROM pg_locks
JOIN pg_stat_activity ON pg_locks.pid = pg_stat_activity.pid
WHERE NOT pg_locks.granted
ORDER BY pg_stat_activity.query_start;

-- =============================================================================
-- View: Database-wide statistics summary
-- =============================================================================

CREATE OR REPLACE VIEW monitoring.database_stats AS
SELECT
    datname,
    numbackends AS active_connections,
    xact_commit AS transactions_committed,
    xact_rollback AS transactions_rolled_back,
    blks_read,
    blks_hit,
    CASE
        WHEN blks_hit + blks_read = 0 THEN 1.0
        ELSE round(blks_hit::numeric / (blks_hit + blks_read)::numeric, 4)
    END AS cache_hit_ratio,
    tup_returned,
    tup_fetched,
    tup_inserted,
    tup_updated,
    tup_deleted,
    temp_files,
    pg_size_pretty(temp_bytes) AS temp_bytes,
    deadlocks
FROM pg_stat_database
WHERE datname = 'homeiq';

-- =============================================================================
-- Grant read access to monitoring schema
-- =============================================================================

GRANT USAGE ON SCHEMA monitoring TO PUBLIC;
GRANT SELECT ON ALL TABLES IN SCHEMA monitoring TO PUBLIC;
