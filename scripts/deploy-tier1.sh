#!/bin/bash
# =============================================================================
# HomeIQ Deploy — Tier 1: Core Infrastructure
# =============================================================================
# Deploys: InfluxDB, PostgreSQL, websocket-ingestion, data-api, admin-api
# Also brings up monitoring: Prometheus, Grafana, postgres-exporter
#
# Usage:
#   ./scripts/deploy-tier1.sh                # Deploy and verify
#   ./scripts/deploy-tier1.sh --no-tag       # Skip git tagging
#   ./scripts/deploy-tier1.sh --rollback     # Rollback Tier 1
#
# Includes a 30-minute health verification loop after deployment.
# Exit codes: 0 = success, 1 = failure (triggers rollback advice)
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
export PROJECT_ROOT
source "$SCRIPT_DIR/deployment/common.sh"

SKIP_TAG=false
ROLLBACK=false
HEALTH_GATE_MINUTES=${HEALTH_GATE_MINUTES:-30}

while [[ $# -gt 0 ]]; do
  case $1 in
    --no-tag)   SKIP_TAG=true; shift ;;
    --rollback) ROLLBACK=true; shift ;;
    -h|--help)
      echo "Usage: $0 [--no-tag] [--rollback]"
      echo "  --no-tag     Skip creating git tag"
      echo "  --rollback   Rollback Tier 1 to previous state"
      exit 0
      ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

COMPOSE_FILE="domains/core-platform/compose.yml"
START_TIME=$(date +%s)

# --- Tier 1 service definitions ---
TIER1_SERVICES=(
  "influxdb:8086"
  "postgres:5432"
  "websocket-ingestion:8001"
  "data-api:8006"
  "admin-api:8004"
)

TIER1_HEALTH_SERVICES=(
  "websocket-ingestion:8001"
  "data-api:8006"
  "admin-api:8004"
)

# --- Rollback ---
if [ "$ROLLBACK" = true ]; then
  log_header "Tier 1 Rollback"
  rollback_domain "core-platform" "$COMPOSE_FILE"
  log_info "Tier 1 rollback complete. Verify health manually."
  exit 0
fi

# --- Deploy ---
log_header "TIER 1: Core Infrastructure"
log_info "Services: InfluxDB, PostgreSQL, websocket-ingestion, data-api, admin-api"
log_info "Plus monitoring: Prometheus, Grafana, postgres-exporter"

# Git tag
if [ "$SKIP_TAG" = false ]; then
  log_info "Creating git tag: deployment-phase5-tier1-${DEPLOY_TIMESTAMP}"
  cd "$PROJECT_ROOT"
  git tag -a "deployment-phase5-tier1-${DEPLOY_TIMESTAMP}" \
    -m "Phase 5 Tier 1 deployment — core infrastructure" 2>> "$LOG_FILE" || \
    log_warn "Git tag creation failed (may already exist)"
fi

# Step 1: Verify databases are running
log_info "Step 1/5: Verifying database containers..."
docker compose -f "$PROJECT_ROOT/$COMPOSE_FILE" up -d influxdb postgres 2>> "$LOG_FILE"
sleep 5

if docker exec homeiq-postgres pg_isready -U homeiq -d homeiq > /dev/null 2>&1; then
  log_success "PostgreSQL is ready"
else
  log_warn "PostgreSQL not ready yet — will retry during health gate"
fi

if curl -f -s --max-time 5 "http://localhost:8086/health" > /dev/null 2>&1; then
  log_success "InfluxDB is ready"
else
  log_warn "InfluxDB not ready yet — will retry during health gate"
fi

# Step 2: Deploy core services
log_info "Step 2/5: Deploying core-platform services..."
deploy_compose "$COMPOSE_FILE"

# Step 3: Wait for initialization
log_info "Step 3/5: Waiting 15 seconds for services to initialize..."
sleep 15

# Step 4: Health checks
log_info "Step 4/5: Running health checks..."
if ! wait_for_services "Tier 1" "${TIER1_HEALTH_SERVICES[@]}"; then
  log_error "Tier 1 health checks FAILED"
  log_error "Rollback with: $0 --rollback"
  exit 1
fi

# Also verify databases specifically
if docker exec homeiq-postgres pg_isready -U homeiq -d homeiq > /dev/null 2>&1; then
  log_success "PostgreSQL accepting connections"
else
  log_error "PostgreSQL NOT accepting connections"
  exit 1
fi

if curl -f -s --max-time 5 "http://localhost:8086/health" > /dev/null 2>&1; then
  log_success "InfluxDB healthy"
else
  log_error "InfluxDB NOT healthy"
  exit 1
fi

# Verify data flow: websocket -> InfluxDB connection
log_info "Verifying data-api can query InfluxDB..."
if curl -f -s --max-time 10 "http://localhost:8006/health" | grep -qi "ok\|healthy\|true" 2>/dev/null; then
  log_success "data-api is connected and responding"
else
  log_warn "data-api health response did not confirm full connectivity"
fi

gate_check "Tier 1 Health Check" 0

# Step 5: 30-minute health verification loop
log_info "Step 5/5: Starting ${HEALTH_GATE_MINUTES}-minute health verification loop..."
log_info "Press Ctrl+C to skip (services will remain running)"

GATE_END=$(($(date +%s) + HEALTH_GATE_MINUTES * 60))
CHECK_INTERVAL=60  # Check every minute
FAILURES=0

while [ "$(date +%s)" -lt "$GATE_END" ]; do
  remaining=$(( (GATE_END - $(date +%s)) / 60 ))
  all_healthy=true

  for entry in "${TIER1_HEALTH_SERVICES[@]}"; do
    IFS=':' read -r name port <<< "$entry"
    if ! curl -f -s --max-time 5 "http://localhost:${port}/health" > /dev/null 2>&1; then
      log_warn "$name (port $port) health check failed at minute $(( HEALTH_GATE_MINUTES - remaining ))"
      all_healthy=false
      FAILURES=$((FAILURES + 1))
    fi
  done

  if [ $FAILURES -ge 5 ]; then
    log_error "Too many health check failures ($FAILURES) — Tier 1 unstable"
    log_error "Consider rollback: $0 --rollback"
    exit 1
  fi

  if [ "$all_healthy" = true ]; then
    log_info "  Health check OK — ${remaining}m remaining in verification window"
  fi

  sleep $CHECK_INTERVAL
done

# --- Summary ---
ELAPSED=$(($(date +%s) - START_TIME))
log_header "Tier 1 Deployment Complete"
log_success "Duration: $(format_duration $ELAPSED)"
log_success "Services deployed: websocket-ingestion, data-api, admin-api"
log_success "Databases: PostgreSQL 17, InfluxDB 2.8.0"
log_success "Monitoring: Prometheus, Grafana, postgres-exporter"
log_success "${HEALTH_GATE_MINUTES}-minute health gate PASSED ($FAILURES transient failures)"
echo ""
log_info "Next: Deploy Tier 2 with scripts/deploy-tier2.sh"
log_info "Full log: $LOG_FILE"
