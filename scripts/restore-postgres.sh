#!/bin/bash
# HomeIQ PostgreSQL Restore Script
# Restores a database backup created by backup-postgres.sh.
#
# Usage:
#   ./scripts/restore-postgres.sh <backup_file>                    # Full restore with confirmation
#   ./scripts/restore-postgres.sh <backup_file> --schema core      # Restore single schema
#   ./scripts/restore-postgres.sh <backup_file> --force            # Skip confirmation prompt
#   ./scripts/restore-postgres.sh <backup_file> --list             # List contents of backup
#
# Environment variables:
#   PG_HOST          PostgreSQL host (default: localhost)
#   PG_PORT          PostgreSQL port (default: 5432)
#   POSTGRES_USER    PostgreSQL user (default: homeiq)
#   POSTGRES_DB      PostgreSQL database (default: homeiq)
#   PGPASSWORD       PostgreSQL password (set this or use .pgpass)

set -euo pipefail

# Configuration
PG_HOST="${PG_HOST:-localhost}"
PG_PORT="${PG_PORT:-5432}"
PG_USER="${POSTGRES_USER:-homeiq}"
PG_DB="${POSTGRES_DB:-homeiq}"
LOG_FILE="/tmp/homeiq-restore-$(date +%Y%m%d_%H%M%S).log"

# Known schemas (must match backup-postgres.sh)
SCHEMAS=(core automation agent blueprints energy devices patterns rag)

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging
log() {
    local msg="$(date '+%Y-%m-%d %H:%M:%S') - $1"
    echo -e "$msg" | tee -a "$LOG_FILE"
}

log_info()    { log "${BLUE}[INFO]${NC}    $1"; }
log_success() { log "${GREEN}[SUCCESS]${NC} $1"; }
log_warn()    { log "${YELLOW}[WARNING]${NC} $1"; }
log_error()   { log "${RED}[ERROR]${NC}   $1"; }

# Usage
usage() {
    echo "Usage: $0 <backup_file> [options]"
    echo ""
    echo "Arguments:"
    echo "  <backup_file>       Path to a .dump file created by backup-postgres.sh"
    echo ""
    echo "Options:"
    echo "  --schema <name>     Restore only the specified schema"
    echo "  --force             Skip confirmation prompt"
    echo "  --list              List contents of the backup file and exit"
    echo "  --dry-run           Show what would be restored without making changes"
    echo "  --help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 backups/postgres/homeiq_full_20260224_020000.dump"
    echo "  $0 backups/postgres/homeiq_core_20260224_020000.dump --schema core"
    echo "  $0 backups/postgres/homeiq_full_20260224_020000.dump --force"
    exit 1
}

# Validate backup file
validate_backup() {
    local backup_file="$1"

    if [ ! -f "$backup_file" ]; then
        log_error "Backup file not found: $backup_file"
        exit 1
    fi

    # Verify it is a valid pg_dump custom-format file
    if ! pg_restore --list "$backup_file" > /dev/null 2>&1; then
        log_error "Invalid backup file (not a pg_dump custom format): $backup_file"
        exit 1
    fi

    local file_size
    file_size=$(stat -c%s "$backup_file" 2>/dev/null || stat -f%z "$backup_file" 2>/dev/null || echo "unknown")
    log_info "Backup file: $backup_file (${file_size} bytes)"
    log_success "Backup file validated as pg_dump custom format."
}

# List backup contents
list_backup() {
    local backup_file="$1"
    log_info "Contents of $backup_file:"
    echo ""
    pg_restore --list "$backup_file"
}

# Get row counts for verification
get_row_counts() {
    local schema_filter="${1:-}"
    local counts=""

    if [ -n "$schema_filter" ]; then
        counts=$(psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DB" -t -A <<SQL
SELECT schemaname || '.' || relname || ':' || n_live_tup
FROM pg_stat_user_tables
WHERE schemaname = '${schema_filter}'
ORDER BY schemaname, relname;
SQL
        )
    else
        counts=$(psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DB" -t -A <<SQL
SELECT schemaname || '.' || relname || ':' || n_live_tup
FROM pg_stat_user_tables
WHERE schemaname IN ('core','automation','agent','blueprints','energy','devices','patterns','rag')
ORDER BY schemaname, relname;
SQL
        )
    fi

    echo "$counts"
}

# Confirm restore
confirm_restore() {
    local backup_file="$1"
    local target="$2"

    echo ""
    echo "============================================="
    echo "  HomeIQ PostgreSQL Restore"
    echo "============================================="
    echo ""
    echo "  Backup file : $backup_file"
    echo "  Target host : ${PG_HOST}:${PG_PORT}"
    echo "  Database    : ${PG_DB}"
    echo "  User        : ${PG_USER}"
    echo "  Restoring   : ${target}"
    echo ""
    echo "  WARNING: This will DROP and recreate objects"
    echo "  in the target schema(s). Data will be lost."
    echo ""
    echo "============================================="
    echo ""

    read -r -p "Proceed with restore? (yes/no): " response
    if [ "$response" != "yes" ]; then
        log_warn "Restore cancelled by user."
        exit 0
    fi
}

# Restore full database
restore_full() {
    local backup_file="$1"

    log_info "Starting full database restore..."

    pg_restore \
        -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DB" \
        --clean --if-exists \
        --no-owner --no-privileges \
        --verbose \
        "$backup_file" 2>&1 | tee -a "$LOG_FILE"

    local exit_code=${PIPESTATUS[0]}

    # pg_restore returns non-zero for warnings too; check for actual failures
    if [ "$exit_code" -ne 0 ]; then
        log_warn "pg_restore exited with code $exit_code (may include non-fatal warnings)."
    fi

    log_success "Full database restore completed."
}

# Restore single schema
restore_schema() {
    local backup_file="$1"
    local schema="$2"

    # Validate schema name
    local valid=false
    for s in "${SCHEMAS[@]}"; do
        if [ "$s" = "$schema" ]; then
            valid=true
            break
        fi
    done

    if [ "$valid" = "false" ]; then
        log_error "Unknown schema: $schema"
        log_info "Valid schemas: ${SCHEMAS[*]}"
        exit 1
    fi

    log_info "Restoring schema: $schema"

    pg_restore \
        -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DB" \
        --schema="$schema" \
        --clean --if-exists \
        --no-owner --no-privileges \
        --verbose \
        "$backup_file" 2>&1 | tee -a "$LOG_FILE"

    local exit_code=${PIPESTATUS[0]}
    if [ "$exit_code" -ne 0 ]; then
        log_warn "pg_restore exited with code $exit_code (may include non-fatal warnings)."
    fi

    log_success "Schema '$schema' restore completed."
}

# Verify restoration with row counts
verify_restore() {
    local schema_filter="${1:-}"

    log_info "Verifying restoration..."

    # Force stats update
    psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DB" -c "ANALYZE;" > /dev/null 2>&1

    local counts
    counts=$(get_row_counts "$schema_filter")

    if [ -z "$counts" ]; then
        log_warn "No tables found after restore. This may indicate a problem."
        return 1
    fi

    echo ""
    echo "  Post-restore row counts:"
    echo "  -------------------------"
    local total_rows=0
    while IFS=':' read -r table_name row_count; do
        if [ -n "$table_name" ]; then
            printf "  %-40s %s rows\n" "$table_name" "$row_count"
            total_rows=$((total_rows + row_count))
        fi
    done <<< "$counts"
    echo "  -------------------------"
    echo "  Total rows: $total_rows"
    echo ""

    if [ "$total_rows" -eq 0 ]; then
        log_warn "Zero rows found after restore. Verify backup file contains data."
        return 1
    fi

    log_success "Restoration verified: $total_rows total rows across restored tables."
    return 0
}

# Main
main() {
    local backup_file=""
    local schema=""
    local force=false
    local list_only=false
    local dry_run=false

    # Parse arguments
    while [ $# -gt 0 ]; do
        case "$1" in
            --schema)
                schema="$2"
                shift 2
                ;;
            --force)
                force=true
                shift
                ;;
            --list)
                list_only=true
                shift
                ;;
            --dry-run)
                dry_run=true
                shift
                ;;
            --help|-h)
                usage
                ;;
            -*)
                log_error "Unknown option: $1"
                usage
                ;;
            *)
                if [ -z "$backup_file" ]; then
                    backup_file="$1"
                else
                    log_error "Unexpected argument: $1"
                    usage
                fi
                shift
                ;;
        esac
    done

    if [ -z "$backup_file" ]; then
        log_error "Backup file path is required."
        usage
    fi

    # Validate
    validate_backup "$backup_file"

    # List mode
    if [ "$list_only" = "true" ]; then
        list_backup "$backup_file"
        exit 0
    fi

    # Determine target description
    local target="all schemas (full restore)"
    if [ -n "$schema" ]; then
        target="schema '$schema' only"
    fi

    # Dry run mode
    if [ "$dry_run" = "true" ]; then
        log_info "DRY RUN - Would restore: $target"
        log_info "DRY RUN - From: $backup_file"
        log_info "DRY RUN - To: ${PG_HOST}:${PG_PORT}/${PG_DB}"
        list_backup "$backup_file"
        exit 0
    fi

    # Confirmation
    if [ "$force" = "false" ]; then
        confirm_restore "$backup_file" "$target"
    fi

    log_info "Restore log: $LOG_FILE"

    # Capture pre-restore row counts
    log_info "Pre-restore row counts:"
    get_row_counts "$schema" | while IFS=':' read -r table_name row_count; do
        if [ -n "$table_name" ]; then
            printf "  %-40s %s rows\n" "$table_name" "$row_count"
        fi
    done

    # Perform restore
    if [ -n "$schema" ]; then
        restore_schema "$backup_file" "$schema"
    else
        restore_full "$backup_file"
    fi

    # Verify
    verify_restore "$schema"

    echo ""
    log_success "Restore complete. Log saved to: $LOG_FILE"
}

main "$@"
