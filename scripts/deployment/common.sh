#!/bin/bash
# =============================================================================
# HomeIQ Deployment — Shared Functions
# =============================================================================
# Sourced by all deploy-tier*.sh scripts. Do not run directly.
# =============================================================================

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Defaults
DEPLOY_TIMESTAMP=${DEPLOY_TIMESTAMP:-$(date +%Y%m%d_%H%M%S)}
LOG_DIR="${SCRIPT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}/../logs/deployment"
mkdir -p "$LOG_DIR"
LOG_FILE="${LOG_DIR}/deploy_${DEPLOY_TIMESTAMP}.log"
MAX_HEALTH_RETRIES=${MAX_HEALTH_RETRIES:-30}
HEALTH_CHECK_INTERVAL=${HEALTH_CHECK_INTERVAL:-2}
PROJECT_ROOT="${PROJECT_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"

# --- Logging ---

log_info()    { echo -e "${BLUE}[INFO  $(date +'%H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"; }
log_success() { echo -e "${GREEN}[OK    $(date +'%H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"; }
log_error()   { echo -e "${RED}[ERROR $(date +'%H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"; }
log_warn()    { echo -e "${YELLOW}[WARN  $(date +'%H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"; }
log_header()  {
  echo "" | tee -a "$LOG_FILE"
  echo -e "${CYAN}==========================================${NC}" | tee -a "$LOG_FILE"
  echo -e "${CYAN} $1${NC}" | tee -a "$LOG_FILE"
  echo -e "${CYAN}==========================================${NC}" | tee -a "$LOG_FILE"
}

# --- Health checks ---

# check_health PORT SERVICE_NAME [ENDPOINT]
# Returns 0 on success, 1 on failure after retries.
check_health() {
  local port=$1
  local name=$2
  local endpoint=${3:-/health}
  local retries=0

  while [ $retries -lt $MAX_HEALTH_RETRIES ]; do
    if curl -f -s --max-time 5 "http://localhost:${port}${endpoint}" > /dev/null 2>&1; then
      log_success "$name (port $port) is healthy"
      return 0
    fi
    retries=$((retries + 1))
    if [ $retries -lt $MAX_HEALTH_RETRIES ]; then
      log_warn "$name (port $port) not ready — retry $retries/$MAX_HEALTH_RETRIES"
      sleep "$HEALTH_CHECK_INTERVAL"
    fi
  done

  log_error "$name (port $port) FAILED health check after $MAX_HEALTH_RETRIES attempts"
  return 1
}

# wait_for_services TIER_NAME "name:port[:endpoint]" ...
# Checks all listed services. Returns 1 on first failure.
wait_for_services() {
  local tier=$1; shift
  local services=("$@")
  local failed=0

  log_info "Waiting for $tier services to become healthy..."

  for entry in "${services[@]}"; do
    IFS=':' read -r name port endpoint <<< "$entry"
    endpoint=${endpoint:-/health}
    if ! check_health "$port" "$name" "$endpoint"; then
      failed=$((failed + 1))
    fi
  done

  if [ $failed -eq 0 ]; then
    log_success "All $tier services are healthy ($((${#services[@]}))/${#services[@]})"
    return 0
  else
    log_error "$failed of ${#services[@]} $tier services FAILED health checks"
    return 1
  fi
}

# --- Gate ---

# gate_check GATE_NAME EXIT_CODE
# Halts the script on failure (non-zero).
gate_check() {
  local gate=$1
  local result=$2

  if [ "$result" -eq 0 ]; then
    log_success "GATE PASSED: $gate"
    return 0
  else
    log_error "GATE FAILED: $gate — deployment halted"
    log_error "Review logs: $LOG_FILE"
    exit 1
  fi
}

# --- Rollback helper ---

# rollback_domain DOMAIN_NAME COMPOSE_FILE
rollback_domain() {
  local domain=$1
  local compose_file=$2

  log_warn "Rolling back $domain..."
  docker compose -f "$PROJECT_ROOT/$compose_file" down 2>> "$LOG_FILE" || true
  docker compose -f "$PROJECT_ROOT/$compose_file" up -d 2>> "$LOG_FILE"
  log_info "$domain rollback initiated — check health manually"
}

# --- Compose helper ---

# deploy_compose COMPOSE_FILE [EXTRA_ARGS...]
deploy_compose() {
  local compose_file="$PROJECT_ROOT/$1"; shift
  log_info "docker compose -f $compose_file up -d $*"
  docker compose -f "$compose_file" up -d "$@" 2>> "$LOG_FILE"
}

# --- Duration ---

format_duration() {
  local seconds=$1
  printf '%02d:%02d:%02d' $((seconds/3600)) $(((seconds%3600)/60)) $((seconds%60))
}
