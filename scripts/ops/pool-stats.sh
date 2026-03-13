#!/usr/bin/env bash
# pool-stats.sh — Query pool metrics from all DB-connected services
set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'
BOLD='\033[1m'

# Services with database connections (port mappings)
declare -A DB_SERVICES=(
  ["data-api"]=8006
  ["admin-api"]=8004
  ["websocket-ingestion"]=8001
  ["ha-ai-agent-service"]=8030
  ["ai-automation-service-new"]=8036
  ["ai-query-service"]=8035
  ["automation-trace-service"]=8046
  ["device-health-monitor"]=8019
  ["energy-correlator"]=8017
  ["proactive-agent-service"]=8031
  ["blueprint-index"]=8038
  ["activity-writer"]=8045
)

echo -e "${BOLD}${BLUE}╔══════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${BLUE}║               HomeIQ Database Pool Statistics                    ║${NC}"
echo -e "${BOLD}${BLUE}╚══════════════════════════════════════════════════════════════════╝${NC}"
echo ""
printf "%-30s %-12s %-12s %-12s %-12s\n" "SERVICE" "CHECKED_OUT" "POOL_SIZE" "OVERFLOW" "UTIL%"
echo "──────────────────────────────────────────────────────────────────"

for service in $(echo "${!DB_SERVICES[@]}" | tr ' ' '\n' | sort); do
  port=${DB_SERVICES[$service]}

  # Try /metrics endpoint for Prometheus-format pool metrics
  metrics=$(curl -s --connect-timeout 3 --max-time 5 "http://localhost:${port}/metrics" 2>/dev/null || echo "")

  if [ -n "$metrics" ]; then
    checked_out=$(echo "$metrics" | grep -oP 'db_pool_checked_out\s+\K[0-9.]+' 2>/dev/null || echo "n/a")
    utilization=$(echo "$metrics" | grep -oP 'db_pool_utilization_percent\s+\K[0-9.]+' 2>/dev/null || echo "n/a")

    if [ "$utilization" != "n/a" ] && [ "$(echo "$utilization > 80" | bc -l 2>/dev/null || echo 0)" = "1" ]; then
      color=$RED
    elif [ "$utilization" != "n/a" ] && [ "$(echo "$utilization > 50" | bc -l 2>/dev/null || echo 0)" = "1" ]; then
      color=$YELLOW
    else
      color=$GREEN
    fi

    printf "%-30s %-12s %-12s %-12s ${color}%-12s${NC}\n" "$service" "$checked_out" "10" "20" "$utilization"
  else
    printf "%-30s %-12s %-12s %-12s %-12s\n" "$service" "—" "—" "—" "unreachable"
  fi
done

echo ""
echo -e "${BOLD}Note:${NC} Pool defaults: pool_size=10, max_overflow=20 (per service)"
