#!/bin/bash
# HomeIQ Backup/Restore Integration Test
# Spins up a temporary PostgreSQL container, seeds data, backs up, wipes,
# restores, and validates that all data matches the original.
#
# Usage:
#   ./scripts/test-backup-restore.sh
#
# Requirements:
#   - Docker must be running
#   - No port conflict on 15432 (test container uses this port)
#
# Exit codes:
#   0 - All tests passed
#   1 - Test failure

set -euo pipefail

# Test configuration
TEST_CONTAINER="homeiq-backup-test-pg"
TEST_PORT=15432
TEST_USER="homeiq"
TEST_PASSWORD="testpass"
TEST_DB="homeiq"
TEST_BACKUP_DIR="/tmp/homeiq-backup-test-$$"
PG_IMAGE="postgres:17-alpine"

# Known schemas (must match backup-postgres.sh)
SCHEMAS=(core automation agent blueprints energy devices patterns rag)

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PASS_COUNT=0
FAIL_COUNT=0

log_info()    { echo -e "${BLUE}[INFO]${NC}    $1"; }
log_success() { echo -e "${GREEN}[PASS]${NC}    $1"; PASS_COUNT=$((PASS_COUNT + 1)); }
log_fail()    { echo -e "${RED}[FAIL]${NC}    $1"; FAIL_COUNT=$((FAIL_COUNT + 1)); }
log_warn()    { echo -e "${YELLOW}[WARN]${NC}    $1"; }

# Cleanup function (runs on exit)
cleanup() {
    log_info "Cleaning up test resources..."

    # Stop and remove test container
    docker rm -f "$TEST_CONTAINER" > /dev/null 2>&1 || true

    # Remove test backup directory
    rm -rf "$TEST_BACKUP_DIR" 2>/dev/null || true

    log_info "Cleanup complete."
}
trap cleanup EXIT

# Wait for PostgreSQL to be ready
wait_for_pg() {
    local max_attempts=30
    local attempt=1
    log_info "Waiting for PostgreSQL to be ready..."
    while [ "$attempt" -le "$max_attempts" ]; do
        if docker exec "$TEST_CONTAINER" pg_isready -U "$TEST_USER" -d "$TEST_DB" > /dev/null 2>&1; then
            log_info "PostgreSQL is ready (attempt $attempt)."
            return 0
        fi
        sleep 1
        attempt=$((attempt + 1))
    done
    log_fail "PostgreSQL did not become ready in time."
    return 1
}

# Run SQL in the test container
run_sql() {
    docker exec -e PGPASSWORD="$TEST_PASSWORD" "$TEST_CONTAINER" \
        psql -h localhost -U "$TEST_USER" -d "$TEST_DB" -t -A -c "$1"
}

# Run SQL from file
run_sql_file() {
    docker exec -i -e PGPASSWORD="$TEST_PASSWORD" "$TEST_CONTAINER" \
        psql -h localhost -U "$TEST_USER" -d "$TEST_DB" -t -A < "$1"
}

# ===== STEP 1: Create test PostgreSQL container =====
step_create_container() {
    log_info "Step 1: Creating test PostgreSQL container..."

    # Remove any existing test container
    docker rm -f "$TEST_CONTAINER" > /dev/null 2>&1 || true

    docker run -d \
        --name "$TEST_CONTAINER" \
        -e POSTGRES_USER="$TEST_USER" \
        -e POSTGRES_PASSWORD="$TEST_PASSWORD" \
        -e POSTGRES_DB="$TEST_DB" \
        -p "${TEST_PORT}:5432" \
        "$PG_IMAGE"

    wait_for_pg
    log_success "Test PostgreSQL container created and ready."
}

# ===== STEP 2: Create schemas and seed test data =====
step_seed_data() {
    log_info "Step 2: Creating schemas and seeding test data..."

    # Create schemas
    for schema in "${SCHEMAS[@]}"; do
        run_sql "CREATE SCHEMA IF NOT EXISTS $schema;"
    done

    # Seed test data in each schema
    run_sql "
        CREATE TABLE core.services (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            port INTEGER NOT NULL,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT NOW()
        );
        INSERT INTO core.services (name, port) VALUES
            ('websocket-ingestion', 8001),
            ('data-api', 8006),
            ('admin-api', 8004),
            ('health-dashboard', 3000);
    "

    run_sql "
        CREATE TABLE automation.rules (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            trigger_type TEXT NOT NULL,
            enabled BOOLEAN DEFAULT true,
            created_at TIMESTAMP DEFAULT NOW()
        );
        INSERT INTO automation.rules (name, trigger_type) VALUES
            ('lights_on_motion', 'state_changed'),
            ('thermostat_schedule', 'time'),
            ('security_arm', 'state_changed');
    "

    run_sql "
        CREATE TABLE agent.sessions (
            id SERIAL PRIMARY KEY,
            agent_name TEXT NOT NULL,
            user_query TEXT NOT NULL,
            response TEXT,
            score FLOAT,
            created_at TIMESTAMP DEFAULT NOW()
        );
        INSERT INTO agent.sessions (agent_name, user_query, response, score) VALUES
            ('ha-ai-agent', 'Turn on kitchen lights', 'Done', 0.95),
            ('proactive-agent', 'Energy suggestion', 'Reduce heating', 0.88);
    "

    run_sql "
        CREATE TABLE energy.readings (
            id SERIAL PRIMARY KEY,
            meter_id TEXT NOT NULL,
            value_kwh FLOAT NOT NULL,
            timestamp TIMESTAMP DEFAULT NOW()
        );
        INSERT INTO energy.readings (meter_id, value_kwh) VALUES
            ('meter_001', 12.5),
            ('meter_001', 13.2),
            ('meter_002', 8.7);
    "

    run_sql "
        CREATE TABLE devices.registry (
            id SERIAL PRIMARY KEY,
            entity_id TEXT NOT NULL UNIQUE,
            device_type TEXT NOT NULL,
            area TEXT,
            last_seen TIMESTAMP DEFAULT NOW()
        );
        INSERT INTO devices.registry (entity_id, device_type, area) VALUES
            ('light.kitchen', 'light', 'kitchen'),
            ('sensor.temperature_living', 'sensor', 'living_room'),
            ('switch.office_fan', 'switch', 'office');
    "

    # Capture expected row counts
    log_success "Test data seeded across 5 schemas."
}

# ===== STEP 3: Capture original row counts =====
declare -A ORIGINAL_COUNTS

step_capture_counts() {
    log_info "Step 3: Capturing original row counts..."

    ORIGINAL_COUNTS[core.services]=$(run_sql "SELECT COUNT(*) FROM core.services;")
    ORIGINAL_COUNTS[automation.rules]=$(run_sql "SELECT COUNT(*) FROM automation.rules;")
    ORIGINAL_COUNTS[agent.sessions]=$(run_sql "SELECT COUNT(*) FROM agent.sessions;")
    ORIGINAL_COUNTS[energy.readings]=$(run_sql "SELECT COUNT(*) FROM energy.readings;")
    ORIGINAL_COUNTS[devices.registry]=$(run_sql "SELECT COUNT(*) FROM devices.registry;")

    for table in "${!ORIGINAL_COUNTS[@]}"; do
        log_info "  $table: ${ORIGINAL_COUNTS[$table]} rows"
    done

    log_success "Original row counts captured."
}

# ===== STEP 4: Run backup =====
step_run_backup() {
    log_info "Step 4: Running backup..."

    mkdir -p "$TEST_BACKUP_DIR"

    # Run backup against test container using the project backup script
    PG_HOST=localhost \
    PG_PORT=$TEST_PORT \
    POSTGRES_USER=$TEST_USER \
    PGPASSWORD=$TEST_PASSWORD \
    POSTGRES_DB=$TEST_DB \
    BACKUP_DIR=$TEST_BACKUP_DIR \
        bash "$(dirname "$0")/backup-postgres.sh"

    # Verify backup files exist
    local full_count
    full_count=$(find "$TEST_BACKUP_DIR" -name "homeiq_full_*.dump" | wc -l)
    if [ "$full_count" -eq 0 ]; then
        log_fail "No full backup file found."
        return 1
    fi

    local schema_count
    schema_count=$(find "$TEST_BACKUP_DIR" -name "homeiq_*.dump" | wc -l)
    log_info "  Backup files created: $schema_count"

    log_success "Backup completed successfully."
}

# ===== STEP 5: Wipe the database =====
step_wipe_database() {
    log_info "Step 5: Wiping database to simulate data loss..."

    for schema in "${SCHEMAS[@]}"; do
        run_sql "DROP SCHEMA IF EXISTS $schema CASCADE;" || true
    done

    # Recreate empty schemas (restore needs them to exist for --clean)
    for schema in "${SCHEMAS[@]}"; do
        run_sql "CREATE SCHEMA IF NOT EXISTS $schema;"
    done

    # Verify tables are gone
    local table_count
    table_count=$(run_sql "SELECT COUNT(*) FROM pg_stat_user_tables WHERE schemaname IN ('core','automation','agent','blueprints','energy','devices','patterns','rag');")

    if [ "$table_count" -eq 0 ]; then
        log_success "Database wiped (0 tables remain)."
    else
        log_fail "Database wipe incomplete ($table_count tables remain)."
    fi
}

# ===== STEP 6: Run restore =====
step_run_restore() {
    log_info "Step 6: Running restore..."

    local backup_file
    backup_file=$(find "$TEST_BACKUP_DIR" -name "homeiq_full_*.dump" -type f | head -1)

    if [ -z "$backup_file" ]; then
        log_fail "No full backup file found for restore."
        return 1
    fi

    log_info "  Restoring from: $backup_file"

    PG_HOST=localhost \
    PG_PORT=$TEST_PORT \
    POSTGRES_USER=$TEST_USER \
    PGPASSWORD=$TEST_PASSWORD \
    POSTGRES_DB=$TEST_DB \
        bash "$(dirname "$0")/restore-postgres.sh" "$backup_file" --force

    log_success "Restore completed."
}

# ===== STEP 7: Validate data matches =====
step_validate_data() {
    log_info "Step 7: Validating restored data matches original..."

    # Force ANALYZE for accurate counts
    run_sql "ANALYZE;"

    local all_match=true

    for table in "${!ORIGINAL_COUNTS[@]}"; do
        local expected="${ORIGINAL_COUNTS[$table]}"
        local actual
        actual=$(run_sql "SELECT COUNT(*) FROM $table;" 2>/dev/null || echo "ERROR")

        if [ "$actual" = "$expected" ]; then
            log_success "$table: $actual rows (matches original)"
        else
            log_fail "$table: expected $expected rows, got $actual"
            all_match=false
        fi
    done

    # Spot-check specific data
    local service_name
    service_name=$(run_sql "SELECT name FROM core.services WHERE port = 8001;")
    if [ "$service_name" = "websocket-ingestion" ]; then
        log_success "Spot check: core.services data integrity verified"
    else
        log_fail "Spot check: Expected 'websocket-ingestion' but got '$service_name'"
    fi

    local rule_count
    rule_count=$(run_sql "SELECT COUNT(*) FROM automation.rules WHERE enabled = true;")
    if [ "$rule_count" = "3" ]; then
        log_success "Spot check: automation.rules boolean data preserved"
    else
        log_fail "Spot check: Expected 3 enabled rules, got $rule_count"
    fi

    local score
    score=$(run_sql "SELECT score FROM agent.sessions WHERE agent_name = 'ha-ai-agent';")
    if [ "$score" = "0.95" ]; then
        log_success "Spot check: agent.sessions float precision preserved"
    else
        log_fail "Spot check: Expected score 0.95, got $score"
    fi

    if [ "$all_match" = "true" ]; then
        log_success "All row counts match original data."
    fi
}

# ===== STEP 8: Test per-schema restore =====
step_test_schema_restore() {
    log_info "Step 8: Testing per-schema restore..."

    # Wipe just the energy schema
    run_sql "DROP SCHEMA IF EXISTS energy CASCADE;"
    run_sql "CREATE SCHEMA IF NOT EXISTS energy;"

    # Verify energy tables are gone
    local pre_count
    pre_count=$(run_sql "SELECT COUNT(*) FROM pg_tables WHERE schemaname = 'energy';")
    if [ "$pre_count" -ne 0 ]; then
        log_fail "Energy schema was not properly wiped."
        return 1
    fi

    # Find the energy-specific backup
    local energy_backup
    energy_backup=$(find "$TEST_BACKUP_DIR" -name "homeiq_energy_*.dump" -type f | head -1)

    if [ -z "$energy_backup" ]; then
        log_warn "No per-schema energy backup found. Skipping per-schema test."
        return 0
    fi

    PG_HOST=localhost \
    PG_PORT=$TEST_PORT \
    POSTGRES_USER=$TEST_USER \
    PGPASSWORD=$TEST_PASSWORD \
    POSTGRES_DB=$TEST_DB \
        bash "$(dirname "$0")/restore-postgres.sh" "$energy_backup" --schema energy --force

    run_sql "ANALYZE;"

    local energy_count
    energy_count=$(run_sql "SELECT COUNT(*) FROM energy.readings;" 2>/dev/null || echo "ERROR")

    if [ "$energy_count" = "${ORIGINAL_COUNTS[energy.readings]}" ]; then
        log_success "Per-schema restore: energy.readings has ${energy_count} rows (matches)"
    else
        log_fail "Per-schema restore: expected ${ORIGINAL_COUNTS[energy.readings]} rows, got $energy_count"
    fi

    # Verify other schemas were not affected
    local core_count
    core_count=$(run_sql "SELECT COUNT(*) FROM core.services;" 2>/dev/null || echo "ERROR")
    if [ "$core_count" = "${ORIGINAL_COUNTS[core.services]}" ]; then
        log_success "Per-schema restore: core.services unaffected (${core_count} rows)"
    else
        log_fail "Per-schema restore: core.services was modified (expected ${ORIGINAL_COUNTS[core.services]}, got $core_count)"
    fi
}

# ===== Main =====
main() {
    echo "============================================="
    echo "  HomeIQ Backup/Restore Integration Test"
    echo "============================================="
    echo ""

    step_create_container
    step_seed_data
    step_capture_counts
    step_run_backup
    step_wipe_database
    step_run_restore
    step_validate_data
    step_test_schema_restore

    echo ""
    echo "============================================="
    echo "  Test Results"
    echo "============================================="
    echo -e "  ${GREEN}Passed:${NC} $PASS_COUNT"
    echo -e "  ${RED}Failed:${NC} $FAIL_COUNT"
    echo "============================================="

    if [ "$FAIL_COUNT" -gt 0 ]; then
        echo -e "${RED}SOME TESTS FAILED${NC}"
        exit 1
    else
        echo -e "${GREEN}ALL TESTS PASSED${NC}"
        exit 0
    fi
}

main "$@"
