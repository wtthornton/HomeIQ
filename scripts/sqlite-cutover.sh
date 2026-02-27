#!/usr/bin/env bash
# =============================================================================
# HomeIQ SQLite Cutover — Dry-Run Report
# =============================================================================
#
# Story 6.5 preparation script. Produces a report of everything that will
# change on cutover day. Does NOT make any modifications.
#
# Prerequisites:
#   - PostgreSQL stability check must pass (check-pg-stability.sh)
#
# Usage:
#   ./scripts/sqlite-cutover.sh
#   ./scripts/sqlite-cutover.sh --skip-stability   # skip PG stability check
#   ./scripts/sqlite-cutover.sh --json              # JSON output
#
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SKIP_STABILITY=false
JSON_OUTPUT=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-stability)
            SKIP_STABILITY=true
            shift
            ;;
        --json)
            JSON_OUTPUT=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [--skip-stability] [--json]"
            echo ""
            echo "Dry-run report for SQLite cutover (Story 6.5)."
            echo "Does NOT make any changes."
            echo ""
            echo "Options:"
            echo "  --skip-stability  Skip PostgreSQL stability check"
            echo "  --json            Output as JSON"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Colors (only for non-JSON)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ---------------------------------------------------------------------------
# Step 0: PostgreSQL stability gate
# ---------------------------------------------------------------------------

if [[ "$JSON_OUTPUT" == "false" ]]; then
    echo -e "${BOLD}============================================================${NC}"
    echo -e "${BOLD}  HomeIQ SQLite Cutover — Dry-Run Report${NC}"
    echo -e "${BOLD}  $(date -u +"%Y-%m-%d %H:%M:%S UTC")${NC}"
    echo -e "${BOLD}============================================================${NC}"
    echo ""
fi

if [[ "$SKIP_STABILITY" == "false" ]]; then
    if [[ "$JSON_OUTPUT" == "false" ]]; then
        echo -e "${BOLD}--- Step 0: PostgreSQL Stability Gate ---${NC}"
    fi

    STABILITY_SCRIPT="$SCRIPT_DIR/check-pg-stability.sh"
    if [[ -f "$STABILITY_SCRIPT" ]]; then
        if "$STABILITY_SCRIPT" --json > /dev/null 2>&1; then
            if [[ "$JSON_OUTPUT" == "false" ]]; then
                echo -e "  ${GREEN}[PASS]${NC} PostgreSQL stability check passed"
                echo ""
            fi
        else
            if [[ "$JSON_OUTPUT" == "false" ]]; then
                echo -e "  ${RED}[FAIL]${NC} PostgreSQL stability check FAILED"
                echo -e "  ${RED}        Cutover should NOT proceed until stability passes.${NC}"
                echo -e "  ${RED}        Run: ./scripts/check-pg-stability.sh for details.${NC}"
            else
                echo '{"status":"BLOCKED","reason":"PostgreSQL stability check failed"}'
            fi
            exit 1
        fi
    else
        if [[ "$JSON_OUTPUT" == "false" ]]; then
            echo -e "  ${YELLOW}[WARN]${NC} Stability script not found at $STABILITY_SCRIPT"
            echo -e "         Proceeding without stability verification."
            echo ""
        fi
    fi
fi

# ---------------------------------------------------------------------------
# Step 1: Database files with SQLite fallback code to modify
# ---------------------------------------------------------------------------

if [[ "$JSON_OUTPUT" == "false" ]]; then
    echo -e "${BOLD}--- Step 1: Database Files with SQLite Fallback Code ---${NC}"
    echo -e "  These files contain dual SQLite/PostgreSQL code."
    echo -e "  On cutover day, the SQLite branches will be removed."
    echo ""
fi

DATABASE_FILES=(
    "domains/core-platform/data-api/src/database.py"
    "domains/automation-core/ai-automation-service-new/src/database/__init__.py"
    "domains/automation-core/ha-ai-agent-service/src/database.py"
    "domains/automation-core/ai-query-service/src/database/__init__.py"
    "domains/ml-engine/ai-training-service/src/database/__init__.py"
    "domains/ml-engine/rag-service/src/database/session.py"
    "domains/ml-engine/device-intelligence-service/src/core/database.py"
    "domains/energy-analytics/proactive-agent-service/src/database.py"
    "domains/blueprints/automation-miner/src/miner/database.py"
    "domains/blueprints/blueprint-index/src/database.py"
    "domains/blueprints/blueprint-suggestion-service/src/database.py"
    "domains/device-management/ha-setup-service/src/database.py"
    "domains/pattern-analysis/ai-pattern-service/src/database/__init__.py"
    "domains/pattern-analysis/api-automation-edge/src/registry/spec_registry.py"
)

DB_FILE_COUNT=0
for f in "${DATABASE_FILES[@]}"; do
    full_path="$PROJECT_ROOT/$f"
    if [[ -f "$full_path" ]]; then
        DB_FILE_COUNT=$((DB_FILE_COUNT + 1))
        if [[ "$JSON_OUTPUT" == "false" ]]; then
            sqlite_lines=$(grep -c -iE "sqlite|aiosqlite|PRAGMA|_is_postgres.*False|StaticPool" "$full_path" 2>/dev/null || echo "0")
            echo -e "  ${CYAN}[$DB_FILE_COUNT]${NC} $f  (${sqlite_lines} SQLite-related lines)"
        fi
    else
        if [[ "$JSON_OUTPUT" == "false" ]]; then
            echo -e "  ${YELLOW}[MISSING]${NC} $f"
        fi
    fi
done

if [[ "$JSON_OUTPUT" == "false" ]]; then
    echo ""
    echo -e "  Total database files to modify: ${BOLD}$DB_FILE_COUNT${NC}"
    echo ""
fi

# ---------------------------------------------------------------------------
# Step 2: Compose file environment variables to remove
# ---------------------------------------------------------------------------

if [[ "$JSON_OUTPUT" == "false" ]]; then
    echo -e "${BOLD}--- Step 2: Compose Environment Variables to Remove ---${NC}"
    echo -e "  SQLite-related env vars in compose files."
    echo ""
fi

COMPOSE_CHANGES=()
while IFS= read -r line; do
    COMPOSE_CHANGES+=("$line")
done < <(grep -rn -iE "sqlite|SQLITE_" "$PROJECT_ROOT/domains/"*/compose.yml 2>/dev/null | \
    grep -vE "^\s*#" || true)

if [[ "$JSON_OUTPUT" == "false" ]]; then
    for change in "${COMPOSE_CHANGES[@]}"; do
        # Strip project root for readability
        display="${change#"$PROJECT_ROOT/"}"
        echo -e "  ${YELLOW}-${NC} $display"
    done
    echo ""
    echo -e "  Total env var lines to review: ${BOLD}${#COMPOSE_CHANGES[@]}${NC}"
    echo ""
fi

# Also find the sqlite-data volume
if [[ "$JSON_OUTPUT" == "false" ]]; then
    echo -e "${BOLD}--- Step 2b: Docker Volumes to Remove ---${NC}"
    echo ""
fi

VOLUME_CHANGES=()
while IFS= read -r line; do
    VOLUME_CHANGES+=("$line")
done < <(grep -rn "sqlite-data" "$PROJECT_ROOT/domains/"*/compose.yml 2>/dev/null || true)

if [[ "$JSON_OUTPUT" == "false" ]]; then
    for change in "${VOLUME_CHANGES[@]}"; do
        display="${change#"$PROJECT_ROOT/"}"
        echo -e "  ${YELLOW}-${NC} $display"
    done
    echo ""
    echo -e "  Total volume references: ${BOLD}${#VOLUME_CHANGES[@]}${NC}"
    echo ""
fi

# ---------------------------------------------------------------------------
# Step 3: requirements.txt files with aiosqlite
# ---------------------------------------------------------------------------

if [[ "$JSON_OUTPUT" == "false" ]]; then
    echo -e "${BOLD}--- Step 3: requirements.txt Files with aiosqlite ---${NC}"
    echo -e "  aiosqlite can be removed from these files on cutover day."
    echo ""
fi

AIOSQLITE_FILES=()
while IFS= read -r line; do
    AIOSQLITE_FILES+=("$line")
done < <(grep -rl "aiosqlite" "$PROJECT_ROOT/domains/"*/*/requirements.txt \
    "$PROJECT_ROOT/domains/"*/*/*/requirements.txt 2>/dev/null || true)

if [[ "$JSON_OUTPUT" == "false" ]]; then
    for f in "${AIOSQLITE_FILES[@]}"; do
        display="${f#"$PROJECT_ROOT/"}"
        version=$(grep "aiosqlite" "$f" 2>/dev/null | head -1)
        echo -e "  ${CYAN}-${NC} $display  ($version)"
    done
    echo ""
    echo -e "  Total requirements.txt to update: ${BOLD}${#AIOSQLITE_FILES[@]}${NC}"
    echo ""
fi

# ---------------------------------------------------------------------------
# Step 4: Summary of cutover actions
# ---------------------------------------------------------------------------

if [[ "$JSON_OUTPUT" == "false" ]]; then
    echo -e "${BOLD}============================================================${NC}"
    echo -e "${BOLD}  Cutover Day Summary${NC}"
    echo -e "${BOLD}============================================================${NC}"
    echo ""
    echo -e "  Database files to refactor:      ${BOLD}$DB_FILE_COUNT${NC}"
    echo -e "  Compose env var lines to review: ${BOLD}${#COMPOSE_CHANGES[@]}${NC}"
    echo -e "  Docker volume references:        ${BOLD}${#VOLUME_CHANGES[@]}${NC}"
    echo -e "  requirements.txt to update:      ${BOLD}${#AIOSQLITE_FILES[@]}${NC}"
    echo ""
    echo -e "  ${YELLOW}NOTE: This is a DRY-RUN report. No changes were made.${NC}"
    echo -e "  ${YELLOW}Cutover target: earliest 2026-03-10${NC}"
    echo ""
    echo -e "  Cutover day checklist: docs/operations/sqlite-cutover-checklist.md"
    echo ""
fi

# ---------------------------------------------------------------------------
# JSON output
# ---------------------------------------------------------------------------

if [[ "$JSON_OUTPUT" == "true" ]]; then
    echo "{"
    echo "  \"timestamp\": \"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\","
    echo "  \"status\": \"DRY_RUN\","
    echo "  \"cutover_target\": \"2026-03-10\","
    echo "  \"database_files\": ["

    first=true
    for f in "${DATABASE_FILES[@]}"; do
        if [[ -f "$PROJECT_ROOT/$f" ]]; then
            if [[ "$first" == "false" ]]; then echo ","; fi
            first=false
            printf "    \"%s\"" "$f"
        fi
    done
    echo ""
    echo "  ],"

    echo "  \"compose_env_var_lines\": ${#COMPOSE_CHANGES[@]},"
    echo "  \"volume_references\": ${#VOLUME_CHANGES[@]},"

    echo "  \"aiosqlite_requirements\": ["
    first=true
    for f in "${AIOSQLITE_FILES[@]}"; do
        if [[ "$first" == "false" ]]; then echo ","; fi
        first=false
        display="${f#"$PROJECT_ROOT/"}"
        printf "    \"%s\"" "$display"
    done
    echo ""
    echo "  ],"

    echo "  \"summary\": {"
    echo "    \"database_files_count\": $DB_FILE_COUNT,"
    echo "    \"compose_changes_count\": ${#COMPOSE_CHANGES[@]},"
    echo "    \"volume_references_count\": ${#VOLUME_CHANGES[@]},"
    echo "    \"requirements_count\": ${#AIOSQLITE_FILES[@]}"
    echo "  }"
    echo "}"
fi
