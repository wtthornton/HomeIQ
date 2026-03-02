#!/bin/bash
# =============================================================================
# HomeIQ Deploy — Tier 2: Essential Services
# =============================================================================
# Deploys: health-dashboard, data-retention, all data-collectors (8 services)
#
# Usage:
#   ./scripts/deploy-tier2.sh                # Deploy and verify
#   ./scripts/deploy-tier2.sh --no-tag       # Skip git tagging
#   ./scripts/deploy-tier2.sh --rollback     # Rollback Tier 2
#
# Prerequisite: Tier 1 must be healthy (checked automatically).
# Includes a 15-minute health verification gate.
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
export PROJECT_ROOT
source "$SCRIPT_DIR/deployment/common.sh"

SKIP_TAG=false
ROLLBACK=false
HEALTH_GATE_MINUTES=${HEALTH_GATE_MINUTES:-15}

while [[ $# -gt 0 ]]; do
  case $1 in
    --no-tag)   SKIP_TAG=true; shift ;;
    --rollback) ROLLBACK=true; shift ;;
    -h|--help)
      echo "Usage: $0 [--no-tag] [--rollback]"
      exit 0
      ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

CORE_COMPOSE="domains/core-platform/compose.yml"
DC_COMPOSE="domains/data-collectors/compose.yml"
START_TIME=$(date +%s)

TIER2_SERVICES=(
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

# --- Rollback ---
if [ "$ROLLBACK" = true ]; then
  log_header "Tier 2 Rollback"
  log_info "Stopping data-collectors..."
  docker compose -f "$PROJECT_ROOT/$DC_COMPOSE" down 2>> "$LOG_FILE" || true
  log_info "Restarting data-collectors with previous config..."
  docker compose -f "$PROJECT_ROOT/$DC_COMPOSE" up -d 2>> "$LOG_FILE" || true
  log_info "Stopping Tier 2 core-platform additions..."
  docker compose -f "$PROJECT_ROOT/$CORE_COMPOSE" up -d influxdb postgres data-api websocket-ingestion admin-api prometheus grafana postgres-exporter 2>> "$LOG_FILE" || true
  log_info "Tier 2 rollback complete. Verify health manually."
  exit 0
fi

# --- Pre-flight: Verify Tier 1 is healthy ---
log_header "TIER 2: Essential Services"
log_info "Pre-flight: Checking Tier 1 services..."

TIER1_CHECK_SERVICES=(
  "websocket-ingestion:8001"
  "data-api:8006"
  "admin-api:8004"
)

MAX_HEALTH_RETRIES=5
HEALTH_CHECK_INTERVAL=2

if ! wait_for_services "Tier 1 (pre-flight)" "${TIER1_CHECK_SERVICES[@]}"; then
  log_error "Tier 1 is NOT healthy — deploy Tier 1 first (scripts/deploy-tier1.sh)"
  exit 1
fi

# Reset retry settings for Tier 2
MAX_HEALTH_RETRIES=30
HEALTH_CHECK_INTERVAL=2

# --- Git tag ---
if [ "$SKIP_TAG" = false ]; then
  log_info "Creating git tag: deployment-phase5-tier2-${DEPLOY_TIMESTAMP}"
  cd "$PROJECT_ROOT"
  git tag -a "deployment-phase5-tier2-${DEPLOY_TIMESTAMP}" \
    -m "Phase 5 Tier 2 deployment — essential services" 2>> "$LOG_FILE" || \
    log_warn "Git tag creation failed (may already exist)"
fi

# --- Deploy ---
log_info "Step 1/4: Deploying health-dashboard and data-retention..."
deploy_compose "$CORE_COMPOSE" health-dashboard data-retention

log_info "Step 2/4: Deploying all data-collectors..."
deploy_compose "$DC_COMPOSE"

log_info "Step 3/4: Waiting 10 seconds for services to initialize..."
sleep 10

# --- Health checks ---
log_info "Step 4/4: Running health checks..."
if ! wait_for_services "Tier 2" "${TIER2_SERVICES[@]}"; then
  log_error "Tier 2 health checks FAILED"
  log_error "Rollback with: $0 --rollback"
  exit 1
fi

gate_check "Tier 2 Health Check" 0

# --- 15-minute health gate ---
log_info "Starting ${HEALTH_GATE_MINUTES}-minute health verification loop..."
log_info "Press Ctrl+C to skip"

GATE_END=$(($(date +%s) + HEALTH_GATE_MINUTES * 60))
CHECK_INTERVAL=60
FAILURES=0

while [ "$(date +%s)" -lt "$GATE_END" ]; do
  remaining=$(( (GATE_END - $(date +%s)) / 60 ))
  all_healthy=true

  for entry in "${TIER2_SERVICES[@]}"; do
    IFS=':' read -r name port <<< "$entry"
    if ! curl -f -s --max-time 5 "http://localhost:${port}/health" > /dev/null 2>&1; then
      log_warn "$name (port $port) health check failed"
      all_healthy=false
      FAILURES=$((FAILURES + 1))
    fi
  done

  if [ $FAILURES -ge 10 ]; then
    log_error "Too many failures ($FAILURES) — Tier 2 unstable"
    log_error "Consider rollback: $0 --rollback"
    exit 1
  fi

  if [ "$all_healthy" = true ]; then
    log_info "  Health check OK — ${remaining}m remaining"
  fi

  sleep $CHECK_INTERVAL
done

# --- Summary ---
ELAPSED=$(($(date +%s) - START_TIME))
log_header "Tier 2 Deployment Complete"
log_success "Duration: $(format_duration $ELAPSED)"
log_success "Services deployed: health-dashboard, data-retention, 8 data-collectors"
log_success "${HEALTH_GATE_MINUTES}-minute health gate PASSED"
echo ""
log_info "Next: Deploy Tier 3 with scripts/deploy-tier3.sh"
log_info "Full log: $LOG_FILE"
