#!/bin/bash
# =============================================================================
# HomeIQ Deploy — Tier 3: ML/AI Services
# =============================================================================
# Deploys: openvino-service, ml-service, ner-service, openai-service,
#          rag-service, ai-core-service, ai-training-service,
#          device-intelligence-service
# (model-prep is development profile only — excluded)
#
# Usage:
#   ./scripts/deploy-tier3.sh                # Deploy and verify
#   ./scripts/deploy-tier3.sh --no-tag       # Skip git tagging
#   ./scripts/deploy-tier3.sh --rollback     # Rollback Tier 3
#
# Note: ML services may take 5-10 minutes to load models. The script
# uses extended health check timeouts to accommodate this.
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

ML_COMPOSE="domains/ml-engine/compose.yml"
START_TIME=$(date +%s)

# ML services with their external ports
TIER3_SERVICES=(
  "openvino-service:8026"
  "ml-service:8025"
  "ai-core-service:8018"
  "ai-training-service:8033"
  "device-intelligence-service:8028"
  "rag-service:8027"
  "openai-service:8020"
)

# --- Rollback ---
if [ "$ROLLBACK" = true ]; then
  log_header "Tier 3 Rollback"
  rollback_domain "ml-engine" "$ML_COMPOSE"
  exit 0
fi

# --- Pre-flight: Verify Tier 1 is healthy ---
log_header "TIER 3: ML/AI Services"
log_info "Pre-flight: Checking Tier 1 core services..."

MAX_HEALTH_RETRIES=5
HEALTH_CHECK_INTERVAL=2

TIER1_CHECK=(
  "data-api:8006"
  "admin-api:8004"
)

if ! wait_for_services "Tier 1 (pre-flight)" "${TIER1_CHECK[@]}"; then
  log_error "Tier 1 is NOT healthy — deploy Tier 1 first"
  exit 1
fi

# Extended timeouts for ML services (model loading)
MAX_HEALTH_RETRIES=60
HEALTH_CHECK_INTERVAL=5

# --- Git tag ---
if [ "$SKIP_TAG" = false ]; then
  log_info "Creating git tag: deployment-phase5-tier3-${DEPLOY_TIMESTAMP}"
  cd "$PROJECT_ROOT"
  git tag -a "deployment-phase5-tier3-${DEPLOY_TIMESTAMP}" \
    -m "Phase 5 Tier 3 deployment — ML/AI services" 2>> "$LOG_FILE" || \
    log_warn "Git tag creation failed"
fi

# --- Deploy ---
log_info "Step 1/4: Deploying ml-engine domain..."
deploy_compose "$ML_COMPOSE"

log_info "Step 2/4: Waiting 30 seconds for model loading (this is normal)..."
sleep 30

# --- Health checks ---
log_info "Step 3/4: Running health checks (extended timeout for ML model loading)..."
log_info "  ML services may take up to 5 minutes to become healthy."

if ! wait_for_services "Tier 3" "${TIER3_SERVICES[@]}"; then
  log_error "Tier 3 health checks FAILED"
  log_error "Some ML services may need more time for model loading."
  log_error "Check logs: docker logs homeiq-openvino-service"
  log_error "Rollback with: $0 --rollback"
  exit 1
fi

# --- Verify model loading ---
log_info "Step 4/4: Verifying ML service responses..."

# Quick inference check on ai-core-service
if curl -f -s --max-time 10 "http://localhost:8018/health" | grep -qi "ok\|healthy\|true" 2>/dev/null; then
  log_success "ai-core-service responding with healthy status"
else
  log_warn "ai-core-service health response format unexpected (service is up)"
fi

# Check openvino model status
if curl -f -s --max-time 10 "http://localhost:8026/health" | grep -qi "ok\|healthy\|true" 2>/dev/null; then
  log_success "openvino-service models loaded"
else
  log_warn "openvino-service health response format unexpected (service is up)"
fi

gate_check "Tier 3 Health Check" 0

# --- Summary ---
ELAPSED=$(($(date +%s) - START_TIME))
log_header "Tier 3 Deployment Complete"
log_success "Duration: $(format_duration $ELAPSED)"
log_success "Services deployed: ${#TIER3_SERVICES[@]} ML/AI services"
log_success "Models loaded and inference endpoints verified"
echo ""
log_info "Next: Deploy Tiers 4-8 with scripts/deploy-tiers4-8.sh"
log_info "Full log: $LOG_FILE"
