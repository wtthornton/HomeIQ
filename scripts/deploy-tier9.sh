#!/bin/bash
# =============================================================================
# HomeIQ Deploy — Tier 9: Frontends & Observability
# =============================================================================
# Deploys: Jaeger, observability-dashboard, ai-automation-ui
# (health-dashboard was deployed in Tier 2)
#
# Usage:
#   ./scripts/deploy-tier9.sh                # Deploy and verify
#   ./scripts/deploy-tier9.sh --no-tag       # Skip git tagging
#   ./scripts/deploy-tier9.sh --rollback     # Rollback Tier 9
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
export PROJECT_ROOT
source "$SCRIPT_DIR/deployment/common.sh"

SKIP_TAG=false
ROLLBACK=false

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

FE_COMPOSE="domains/frontends/compose.yml"
START_TIME=$(date +%s)

TIER9_SERVICES=(
  "jaeger:16686:/"
  "observability-dashboard:8501:/_stcore/health"
  "ai-automation-ui:3001:/health"
)

# --- Rollback ---
if [ "$ROLLBACK" = true ]; then
  log_header "Tier 9 Rollback"
  rollback_domain "frontends" "$FE_COMPOSE"
  exit 0
fi

# --- Pre-flight: Verify core backend is healthy ---
log_header "TIER 9: Frontends & Observability"
log_info "Pre-flight: Checking backend services..."

MAX_HEALTH_RETRIES=5
HEALTH_CHECK_INTERVAL=2

BACKEND_CHECKS=(
  "data-api:8006"
  "admin-api:8004"
  "health-dashboard:3000"
)

if ! wait_for_services "Backend (pre-flight)" "${BACKEND_CHECKS[@]}"; then
  log_error "Backend services are NOT healthy — deploy earlier tiers first"
  exit 1
fi

MAX_HEALTH_RETRIES=20
HEALTH_CHECK_INTERVAL=3

# --- Git tag ---
if [ "$SKIP_TAG" = false ]; then
  log_info "Creating git tag: deployment-phase5-tier9-${DEPLOY_TIMESTAMP}"
  cd "$PROJECT_ROOT"
  git tag -a "deployment-phase5-tier9-${DEPLOY_TIMESTAMP}" \
    -m "Phase 5 Tier 9 deployment — frontends & observability" 2>> "$LOG_FILE" || \
    log_warn "Git tag creation failed"
fi

# --- Deploy ---
log_info "Step 1/4: Deploying frontends domain..."
deploy_compose "$FE_COMPOSE"

log_info "Step 2/4: Waiting 10 seconds for services to initialize..."
sleep 10

# --- Health checks ---
log_info "Step 3/4: Running health checks..."
if ! wait_for_services "Tier 9" "${TIER9_SERVICES[@]}"; then
  log_error "Tier 9 health checks FAILED"
  log_error "Rollback with: $0 --rollback"
  exit 1
fi

gate_check "Tier 9 Health Check" 0

# --- Accessibility verification ---
log_info "Step 4/4: Verifying frontend accessibility..."

# health-dashboard (Tier 2 but verify it's still up)
if curl -f -s --max-time 10 "http://localhost:3000" > /dev/null 2>&1; then
  log_success "health-dashboard (port 3000) is accessible"
else
  log_warn "health-dashboard (port 3000) not accessible"
fi

# ai-automation-ui
if curl -f -s --max-time 10 "http://localhost:3001" > /dev/null 2>&1; then
  log_success "ai-automation-ui (port 3001) is accessible"
else
  log_warn "ai-automation-ui (port 3001) not accessible"
fi

# observability-dashboard (Streamlit)
if curl -f -s --max-time 10 "http://localhost:8501" > /dev/null 2>&1; then
  log_success "observability-dashboard (port 8501) is accessible"
else
  log_warn "observability-dashboard (port 8501) not accessible"
fi

# Jaeger UI
if curl -f -s --max-time 10 "http://localhost:16686" > /dev/null 2>&1; then
  log_success "Jaeger UI (port 16686) is accessible"
else
  log_warn "Jaeger UI (port 16686) not accessible"
fi

# Grafana (from Tier 1 monitoring)
if curl -f -s --max-time 10 "http://localhost:3002/api/health" > /dev/null 2>&1; then
  log_success "Grafana (port 3002) is accessible"
else
  log_warn "Grafana (port 3002) not accessible"
fi

# --- Cross-app switcher test ---
log_info "Verifying cross-app switcher endpoints..."
for url in "http://localhost:3000" "http://localhost:3001" "http://localhost:8501"; do
  if curl -f -s --max-time 5 "$url" > /dev/null 2>&1; then
    log_success "  $url — reachable"
  else
    log_warn "  $url — not reachable"
  fi
done

# --- Summary ---
ELAPSED=$(($(date +%s) - START_TIME))
log_header "Tier 9 Deployment Complete"
log_success "Duration: $(format_duration $ELAPSED)"
log_success "Frontends: health-dashboard, ai-automation-ui, observability-dashboard"
log_success "Observability: Jaeger (tracing), Grafana (metrics), Prometheus (scraping)"
echo ""
log_success "ALL TIERS DEPLOYED SUCCESSFULLY"
echo ""
log_info "Frontend URLs:"
log_info "  Health Dashboard:        http://localhost:3000"
log_info "  AI Automation UI:        http://localhost:3001"
log_info "  Observability Dashboard: http://localhost:8501"
log_info "  Jaeger Tracing:          http://localhost:16686"
log_info "  Grafana Metrics:         http://localhost:3002"
echo ""
log_info "Next: Start post-deployment monitoring with scripts/post-deployment-monitor.sh"
log_info "Full log: $LOG_FILE"
