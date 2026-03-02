#!/bin/bash
# =============================================================================
# HomeIQ Deploy — Tiers 4-8: Domain Services
# =============================================================================
# Deploys in order:
#   Tier 4: automation-core    (7 services)
#   Tier 5: blueprints         (4 services)
#   Tier 6: energy-analytics   (3 services)
#   Tier 7: device-management  (8 services)
#   Tier 8: pattern-analysis   (2 services)
#
# Usage:
#   ./scripts/deploy-tiers4-8.sh               # Deploy all tiers 4-8
#   ./scripts/deploy-tiers4-8.sh --tier 4      # Deploy only tier 4
#   ./scripts/deploy-tiers4-8.sh --no-tag      # Skip git tagging
#   ./scripts/deploy-tiers4-8.sh --rollback 4  # Rollback specific tier
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
export PROJECT_ROOT
source "$SCRIPT_DIR/deployment/common.sh"

SKIP_TAG=false
SINGLE_TIER=""
ROLLBACK_TIER=""

while [[ $# -gt 0 ]]; do
  case $1 in
    --no-tag)       SKIP_TAG=true; shift ;;
    --tier)         SINGLE_TIER="$2"; shift 2 ;;
    --rollback)     ROLLBACK_TIER="$2"; shift 2 ;;
    -h|--help)
      echo "Usage: $0 [--no-tag] [--tier N] [--rollback N]"
      echo "  --tier N       Deploy only tier N (4-8)"
      echo "  --rollback N   Rollback tier N"
      exit 0
      ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

START_TIME=$(date +%s)

# --- Compose file mapping ---
declare -A COMPOSE_FILES=(
  [4]="domains/automation-core/compose.yml"
  [5]="domains/blueprints/compose.yml"
  [6]="domains/energy-analytics/compose.yml"
  [7]="domains/device-management/compose.yml"
  [8]="domains/pattern-analysis/compose.yml"
)

declare -A TIER_NAMES=(
  [4]="automation-core"
  [5]="blueprints"
  [6]="energy-analytics"
  [7]="device-management"
  [8]="pattern-analysis"
)

# Service health checks per tier (name:external_port)
# Tier 4: automation-core
TIER4_SERVICES=(
  "ha-ai-agent-service:8030"
  "ai-automation-service-new:8036"
  "ai-query-service:8035"
  "yaml-validation-service:8037"
  "automation-linter:8016"
  "automation-trace-service:8044"
)

# Tier 5: blueprints
TIER5_SERVICES=(
  "blueprint-index:8038"
  "blueprint-suggestion-service:8039"
  "rule-recommendation-ml:8040:/api/v1/health"
  "automation-miner:8029"
)

# Tier 6: energy-analytics
TIER6_SERVICES=(
  "energy-correlator:8017"
  "energy-forecasting:8042:/api/v1/health"
  "proactive-agent-service:8031"
)

# Tier 7: device-management
TIER7_SERVICES=(
  "device-health-monitor:8019"
  "device-context-classifier:8032"
  "device-setup-assistant:8021"
  "device-database-client:8022"
  "device-recommender:8023"
  "activity-writer:8045"
  "ha-setup-service:8024"
)

# Tier 8: pattern-analysis
TIER8_SERVICES=(
  "ai-pattern-service:8034"
  "api-automation-edge:8041"
)

# --- Rollback ---
if [ -n "$ROLLBACK_TIER" ]; then
  if [ -z "${COMPOSE_FILES[$ROLLBACK_TIER]+x}" ]; then
    echo "Invalid tier: $ROLLBACK_TIER (valid: 4-8)"
    exit 1
  fi
  log_header "Tier $ROLLBACK_TIER Rollback"
  rollback_domain "${TIER_NAMES[$ROLLBACK_TIER]}" "${COMPOSE_FILES[$ROLLBACK_TIER]}"
  exit 0
fi

# --- Pre-flight ---
log_header "TIERS 4-8: Domain Services"
log_info "Pre-flight: Checking Tier 1 core services..."

MAX_HEALTH_RETRIES=5
HEALTH_CHECK_INTERVAL=2

if ! wait_for_services "Tier 1 (pre-flight)" "data-api:8006" "admin-api:8004"; then
  log_error "Tier 1 is NOT healthy — deploy Tier 1 first"
  exit 1
fi

MAX_HEALTH_RETRIES=30
HEALTH_CHECK_INTERVAL=3

# --- Deploy a single tier ---
deploy_tier() {
  local tier_num=$1
  local compose_file="${COMPOSE_FILES[$tier_num]}"
  local tier_name="${TIER_NAMES[$tier_num]}"

  log_header "Tier $tier_num: $tier_name"

  # Deploy
  log_info "Deploying $tier_name..."
  deploy_compose "$compose_file"
  sleep 10

  # Get the right service array
  local -n services="TIER${tier_num}_SERVICES"

  # Health checks
  log_info "Running health checks for Tier $tier_num..."
  if ! wait_for_services "Tier $tier_num ($tier_name)" "${services[@]}"; then
    log_error "Tier $tier_num health checks FAILED"
    log_error "Rollback with: $0 --rollback $tier_num"
    return 1
  fi

  gate_check "Tier $tier_num ($tier_name)" 0
  return 0
}

# --- Git tag ---
if [ "$SKIP_TAG" = false ]; then
  log_info "Creating git tag: deployment-phase5-tiers4-8-${DEPLOY_TIMESTAMP}"
  cd "$PROJECT_ROOT"
  git tag -a "deployment-phase5-tiers4-8-${DEPLOY_TIMESTAMP}" \
    -m "Phase 5 Tiers 4-8 deployment — domain services" 2>> "$LOG_FILE" || \
    log_warn "Git tag creation failed"
fi

# --- Deploy tiers ---
if [ -n "$SINGLE_TIER" ]; then
  if [ -z "${COMPOSE_FILES[$SINGLE_TIER]+x}" ]; then
    echo "Invalid tier: $SINGLE_TIER (valid: 4-8)"
    exit 1
  fi
  deploy_tier "$SINGLE_TIER"
else
  for tier in 4 5 6 7 8; do
    if ! deploy_tier "$tier"; then
      log_error "Stopping deployment at Tier $tier due to failures"
      log_error "Previously deployed tiers remain running"
      exit 1
    fi
  done
fi

# --- Cross-group communication verification ---
log_header "Cross-Group Communication Verification"

log_info "Checking cross-group connectivity..."
CROSS_CHECKS=(
  "ha-ai-agent -> data-api:8006"
  "energy-correlator -> influxdb:8086"
  "proactive-agent -> ha-ai-agent:8030"
  "blueprint-suggestion -> blueprint-index:8038"
)

for check in "${CROSS_CHECKS[@]}"; do
  IFS=':' read -r desc port <<< "$check"
  if curl -f -s --max-time 5 "http://localhost:${port}/health" > /dev/null 2>&1; then
    log_success "  $desc — OK"
  else
    log_warn "  $desc — service not responding (may be expected)"
  fi
done

# --- Summary ---
ELAPSED=$(($(date +%s) - START_TIME))
log_header "Tiers 4-8 Deployment Complete"
log_success "Duration: $(format_duration $ELAPSED)"
log_success "Tier 4 (automation-core): ${#TIER4_SERVICES[@]} services"
log_success "Tier 5 (blueprints): ${#TIER5_SERVICES[@]} services"
log_success "Tier 6 (energy-analytics): ${#TIER6_SERVICES[@]} services"
log_success "Tier 7 (device-management): ${#TIER7_SERVICES[@]} services"
log_success "Tier 8 (pattern-analysis): ${#TIER8_SERVICES[@]} services"
echo ""
log_info "Next: Deploy Tier 9 (frontends) with scripts/deploy-tier9.sh"
log_info "Full log: $LOG_FILE"
