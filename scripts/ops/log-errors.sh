#!/usr/bin/env bash
# log-errors.sh [minutes] — Grep recent Docker logs for ERROR/CRITICAL across all containers
set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'
BOLD='\033[1m'

MINUTES=${1:-10}
SINCE="${MINUTES}m"

echo -e "${BOLD}${BLUE}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${BLUE}║    HomeIQ Error Log Scanner (last ${MINUTES} minutes)         ║${NC}"
echo -e "${BOLD}${BLUE}╚══════════════════════════════════════════════════════╝${NC}"
echo ""

TOTAL_ERRORS=0
TOTAL_CRITICALS=0

# Get all running homeiq containers
CONTAINERS=$(docker ps --filter "name=homeiq" --format "{{.Names}}" 2>/dev/null | sort)

if [ -z "$CONTAINERS" ]; then
  echo -e "${YELLOW}No running HomeIQ containers found.${NC}"
  exit 0
fi

for container in $CONTAINERS; do
  ERRORS=$(docker logs --since "$SINCE" "$container" 2>&1 | grep -ciE '"level":\s*"(ERROR|CRITICAL)"|ERROR|CRITICAL' || true)

  if [ "$ERRORS" -gt 0 ]; then
    # Count criticals separately
    CRITICALS=$(docker logs --since "$SINCE" "$container" 2>&1 | grep -ciE '"level":\s*"CRITICAL"|CRITICAL' || true)
    NON_CRITICAL=$((ERRORS - CRITICALS))

    if [ "$CRITICALS" -gt 0 ]; then
      echo -e "${RED}${BOLD}✗ ${container}${NC}: ${RED}${CRITICALS} CRITICAL${NC}, ${YELLOW}${NON_CRITICAL} ERROR${NC}"
      # Show last 3 critical messages
      docker logs --since "$SINCE" "$container" 2>&1 | grep -iE '"level":\s*"CRITICAL"|CRITICAL' | tail -3 | while read -r line; do
        echo -e "  ${RED}→ $(echo "$line" | cut -c1-120)${NC}"
      done
    else
      echo -e "${YELLOW}⚠ ${container}${NC}: ${YELLOW}${ERRORS} ERROR${NC}"
    fi

    TOTAL_ERRORS=$((TOTAL_ERRORS + NON_CRITICAL))
    TOTAL_CRITICALS=$((TOTAL_CRITICALS + CRITICALS))
  fi
done

echo ""
echo "─────────────────────────────────────────────────────"
if [ "$TOTAL_ERRORS" -eq 0 ] && [ "$TOTAL_CRITICALS" -eq 0 ]; then
  echo -e "${GREEN}${BOLD}✓ No errors found in the last ${MINUTES} minutes${NC}"
else
  echo -e "${BOLD}Total:${NC} ${RED}${TOTAL_CRITICALS} CRITICAL${NC} | ${YELLOW}${TOTAL_ERRORS} ERROR${NC}"
fi

if [ "$TOTAL_CRITICALS" -gt 0 ]; then
  exit 1
fi
