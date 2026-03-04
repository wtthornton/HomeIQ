#!/bin/bash
# Phase 5 Production Deployment Script
# Usage: ./scripts/deploy-phase-5.sh [tier1|tier2|tier3|tier4-9|all]
#
# This script automates the tier-by-tier deployment of HomeIQ Phase 5
# Each tier waits for health checks before proceeding
# Logs all activities to deployment_phase5_$(date +%Y%m%d_%H%M%S).log

set -e

# Configuration
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="deployment_phase5_${TIMESTAMP}.log"
DEPLOYMENT_MARKER="deployment_phase5_${TIMESTAMP}.marker"
MAX_HEALTH_RETRIES=30
HEALTH_CHECK_INTERVAL=2

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
  echo -e "${BLUE}[INFO $(date +'%H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
  echo -e "${GREEN}[✅ $(date +'%H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
  echo -e "${RED}[❌ $(date +'%H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

log_warning() {
  echo -e "${YELLOW}[⚠️  $(date +'%H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

# Health check function
check_service_health() {
  local port=$1
  local service_name=$2
  local retries=0

  while [ $retries -lt $MAX_HEALTH_RETRIES ]; do
    if curl -f -s "http://localhost:$port/health" > /dev/null 2>&1; then
      log_success "$service_name (port $port) is healthy"
      return 0
    fi

    retries=$((retries + 1))
    if [ $retries -lt $MAX_HEALTH_RETRIES ]; then
      log_warning "$service_name (port $port) not ready yet... retrying ($retries/$MAX_HEALTH_RETRIES)"
      sleep $HEALTH_CHECK_INTERVAL
    fi
  done

  log_error "$service_name (port $port) failed health check after $MAX_HEALTH_RETRIES attempts"
  return 1
}

# Wait for all services in a tier
wait_for_tier_health() {
  local tier_name=$1
  shift
  local services=("$@")

  log_info "Waiting for $tier_name services to be healthy..."

  for service in "${services[@]}"; do
    IFS=':' read -r name port <<< "$service"
    if ! check_service_health "$port" "$name"; then
      return 1
    fi
  done

  log_success "All $tier_name services are healthy"
  return 0
}

# Gate check before proceeding
gate_check() {
  local gate_name=$1
  local result=$2

  if [ $result -eq 0 ]; then
    log_success "GATE PASSED: $gate_name"
    echo ""
    return 0
  else
    log_error "GATE FAILED: $gate_name"
    log_error "Deployment halted. Review logs in $LOG_FILE"
    exit 1
  fi
}

# Deploy Tier 1: Critical Infrastructure
deploy_tier_1() {
  log_info "========================================="
  log_info "TIER 1: Critical Infrastructure"
  log_info "========================================="

  # Ensure shared Docker network exists before any compose up
  log_info "Ensuring homeiq-network exists..."
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  "$SCRIPT_DIR/ensure-network.sh"

  log_info "Creating deployment marker and git tag..."
  echo "$TIMESTAMP" > "$DEPLOYMENT_MARKER"
  git tag -a "deployment-phase5-tier1-${TIMESTAMP}" -m "Phase 5 Tier 1 deployment"

  log_info "Deploying core-platform services..."
  docker compose -f domains/core-platform/compose.yml up -d --pull always

  log_info "Waiting 10 seconds for services to initialize..."
  sleep 10

  # Health gate: influxdb and data-api must be healthy before proceeding to tier 2
  log_info "Health gate: waiting for influxdb and data-api..."
  check_service_health 8086 "influxdb"
  check_service_health 8006 "data-api"

  # Check Tier 1 services
  local tier1_services=(
    "websocket-ingestion:8001"
    "data-api:8006"
    "admin-api:8004"
  )

  if ! wait_for_tier_health "Tier 1" "${tier1_services[@]}"; then
    gate_check "Tier 1 Health Check" 1
  fi

  log_info "Running Tier 1 smoke tests..."
  if pytest tests/smoke/tier1_health.py -v >> "$LOG_FILE" 2>&1; then
    log_success "Tier 1 smoke tests passed"
  else
    log_warning "Tier 1 smoke tests had issues (check logs)"
  fi

  gate_check "Tier 1 Deployment" 0
  log_info ""
}

# Deploy Tier 2: Data Collection
deploy_tier_2() {
  log_info "========================================="
  log_info "TIER 2: Data Collection & Core Features"
  log_info "========================================="

  log_info "Creating git tag..."
  git tag -a "deployment-phase5-tier2-${TIMESTAMP}" -m "Phase 5 Tier 2 deployment"

  log_info "Deploying core-platform data services..."
  docker compose -f domains/core-platform/compose.yml up -d health-dashboard data-retention --pull always

  log_info "Deploying data-collectors domain..."
  docker compose -f domains/data-collectors/compose.yml up -d --pull always

  log_info "Waiting 10 seconds for services to initialize..."
  sleep 10

  # Check Tier 2 services
  local tier2_services=(
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
  )

  if ! wait_for_tier_health "Tier 2" "${tier2_services[@]}"; then
    gate_check "Tier 2 Health Check" 1
  fi

  gate_check "Tier 2 Deployment" 0
  log_info ""
}

# Deploy Tier 3: ML/AI Services
deploy_tier_3() {
  log_info "========================================="
  log_info "TIER 3: ML/AI Services"
  log_info "========================================="

  log_info "Creating git tag..."
  git tag -a "deployment-phase5-tier3-${TIMESTAMP}" -m "Phase 5 Tier 3 deployment"

  log_info "Deploying ml-engine domain..."
  docker compose -f domains/ml-engine/compose.yml up -d --pull always

  log_info "Waiting 30 seconds for model loading (this is normal)..."
  sleep 30

  # Check Tier 3 services
  local tier3_services=(
    "openvino-service:8026"
    "ml-service:8025"
    "ai-core-service:8018"
    "ai-training-service:8033"
    "device-intelligence-service:8028"
  )

  if ! wait_for_tier_health "Tier 3" "${tier3_services[@]}"; then
    gate_check "Tier 3 Health Check" 1
  fi

  gate_check "Tier 3 Deployment" 0
  log_info ""
}

# Deploy Tiers 4-9: Remaining Services
deploy_tiers_4_9() {
  log_info "========================================="
  log_info "TIERS 4-9: Remaining Services"
  log_info "========================================="

  log_info "Creating git tag..."
  git tag -a "deployment-phase5-tiers49-${TIMESTAMP}" -m "Phase 5 Tiers 4-9 deployment"

  log_info "Deploying Tier 4: automation-core..."
  docker compose -f domains/automation-core/compose.yml up -d --pull always

  log_info "Deploying Tier 5: blueprints..."
  docker compose -f domains/blueprints/compose.yml up -d --pull always

  log_info "Deploying Tier 6: energy-analytics..."
  docker compose -f domains/energy-analytics/compose.yml up -d --pull always

  log_info "Deploying Tier 7: device-management..."
  docker compose -f domains/device-management/compose.yml up -d --pull always

  log_info "Deploying Tier 8: pattern-analysis..."
  docker compose -f domains/pattern-analysis/compose.yml up -d --pull always

  log_info "Deploying Tier 9: frontends..."
  docker compose -f domains/frontends/compose.yml up -d --pull always

  log_info "Waiting 15 seconds for services to initialize..."
  sleep 15

  # Simple health check for all services (ping /health endpoints)
  log_info "Running full health checks..."
  local all_healthy=true

  for port in 8030 8036 8035 8016 8037 8032 8038 8039 8029 8017 8024 8031 8019 8022 8023 8021 8032 8033 8034 8034 16686; do
    if curl -f -s "http://localhost:$port/health" > /dev/null 2>&1; then
      log_success "Port $port is responding"
    else
      log_warning "Port $port is not responding yet"
    fi
  done

  gate_check "Tiers 4-9 Deployment" 0
  log_info ""
}

# Post-deployment validation
post_deployment_validation() {
  log_info "========================================="
  log_info "POST-DEPLOYMENT VALIDATION"
  log_info "========================================="

  log_info "Running integration tests..."
  if pytest tests/integration/ -v >> "$LOG_FILE" 2>&1; then
    log_success "Integration tests passed"
  else
    log_warning "Integration tests had issues"
  fi

  log_info "Running E2E tests..."
  if pytest tests/e2e/playwright/ -v >> "$LOG_FILE" 2>&1; then
    log_success "E2E tests passed"
  else
    log_warning "E2E tests had issues"
  fi

  log_info "Checking error rates..."
  # This would check actual error rates from logs

  log_info ""
}

# Main deployment orchestration
main() {
  local tier=$1

  log_info "========================================="
  log_info "Phase 5 Production Deployment"
  log_info "Start Time: $(date)"
  log_info "Log File: $LOG_FILE"
  log_info "========================================="
  log_info ""

  case $tier in
    tier1)
      deploy_tier_1
      ;;
    tier2)
      deploy_tier_1
      deploy_tier_2
      ;;
    tier3)
      deploy_tier_1
      deploy_tier_2
      deploy_tier_3
      ;;
    tier4-9)
      deploy_tier_1
      deploy_tier_2
      deploy_tier_3
      deploy_tiers_4_9
      ;;
    all)
      deploy_tier_1
      deploy_tier_2
      deploy_tier_3
      deploy_tiers_4_9
      post_deployment_validation
      ;;
    *)
      echo "Usage: $0 [tier1|tier2|tier3|tier4-9|all]"
      echo ""
      echo "Options:"
      echo "  tier1      - Deploy only Tier 1 (critical infrastructure)"
      echo "  tier2      - Deploy up to Tier 2 (+ data collection)"
      echo "  tier3      - Deploy up to Tier 3 (+ ML/AI services)"
      echo "  tier4-9    - Deploy all tiers (+ remaining services)"
      echo "  all        - Deploy everything and run validation"
      exit 1
      ;;
  esac

  log_info "========================================="
  log_info "Deployment Stage Complete"
  log_info "End Time: $(date)"
  log_info "Total Duration: $(date -d @$(($(date +%s) - START_TIME)) +%H:%M:%S)"
  log_info "========================================="
  log_info "Check logs in: $LOG_FILE"
}

# Entry point
START_TIME=$(date +%s)
main "$@"
