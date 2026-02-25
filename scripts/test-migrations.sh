#!/bin/bash
#
# test-migrations.sh — Validate Alembic migrations for all services
#
# Iterates over every service that has an alembic.ini file, runs
# upgrade head -> downgrade base -> upgrade head, and reports results.
#
# Prerequisites:
#   - PostgreSQL running and accessible (see POSTGRES_URL)
#   - Python environment with service dependencies installed
#   - init-schemas.sql already applied to the target database
#
# Usage:
#   POSTGRES_URL=postgresql+asyncpg://homeiq:homeiq_test@localhost:5432/homeiq_test \
#     ./scripts/test-migrations.sh
#
# Exit code: 0 if all services pass, 1 if any fail.

set -euo pipefail

# Colors for output (disabled if not a terminal)
if [ -t 1 ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[0;33m'
    BOLD='\033[1m'
    NC='\033[0m'
else
    RED=''
    GREEN=''
    YELLOW=''
    BOLD=''
    NC=''
fi

# Resolve project root (script lives in scripts/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ -z "${POSTGRES_URL:-}" ]; then
    echo -e "${YELLOW}WARNING: POSTGRES_URL not set. Migrations will use default SQLite URL from alembic.ini.${NC}"
fi

echo -e "${BOLD}=== Alembic Migration Validation ===${NC}"
echo ""

passed=0
failed=0
skipped=0
failed_services=""

# Find all services with alembic.ini
while IFS= read -r -d '' alembic_ini; do
    service_dir="$(dirname "$alembic_ini")"
    service_name="$(basename "$service_dir")"
    # Include domain group for clarity
    domain_group="$(basename "$(dirname "$service_dir")")"
    display_name="${domain_group}/${service_name}"

    echo -e "${BOLD}--- ${display_name} ---${NC}"

    # Check if alembic/versions directory exists and has migration files
    versions_dir="${service_dir}/alembic/versions"
    if [ ! -d "$versions_dir" ] || [ -z "$(find "$versions_dir" -name '*.py' -not -name '__pycache__' 2>/dev/null)" ]; then
        echo -e "  ${YELLOW}SKIP${NC} — no migration files in ${versions_dir}"
        ((skipped++))
        echo ""
        continue
    fi

    # Run the upgrade/downgrade/upgrade cycle
    if (
        cd "$service_dir"
        echo "  upgrade head..."
        python -m alembic upgrade head 2>&1 | sed 's/^/    /'
        echo "  downgrade base..."
        python -m alembic downgrade base 2>&1 | sed 's/^/    /'
        echo "  upgrade head (re-apply)..."
        python -m alembic upgrade head 2>&1 | sed 's/^/    /'
    ); then
        echo -e "  ${GREEN}PASS${NC}"
        ((passed++))
    else
        echo -e "  ${RED}FAIL${NC}"
        ((failed++))
        failed_services="${failed_services}  - ${display_name}\n"
    fi

    echo ""
done < <(find "$PROJECT_ROOT/domains" -name "alembic.ini" -print0 | sort -z)

# Summary
echo -e "${BOLD}=== Summary ===${NC}"
echo -e "  ${GREEN}Passed:${NC}  ${passed}"
echo -e "  ${RED}Failed:${NC}  ${failed}"
echo -e "  ${YELLOW}Skipped:${NC} ${skipped}"
echo ""

if [ "$failed" -gt 0 ]; then
    echo -e "${RED}Failed services:${NC}"
    echo -e "$failed_services"
    exit 1
fi

if [ "$passed" -eq 0 ] && [ "$skipped" -gt 0 ]; then
    echo -e "${YELLOW}No services had migration files to test.${NC}"
    exit 0
fi

echo -e "${GREEN}All migration tests passed.${NC}"
exit 0
