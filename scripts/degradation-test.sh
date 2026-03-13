#!/usr/bin/env bash
# scripts/degradation-test.sh — Graceful Degradation Smoke Tests (Epic 55, Story 55.3)
# Tests that services degrade gracefully when dependencies go down.
# Each test stops a dependency, verifies dependent services return non-5xx responses,
# then restarts the dependency and waits for it to become healthy again.
# Usage: ./scripts/degradation-test.sh

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

PASS=0
FAIL=0

check_not_500() {
    local url="$1"
    local label="$2"
    local code
    code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$url" 2>/dev/null || echo "000")
    if [[ "$code" == "500" || "$code" == "502" || "$code" == "503" || "$code" == "000" ]]; then
        echo -e "  ${RED}FAIL${NC} $label → HTTP $code"
        FAIL=$((FAIL + 1))
    else
        echo -e "  ${GREEN}PASS${NC} $label → HTTP $code"
        PASS=$((PASS + 1))
    fi
}

wait_healthy() {
    local container="$1"
    local max_wait="${2:-30}"
    echo -n "  Waiting for $container to be healthy..."
    for i in $(seq 1 "$max_wait"); do
        local health
        health=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "unknown")
        if [[ "$health" == "healthy" ]]; then
            echo -e " ${GREEN}ready${NC}"
            return 0
        fi
        sleep 1
    done
    echo -e " ${YELLOW}timeout (may still be starting)${NC}"
}

# =========================================================================
# Test 1: InfluxDB Down
# =========================================================================
echo ""
echo -e "${CYAN}Test 1: InfluxDB Down${NC}"
echo "  Stopping homeiq-influxdb..."
docker stop homeiq-influxdb > /dev/null 2>&1
sleep 5

check_not_500 "http://localhost:8006/health" "data-api /health (influxdb down)"
check_not_500 "http://localhost:8006/api/v1/events" "data-api /api/v1/events (influxdb down)"

echo "  Restarting homeiq-influxdb..."
docker start homeiq-influxdb > /dev/null 2>&1
wait_healthy "homeiq-influxdb" 30

# =========================================================================
# Test 2: PostgreSQL Down
# =========================================================================
echo ""
echo -e "${CYAN}Test 2: PostgreSQL Down${NC}"
echo "  Stopping homeiq-postgres..."
docker stop homeiq-postgres > /dev/null 2>&1
sleep 5

check_not_500 "http://localhost:8006/health" "data-api /health (postgres down)"
check_not_500 "http://localhost:8004/health" "admin-api /health (postgres down)"

echo "  Restarting homeiq-postgres..."
docker start homeiq-postgres > /dev/null 2>&1
wait_healthy "homeiq-postgres" 30

# =========================================================================
# Test 3: Weather API Down
# =========================================================================
echo ""
echo -e "${CYAN}Test 3: Weather API Down${NC}"
echo "  Stopping homeiq-weather-api..."
docker stop homeiq-weather-api > /dev/null 2>&1
sleep 3

check_not_500 "http://localhost:8006/health" "data-api /health (weather-api down)"

echo "  Restarting homeiq-weather-api..."
docker start homeiq-weather-api > /dev/null 2>&1
wait_healthy "homeiq-weather-api" 30

# =========================================================================
# Test 4: Data API Down
# =========================================================================
echo ""
echo -e "${CYAN}Test 4: Data API Down${NC}"
echo "  Stopping homeiq-data-api..."
docker stop homeiq-data-api > /dev/null 2>&1
sleep 5

check_not_500 "http://localhost:8004/health" "admin-api /health (data-api down)"
check_not_500 "http://localhost:3000/health" "health-dashboard /health (data-api down)"

echo "  Restarting homeiq-data-api..."
docker start homeiq-data-api > /dev/null 2>&1
wait_healthy "homeiq-data-api" 30

# =========================================================================
# Results
# =========================================================================
echo ""
echo "================================="
echo -e "Results: ${GREEN}${PASS} passed${NC}, ${RED}${FAIL} failed${NC}"
echo "================================="

exit $FAIL
