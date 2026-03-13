#!/bin/bash
# Check deployed code versions across all HomeIQ services
# Usage: ./scripts/check-versions.sh [--expected-sha <sha>]
#
# Queries every service's /health endpoint and reports git_sha + build_time.
# With --expected-sha, highlights mismatches (stale containers).

EXPECTED_SHA=""

while [[ $# -gt 0 ]]; do
  case $1 in
    --expected-sha) EXPECTED_SHA="$2"; shift 2 ;;
    *) echo "Usage: $0 [--expected-sha <sha>]"; exit 1 ;;
  esac
done

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SERVICES=(
  # Tier 1: Critical Infrastructure
  "websocket-ingestion:8001"
  "data-api:8006"
  "admin-api:8004"
  # Tier 2: Data Collection
  "health-dashboard:3000"
  "data-retention:8080"
  "weather-api:8009"
  "smart-meter-service:8014"
  "sports-api:8005"
  "calendar-service:8013"
  "carbon-intensity:8010"
  "electricity-pricing:8011"
  "air-quality:8012"
  "log-aggregator:8015"
  # Tier 3: ML/AI
  "openvino-service:8026"
  "ml-service:8025"
  "ai-core-service:8018"
  "ai-training-service:8033"
  "device-intelligence-service:8028"
  "rag-service:8027"
  "openai-service:8020"
  # Tier 4: Automation Core
  "ha-ai-agent-service:8030"
  "ai-automation-service-new:8036"
  "ai-query-service:8035"
  "automation-linter:8016"
  "yaml-validation-service:8037"
  "automation-trace-service:8044"
  "ha-device-control:8046"
  # Tier 5: Blueprints
  "blueprint-index:8038"
  "blueprint-suggestion-service:8039"
  "automation-miner:8029"
  "rule-recommendation-ml:8040"
  # Tier 6: Energy Analytics
  "energy-correlator:8017"
  "energy-forecasting:8042"
  "proactive-agent-service:8031"
  # Tier 7: Device Management
  "device-health-monitor:8019"
  "device-setup-assistant:8021"
  "device-database-client:8022"
  "device-recommender:8023"
  "ha-setup-service:8024"
  "device-context-classifier:8032"
  "activity-recognition:8043"
  "activity-writer:8045"
  # Tier 8: Pattern Analysis
  "ai-pattern-service:8034"
  "api-automation-edge:8041"
  # Tier 9: Frontends
  "ai-automation-ui:3001"
  "observability-dashboard:8501"
  "voice-gateway:8047"
)

printf "%-35s %-12s %-10s %s\n" "SERVICE" "GIT_SHA" "VERSION" "BUILD_TIME"
printf "%-35s %-12s %-10s %s\n" "---" "---" "---" "---"

MISMATCH=0
TOTAL=0
OK=0

for entry in "${SERVICES[@]}"; do
  IFS=':' read -r name port <<< "$entry"
  TOTAL=$((TOTAL + 1))

  response=$(curl -s -f "http://localhost:$port/health" 2>/dev/null)
  if [ $? -ne 0 ]; then
    printf "${RED}%-35s %-12s %-10s %s${NC}\n" "$name:$port" "UNREACHABLE" "-" "-"
    MISMATCH=$((MISMATCH + 1))
    continue
  fi

  git_sha=$(echo "$response" | python -c "import sys,json; print(json.load(sys.stdin).get('git_sha','N/A'))" 2>/dev/null || echo "N/A")
  version=$(echo "$response" | python -c "import sys,json; print(json.load(sys.stdin).get('version','N/A'))" 2>/dev/null || echo "N/A")
  build_time=$(echo "$response" | python -c "import sys,json; print(json.load(sys.stdin).get('build_time','N/A'))" 2>/dev/null || echo "N/A")

  if [ -n "$EXPECTED_SHA" ] && [ "$git_sha" != "$EXPECTED_SHA" ]; then
    printf "${YELLOW}%-35s %-12s %-10s %s${NC}\n" "$name:$port" "$git_sha" "$version" "$build_time"
    MISMATCH=$((MISMATCH + 1))
  else
    printf "${GREEN}%-35s %-12s %-10s %s${NC}\n" "$name:$port" "$git_sha" "$version" "$build_time"
    OK=$((OK + 1))
  fi
done

echo ""
echo "Summary: $TOTAL services checked, $OK matching, $MISMATCH mismatched/unreachable"

if [ -n "$EXPECTED_SHA" ]; then
  echo "Expected SHA: $EXPECTED_SHA"
fi

if [ $MISMATCH -gt 0 ] && [ -n "$EXPECTED_SHA" ]; then
  echo ""
  echo "Yellow entries need rebuild+redeploy to match expected SHA."
  exit 1
fi
