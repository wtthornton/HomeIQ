#!/bin/bash
# HomeIQ SQLite-to-PostgreSQL Migration Validation Orchestrator
#
# Runs schema structure checks first, then data integrity validation.
# Returns non-zero if any validation fails.
#
# Usage:
#   ./scripts/validate-migration/run_validation.sh
#
# Environment variables:
#   POSTGRES_URL  - PostgreSQL URL (default: postgresql+asyncpg://homeiq:homeiq-secure-2026@localhost:5432/homeiq)
#   SQLITE_DIR    - Directory with SQLite files (default: ./data/)
#   SCHEMAS       - Space-separated list of schemas (default: all)
#   DRY_RUN       - Set to "1" for dry run mode

set -euo pipefail

# --- Configuration ---
POSTGRES_URL="${POSTGRES_URL:-postgresql+asyncpg://homeiq:homeiq-secure-2026@localhost:5432/homeiq}"
SQLITE_DIR="${SQLITE_DIR:-./data/}"
SCHEMAS="${SCHEMAS:-}"
DRY_RUN="${DRY_RUN:-0}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPORT_DIR="${SCRIPT_DIR}/reports"

# --- Helpers ---
timestamp() {
    date "+%Y-%m-%d %H:%M:%S"
}

log_info() {
    echo "[$(timestamp)] INFO  $*"
}

log_error() {
    echo "[$(timestamp)] ERROR $*" >&2
}

log_success() {
    echo "[$(timestamp)] PASS  $*"
}

log_fail() {
    echo "[$(timestamp)] FAIL  $*" >&2
}

# --- Banner ---
echo ""
echo "=============================================="
echo "  HomeIQ Migration Validation"
echo "  $(timestamp)"
echo "=============================================="
echo ""
log_info "PostgreSQL: ${POSTGRES_URL##*@}"
log_info "SQLite dir: ${SQLITE_DIR}"
if [ -n "${SCHEMAS}" ]; then
    log_info "Schemas:    ${SCHEMAS}"
else
    log_info "Schemas:    all"
fi
echo ""

# Build schema args
SCHEMA_ARGS=""
if [ -n "${SCHEMAS}" ]; then
    SCHEMA_ARGS="--schemas ${SCHEMAS}"
fi

# Build dry-run arg
DRY_RUN_ARG=""
if [ "${DRY_RUN}" = "1" ]; then
    DRY_RUN_ARG="--dry-run"
    log_info "DRY RUN MODE - no database connections will be made"
    echo ""
fi

# Create reports directory
mkdir -p "${REPORT_DIR}"

EXIT_CODE=0

# ---------------------------------------------------------------------------
# Stage 1: Schema Structure Validation
# ---------------------------------------------------------------------------
echo "----------------------------------------------"
echo "  Stage 1: Schema Structure Check"
echo "----------------------------------------------"
echo ""

SCHEMA_EXIT=0
python "${SCRIPT_DIR}/check_schemas.py" \
    --postgres-url "${POSTGRES_URL}" \
    ${SCHEMA_ARGS} \
    ${DRY_RUN_ARG} || SCHEMA_EXIT=$?

if [ "${SCHEMA_EXIT}" -ne 0 ]; then
    log_fail "Schema structure check FAILED (exit code ${SCHEMA_EXIT})"
    log_error "Fix schema issues before running data validation."
    EXIT_CODE=1

    if [ "${DRY_RUN}" != "1" ]; then
        echo ""
        echo "----------------------------------------------"
        echo "  Skipping Stage 2 (schema check failed)"
        echo "----------------------------------------------"
        echo ""
        echo "=============================================="
        echo "  RESULT: FAIL"
        echo "  Schema structure check did not pass."
        echo "  Data validation was skipped."
        echo "=============================================="
        exit "${EXIT_CODE}"
    fi
else
    log_success "Schema structure check passed"
fi

echo ""

# ---------------------------------------------------------------------------
# Stage 2: Data Integrity Validation
# ---------------------------------------------------------------------------
echo "----------------------------------------------"
echo "  Stage 2: Data Integrity Validation"
echo "----------------------------------------------"
echo ""

REPORT_FILE="${REPORT_DIR}/validation-$(date +%Y%m%d-%H%M%S).json"

DATA_EXIT=0
python "${SCRIPT_DIR}/validate_data.py" \
    --postgres-url "${POSTGRES_URL}" \
    --sqlite-dir "${SQLITE_DIR}" \
    --output "${REPORT_FILE}" \
    ${SCHEMA_ARGS} \
    ${DRY_RUN_ARG} || DATA_EXIT=$?

if [ "${DATA_EXIT}" -ne 0 ]; then
    log_fail "Data integrity validation FAILED (exit code ${DATA_EXIT})"
    EXIT_CODE=1
else
    log_success "Data integrity validation passed"
fi

if [ "${DRY_RUN}" != "1" ] && [ -f "${REPORT_FILE}" ]; then
    log_info "Report saved to: ${REPORT_FILE}"
fi

echo ""

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo "=============================================="
if [ "${EXIT_CODE}" -eq 0 ]; then
    echo "  RESULT: PASS"
    echo "  All validation checks passed."
else
    echo "  RESULT: FAIL"
    echo "  One or more validation stages failed."
    echo "  Review the output above for details."
    if [ -f "${REPORT_FILE}" ]; then
        echo "  JSON report: ${REPORT_FILE}"
    fi
fi
echo "=============================================="
echo ""

exit "${EXIT_CODE}"
