#!/usr/bin/env bash
# check-all-health.sh — Hit /health on all HomeIQ services, report status matrix
set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'
BOLD='\033[1m'

# Service registry: name:port
declare -A SERVICES=(
  # Core Platform
  ["data-api"]=8006
  ["websocket-ingestion"]=8001
  ["admin-api"]=8004
  ["health-dashboard"]=3000
  ["data-retention"]=8080
  # Data Collectors
  ["weather-api"]=8009
  ["smart-meter-service"]=8014
  ["sports-api"]=8005
  ["air-quality-service"]=8012
  ["carbon-intensity-service"]=8010
  ["electricity-pricing-service"]=8011
  ["calendar-service"]=8013
  ["log-aggregator"]=8015
  # ML Engine
  ["ai-core-service"]=8033
  ["openvino-service"]=8026
  ["ml-service"]=8025
  ["ner-service"]=8020
  ["openai-service"]=8027
  ["rag-service"]=8018
  ["ai-training-service"]=8028
  ["device-intelligence-service"]=8019
  # Automation Core
  ["ha-ai-agent-service"]=8030
  ["ai-automation-service-new"]=8036
  ["ai-query-service"]=8035
  ["yaml-validation-service"]=8037
  ["automation-linter"]=8016
  ["ai-code-executor"]=8044
  ["automation-trace-service"]=8046
  # Blueprints
  ["blueprint-index"]=8038
  ["blueprint-suggestion-service"]=8039
  ["rule-recommendation-ml"]=8040
  ["automation-miner"]=8029
  # Energy Analytics
  ["energy-correlator"]=8017
  ["energy-forecasting"]=8042
  ["proactive-agent-service"]=8031
  # Device Management
  ["device-health-monitor"]=8019
  ["device-setup-assistant"]=8021
  ["device-database-client"]=8022
  ["device-recommender"]=8023
  ["activity-recognition"]=8043
  ["activity-writer"]=8045
  ["ha-setup-service"]=8024
  # Pattern Analysis
  ["ai-pattern-service"]=8034
  ["api-automation-edge"]=8041
  # Infrastructure
  ["prometheus"]=9090
  ["grafana"]=3002
  ["jaeger"]=16686
)

HEALTHY=0
DEGRADED=0
DOWN=0
TOTAL=${#SERVICES[@]}

echo -e "${BOLD}${BLUE}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${BLUE}║         HomeIQ Service Health Matrix                 ║${NC}"
echo -e "${BOLD}${BLUE}╚══════════════════════════════════════════════════════╝${NC}"
echo ""
printf "%-35s %-8s %s\n" "SERVICE" "PORT" "STATUS"
echo "─────────────────────────────────────────────────────"

for service in $(echo "${!SERVICES[@]}" | tr ' ' '\n' | sort); do
  port=${SERVICES[$service]}
  status_code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 3 --max-time 5 "http://localhost:${port}/health" 2>/dev/null || echo "000")

  if [ "$status_code" = "200" ]; then
    printf "%-35s %-8s ${GREEN}● HEALTHY${NC}\n" "$service" "$port"
    ((HEALTHY++))
  elif [ "$status_code" = "000" ]; then
    printf "%-35s %-8s ${RED}✗ DOWN${NC}\n" "$service" "$port"
    ((DOWN++))
  else
    printf "%-35s %-8s ${YELLOW}◐ DEGRADED (HTTP ${status_code})${NC}\n" "$service" "$port"
    ((DEGRADED++))
  fi
done

echo ""
echo "─────────────────────────────────────────────────────"
echo -e "${BOLD}Summary:${NC} ${GREEN}${HEALTHY} healthy${NC} | ${YELLOW}${DEGRADED} degraded${NC} | ${RED}${DOWN} down${NC} | Total: ${TOTAL}"

if [ "$DOWN" -gt 0 ]; then
  exit 1
fi
