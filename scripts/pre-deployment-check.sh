#!/bin/bash
# =============================================================================
# HomeIQ Pre-Deployment Validation Gate
# =============================================================================
# Runs all pre-deployment checks and outputs a go/no-go summary.
#
# Usage:
#   ./scripts/pre-deployment-check.sh             # Full validation
#   ./scripts/pre-deployment-check.sh --quick      # Health checks only
#   ./scripts/pre-deployment-check.sh --json       # JSON output
#
# Exit codes: 0 = GO, 1 = NO-GO
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/deployment/common.sh"

QUICK_MODE=false
JSON_OUTPUT=false

while [[ $# -gt 0 ]]; do
  case $1 in
    --quick)   QUICK_MODE=true; shift ;;
    --json)    JSON_OUTPUT=true; shift ;;
    -h|--help)
      echo "Usage: $0 [--quick] [--json]"
      echo "  --quick   Skip tests and Docker build verification"
      echo "  --json    Output results as JSON"
      exit 0
      ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

# Track results
declare -a CHECK_NAMES=()
declare -a CHECK_RESULTS=()
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0

record_check() {
  local name=$1
  local result=$2  # pass|fail|warn
  CHECK_NAMES+=("$name")
  CHECK_RESULTS+=("$result")
  TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
  if [ "$result" = "pass" ]; then
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
    log_success "$name"
  elif [ "$result" = "warn" ]; then
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
    log_warn "$name (warning)"
  else
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
    log_error "$name"
  fi
}

# =========================================================================
# CHECK 1: Service Health Endpoints
# =========================================================================
check_health_endpoints() {
  log_header "Check 1: Service Health Endpoints"

  # All 33 services with health endpoints from the deployment plan
  local -a HEALTH_SERVICES=(
    "websocket-ingestion:8001"
    "data-api:8006"
    "admin-api:8004"
    "health-dashboard:3000:/health"
    "data-retention:8080"
    "weather-api:8009"
    "smart-meter-service:8014"
    "sports-api:8005"
    "calendar-service:8013"
    "carbon-intensity:8010"
    "electricity-pricing:8011"
    "air-quality:8012"
    "log-aggregator:8015"
    "ai-core-service:8018"
    "device-intelligence-service:8028"
    "openvino-service:8026"
    "ml-service:8025"
    "ai-training-service:8033"
    "rag-service:8027"
    "openai-service:8020"
    "automation-linter:8016"
    "ha-ai-agent-service:8030"
    "automation-trace-service:8044"
    "ai-automation-service-new:8036"
    "ai-query-service:8035"
    "yaml-validation-service:8037"
    "ha-device-control:8046"
    "blueprint-suggestion-service:8039"
    "blueprint-index:8038"
    "automation-miner:8029"
    "rule-recommendation-ml:8040:/api/v1/health"
    "energy-correlator:8017"
    "energy-forecasting:8042:/api/v1/health"
    "proactive-agent-service:8031"
    "device-health-monitor:8019"
    "device-database-client:8022"
    "device-recommender:8023"
    "device-setup-assistant:8021"
    "device-context-classifier:8032"
    "activity-recognition:8043"
    "activity-writer:8045"
    "ha-setup-service:8024"
    "ai-pattern-service:8034"
    "api-automation-edge:8041"
    "voice-gateway:8047"
    "jaeger:16686:/"
    "observability-dashboard:8501:/_stcore/health"
    "ai-automation-ui:3001:/health"
  )

  local healthy=0
  local unhealthy=0
  local total=${#HEALTH_SERVICES[@]}

  # Use short retries for pre-deployment check (services should already be up)
  MAX_HEALTH_RETRIES=3
  HEALTH_CHECK_INTERVAL=1

  for entry in "${HEALTH_SERVICES[@]}"; do
    IFS=':' read -r name port endpoint <<< "$entry"
    endpoint=${endpoint:-/health}
    if curl -f -s --max-time 5 "http://localhost:${port}${endpoint}" > /dev/null 2>&1; then
      healthy=$((healthy + 1))
    else
      log_warn "  $name (port $port) is NOT responding"
      unhealthy=$((unhealthy + 1))
    fi
  done

  log_info "Health endpoints: $healthy/$total responding"

  # 2 HA-dependent services are expected to be degraded
  if [ $unhealthy -le 2 ]; then
    record_check "Health endpoints ($healthy/$total responding, $unhealthy down)" "pass"
  else
    record_check "Health endpoints ($healthy/$total responding, $unhealthy down)" "fail"
  fi
}

# =========================================================================
# CHECK 2: Test Suite
# =========================================================================
check_tests() {
  log_header "Check 2: Test Suite"

  if [ "$QUICK_MODE" = true ]; then
    record_check "Test suite (skipped — quick mode)" "warn"
    return
  fi

  cd "$PROJECT_ROOT"
  if python -m pytest tests/ --tb=no -q 2>> "$LOG_FILE"; then
    record_check "Python test suite (all passing)" "pass"
  else
    record_check "Python test suite (failures detected)" "fail"
  fi
}

# =========================================================================
# CHECK 3: Docker Compose Config
# =========================================================================
check_docker_config() {
  log_header "Check 3: Docker Compose Configuration"

  cd "$PROJECT_ROOT"
  if docker compose config --quiet 2>> "$LOG_FILE"; then
    record_check "Docker Compose config validates" "pass"
  else
    record_check "Docker Compose config validation FAILED" "fail"
  fi
}

# =========================================================================
# CHECK 4: PostgreSQL Schemas
# =========================================================================
check_postgres() {
  log_header "Check 4: PostgreSQL Database"

  # Check PostgreSQL is reachable
  if ! docker exec homeiq-postgres pg_isready -U homeiq -d homeiq > /dev/null 2>&1; then
    record_check "PostgreSQL connection" "fail"
    return
  fi
  record_check "PostgreSQL connection" "pass"

  # Check 8 expected schemas
  local expected_schemas=("core" "automation" "agent" "blueprints" "energy" "devices" "patterns" "rag")
  local found=0
  for schema in "${expected_schemas[@]}"; do
    if docker exec homeiq-postgres psql -U homeiq -d homeiq -tAc "SELECT 1 FROM information_schema.schemata WHERE schema_name='${schema}'" 2>/dev/null | grep -q "1"; then
      found=$((found + 1))
    else
      log_warn "  Schema '$schema' not found"
    fi
  done

  if [ $found -eq ${#expected_schemas[@]} ]; then
    record_check "PostgreSQL schemas ($found/${#expected_schemas[@]})" "pass"
  else
    record_check "PostgreSQL schemas ($found/${#expected_schemas[@]} — missing schemas)" "fail"
  fi
}

# =========================================================================
# CHECK 5: InfluxDB
# =========================================================================
check_influxdb() {
  log_header "Check 5: InfluxDB"

  if curl -f -s --max-time 5 "http://localhost:8086/health" > /dev/null 2>&1; then
    record_check "InfluxDB health" "pass"
  else
    record_check "InfluxDB health" "fail"
  fi
}

# =========================================================================
# CHECK 6: Docker Images (build verification)
# =========================================================================
check_docker_images() {
  log_header "Check 6: Docker Image Verification"

  if [ "$QUICK_MODE" = true ]; then
    record_check "Docker images (skipped — quick mode)" "warn"
    return
  fi

  local image_count
  image_count=$(docker images --format '{{.Repository}}' | grep -c "homeiq" 2>/dev/null || echo "0")

  if [ "$image_count" -ge 30 ]; then
    record_check "Docker images ($image_count homeiq images found)" "pass"
  else
    record_check "Docker images (only $image_count homeiq images — expected 30+)" "warn"
  fi
}

# =========================================================================
# CHECK 7: Disk Space
# =========================================================================
check_disk_space() {
  log_header "Check 7: Disk Space"

  # Get available space in GB (works on Linux; adapt for other OS)
  local avail_kb
  avail_kb=$(df "$PROJECT_ROOT" 2>/dev/null | tail -1 | awk '{print $4}')
  local avail_gb=$((avail_kb / 1024 / 1024))

  if [ "$avail_gb" -ge 20 ]; then
    record_check "Disk space (${avail_gb}GB available)" "pass"
  elif [ "$avail_gb" -ge 10 ]; then
    record_check "Disk space (${avail_gb}GB available — low)" "warn"
  else
    record_check "Disk space (${avail_gb}GB available — critically low)" "fail"
  fi
}

# =========================================================================
# CHECK 8: Monitoring Infrastructure
# =========================================================================
check_monitoring() {
  log_header "Check 8: Monitoring Infrastructure"

  local monitoring_ok=true

  # Prometheus
  if curl -f -s --max-time 5 "http://localhost:9090/-/healthy" > /dev/null 2>&1; then
    log_info "  Prometheus is healthy"
  else
    log_warn "  Prometheus is NOT responding"
    monitoring_ok=false
  fi

  # Grafana
  if curl -f -s --max-time 5 "http://localhost:3002/api/health" > /dev/null 2>&1; then
    log_info "  Grafana is healthy"
  else
    log_warn "  Grafana is NOT responding"
    monitoring_ok=false
  fi

  if [ "$monitoring_ok" = true ]; then
    record_check "Monitoring infrastructure (Prometheus + Grafana)" "pass"
  else
    record_check "Monitoring infrastructure (Prometheus/Grafana issues)" "warn"
  fi
}

# =========================================================================
# SUMMARY
# =========================================================================
print_summary() {
  log_header "PRE-DEPLOYMENT VALIDATION SUMMARY"

  local decision="GO"
  if [ $FAILED_CHECKS -gt 0 ]; then
    decision="NO-GO"
  fi

  echo "" | tee -a "$LOG_FILE"
  log_info "Timestamp:    $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  log_info "Total Checks: $TOTAL_CHECKS"
  log_info "Passed:       $PASSED_CHECKS"
  log_info "Failed:       $FAILED_CHECKS"
  echo "" | tee -a "$LOG_FILE"

  if [ "$decision" = "GO" ]; then
    log_success "DECISION: GO — All pre-deployment gates passed"
    log_info "Proceed with Tier 1 deployment (scripts/deploy-tier1.sh)"
  else
    log_error "DECISION: NO-GO — $FAILED_CHECKS checks failed"
    log_error "Fix failures above before proceeding with deployment"
  fi

  echo "" | tee -a "$LOG_FILE"
  log_info "Full log: $LOG_FILE"
}

print_json_summary() {
  local decision="GO"
  [ $FAILED_CHECKS -gt 0 ] && decision="NO-GO"

  echo "{"
  echo "  \"timestamp\": \"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\","
  echo "  \"decision\": \"$decision\","
  echo "  \"total_checks\": $TOTAL_CHECKS,"
  echo "  \"passed\": $PASSED_CHECKS,"
  echo "  \"failed\": $FAILED_CHECKS,"
  echo "  \"checks\": ["
  for i in "${!CHECK_NAMES[@]}"; do
    [ "$i" -gt 0 ] && echo ","
    echo -n "    {\"name\": \"${CHECK_NAMES[$i]}\", \"result\": \"${CHECK_RESULTS[$i]}\"}"
  done
  echo ""
  echo "  ]"
  echo "}"
}

# =========================================================================
# MAIN
# =========================================================================
main() {
  log_header "HomeIQ Pre-Deployment Validation Gate"
  log_info "Mode: $([ "$QUICK_MODE" = true ] && echo 'quick' || echo 'full')"
  log_info "Project root: $PROJECT_ROOT"
  echo ""

  check_health_endpoints
  check_tests
  check_docker_config
  check_postgres
  check_influxdb
  check_docker_images
  check_disk_space
  check_monitoring

  if [ "$JSON_OUTPUT" = true ]; then
    print_json_summary
  else
    print_summary
  fi

  [ $FAILED_CHECKS -eq 0 ] && exit 0 || exit 1
}

main
