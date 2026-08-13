#!/bin/bash
# start-stack.sh — Start all 9 HomeIQ domains in dependency order.
# Each domain launches as a separate Docker Desktop group (via compose name: directive).
#
# Usage:
#   ./scripts/start-stack.sh              # Full stack (includes production-profile services)
#   ./scripts/start-stack.sh --skip-wait  # Skip health polling after core-platform
#
# IMPORTANT: This script starts each domain via its own compose file to ensure
# containers get the correct 'homeiq-<domain>' project name in Docker Desktop.
# Never use the root docker-compose.yml with --profile production directly.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

SKIP_WAIT=false
for arg in "$@"; do
  case "$arg" in
    --skip-wait) SKIP_WAIT=true ;;
  esac
done

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

DOMAINS=(
  core-platform
  data-collectors
  ml-engine
  automation-core
  blueprints
  energy-analytics
  device-management
  pattern-analysis
  frontends
)

log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_ok()      { echo -e "${GREEN}[OK]${NC} $1"; }
log_waiting() { echo -e "${YELLOW}[WAITING]${NC} $1"; }
log_timeout() { echo -e "${RED}[TIMEOUT]${NC} $1"; }

# Ensure the shared Docker network exists
log_info "Ensuring homeiq-network exists..."
"$SCRIPT_DIR/ensure-network.sh"
echo ""

# Poll a health endpoint until it responds 200 or timeout
wait_for_health() {
  local url="$1"
  local label="$2"
  local timeout=60
  local interval=5
  local elapsed=0

  while [[ $elapsed -lt $timeout ]]; do
    if curl -sf "$url" > /dev/null 2>&1; then
      log_ok "$label is healthy"
      return 0
    fi
    log_waiting "$label not ready yet (${elapsed}s / ${timeout}s)..."
    sleep $interval
    elapsed=$((elapsed + interval))
  done

  log_timeout "$label did not become healthy within ${timeout}s"
  return 1
}

# Start each domain
start_domain() {
  local domain="$1"
  local compose_file="$PROJECT_ROOT/domains/$domain/compose.yml"
  local env_file_flag=""
  if [[ -f "$PROJECT_ROOT/.env" ]]; then
    env_file_flag="--env-file $PROJECT_ROOT/.env"
  fi

  if [[ ! -f "$compose_file" ]]; then
    echo -e "${RED}[ERROR]${NC} Compose file not found: $compose_file"
    return 1
  fi

  log_info "Starting $domain..."
  # `--build` alone is enough to pick up source changes: the Dockerfiles COPY
  # specific paths, so BuildKit reuses every layer whose inputs are unchanged and
  # a normal start is almost entirely cache hits.
  #
  # `--pull always` and `--force-recreate` are NOT defaults because they defeat
  # that: the first re-fetches every base image from the registry on each start
  # (slow, and needs the network), and the second tears down and recreates all 58
  # containers even when nothing about them changed. Set STACK_REFRESH=1 for the
  # old behaviour when you genuinely want fresh base images and clean containers.
  local refresh_flags=""
  if [[ "${STACK_REFRESH:-0}" == "1" ]]; then
    refresh_flags="--pull always --force-recreate"
  fi
  docker compose -f "$compose_file" $env_file_flag --profile production up -d --build $refresh_flags
  log_ok "$domain started."
}

# --- Ordered startup ---

# Required env keys must exist BEFORE anything starts: the 2026-08-01 .env
# rewrite silently dropped 55 populated keys and nothing failed loudly for
# ten days (TAP-5902).
if ! bash "$SCRIPT_DIR/preflight-env.sh"; then
  echo -e "${RED}[ERROR]${NC} Env preflight failed — not starting the stack."
  exit 1
fi

# 1. core-platform (critical — other domains depend on it)
start_domain "core-platform"

if [[ "$SKIP_WAIT" == "false" ]]; then
  log_info "Waiting for core-platform dependencies..."
  wait_for_health "http://localhost:8086/health" "influxdb" || true
  wait_for_health "http://localhost:8006/health" "data-api" || true
  echo ""
fi

# 2-9. Remaining domains (no inter-dependencies requiring waits)
for domain in "${DOMAINS[@]:1}"; do
  start_domain "$domain"
done

# --- Verify project groups ---
echo ""
log_info "Verifying Docker project group assignments..."
"$SCRIPT_DIR/domain.sh" verify || log_timeout "Some containers in wrong project group — run './scripts/domain.sh verify' for details."

# --- Summary ---
echo ""
echo "=========================================="
echo -e "${GREEN}HomeIQ Full Stack Started${NC}"
echo "=========================================="
for domain in "${DOMAINS[@]}"; do
  echo -e "  ${GREEN}*${NC} $domain"
done
echo ""
echo "Use './scripts/domain.sh status <domain>' to check individual domains."
echo "Use './scripts/domain.sh logs <domain> [service]' to view logs."
echo "Use './scripts/domain.sh verify' to check project group assignments."
echo "=========================================="
