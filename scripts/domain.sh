#!/bin/bash
# domain.sh — Per-domain Docker Compose helper for HomeIQ.
# Usage: ./scripts/domain.sh <command> <domain> [service]
#
# Commands:
#   start    Start a domain's services (includes production-profile services)
#   stop     Stop a domain's services
#   restart  Restart a domain's services
#   status   Show running containers for a domain
#   logs     Tail service logs (optional: specific service name)
#   build    Build domain images
#   list     Print valid domain names
#   verify   Check all running containers belong to correct Docker project group
#
# Always uses --profile production (air-quality, carbon-intensity, etc.).
#
# IMPORTANT: Always use this script (or start-stack.sh) to manage domains.
# Never run 'docker compose up' from the root docker-compose.yml with
# --profile production — that assigns the root 'homeiq' project name
# instead of the domain's 'homeiq-<domain>' name, causing containers
# to appear in the wrong Docker Desktop group.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

VALID_DOMAINS=(
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

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

usage() {
  echo "Usage: $0 <command> <domain> [service] [--all-profiles]"
  echo ""
  echo "Commands:"
  echo "  start    Start a domain's services"
  echo "  stop     Stop a domain's services"
  echo "  restart  Restart a domain's services"
  echo "  status   Show running containers for a domain"
  echo "  logs     Tail service logs (optional: specific service name)"
  echo "  build    Build domain images"
  echo "  list     Print valid domain names"
  echo "  verify   Check all containers are in correct Docker project groups"
  echo ""
  echo "Valid domains:"
  for d in "${VALID_DOMAINS[@]}"; do
    echo "  $d"
  done
  echo ""
  echo "IMPORTANT: Always use this script to manage domains. Never run"
  echo "'docker compose up --profile production' from the project root —"
  echo "it assigns the wrong project name to containers."
  exit 1
}

validate_domain() {
  local domain="$1"
  for d in "${VALID_DOMAINS[@]}"; do
    if [[ "$d" == "$domain" ]]; then
      return 0
    fi
  done
  echo -e "${RED}[ERROR]${NC} Invalid domain: $domain"
  echo ""
  echo "Valid domains:"
  for d in "${VALID_DOMAINS[@]}"; do
    echo "  $d"
  done
  exit 1
}

COMMAND="${1:-}"
DOMAIN="${2:-}"
SERVICE="${3:-}"

if [[ -z "$COMMAND" ]]; then
  usage
fi

# Handle list command (no domain required)
if [[ "$COMMAND" == "list" ]]; then
  for d in "${VALID_DOMAINS[@]}"; do
    echo "$d"
  done
  exit 0
fi

# Handle verify command (no domain required — checks all containers)
if [[ "$COMMAND" == "verify" ]]; then
  echo -e "${GREEN}[VERIFY]${NC} Checking Docker project group assignments..."
  ERRORS=0
  # Check for orphan containers in root 'homeiq' project (from docker compose up at root)
  while IFS=$'\t' read -r name project; do
    if [[ -n "$name" && "$project" == "homeiq" ]]; then
      echo -e "${RED}[MISMATCH]${NC} $name is in orphan project 'homeiq' — should be in homeiq-<domain>"
      echo "  Fix: docker compose --profile production down && ./scripts/start-stack.sh"
      ERRORS=$((ERRORS + 1))
    fi
  done < <(docker ps -a --filter "name=homeiq-" --format "{{.Names}}\t{{.Label \"com.docker.compose.project\"}}" 2>/dev/null)
  if [[ $ERRORS -eq 0 ]]; then
    echo -e "${GREEN}[OK]${NC} All containers are in the correct Docker project groups."
  else
    echo ""
    echo -e "${RED}[FAIL]${NC} $ERRORS container(s) in wrong project group."
    echo "This usually happens when services are started via the root docker-compose.yml."
    echo "Always use './scripts/start-stack.sh' or './scripts/domain.sh start <domain>' instead."
    exit 1
  fi
  exit 0
fi

# All other commands require a domain
if [[ -z "$DOMAIN" ]]; then
  usage
fi

validate_domain "$DOMAIN"

COMPOSE_FILE="$PROJECT_ROOT/domains/$DOMAIN/compose.yml"
ENV_FILE="$PROJECT_ROOT/.env"
ENV_FILE_FLAG=""
if [[ -f "$ENV_FILE" ]]; then
  ENV_FILE_FLAG="--env-file $ENV_FILE"
fi

if [[ ! -f "$COMPOSE_FILE" ]]; then
  echo -e "${RED}[ERROR]${NC} Compose file not found: $COMPOSE_FILE"
  exit 1
fi

case "$COMMAND" in
  start)
    echo -e "${GREEN}[START]${NC} Starting $DOMAIN..."
    "$SCRIPT_DIR/ensure-network.sh"
    docker compose -f "$COMPOSE_FILE" $ENV_FILE_FLAG --profile production up -d ${SERVICE:+"$SERVICE"}
    echo -e "${GREEN}[OK]${NC} $DOMAIN started."
    ;;
  stop)
    echo -e "${YELLOW}[STOP]${NC} Stopping $DOMAIN..."
    docker compose -f "$COMPOSE_FILE" $ENV_FILE_FLAG --profile production down
    echo -e "${GREEN}[OK]${NC} $DOMAIN stopped."
    ;;
  restart)
    echo -e "${YELLOW}[RESTART]${NC} Restarting $DOMAIN..."
    "$SCRIPT_DIR/ensure-network.sh"
    docker compose -f "$COMPOSE_FILE" $ENV_FILE_FLAG --profile production down
    docker compose -f "$COMPOSE_FILE" $ENV_FILE_FLAG --profile production up -d ${SERVICE:+"$SERVICE"}
    echo -e "${GREEN}[OK]${NC} $DOMAIN restarted."
    ;;
  status)
    docker compose -f "$COMPOSE_FILE" $ENV_FILE_FLAG --profile production ps
    ;;
  logs)
    if [[ -n "$SERVICE" ]]; then
      docker compose -f "$COMPOSE_FILE" $ENV_FILE_FLAG logs -f "$SERVICE"
    else
      docker compose -f "$COMPOSE_FILE" $ENV_FILE_FLAG logs -f
    fi
    ;;
  build)
    echo -e "${GREEN}[BUILD]${NC} Building $DOMAIN images..."
    docker compose -f "$COMPOSE_FILE" $ENV_FILE_FLAG --profile production build ${SERVICE:+"$SERVICE"}
    echo -e "${GREEN}[OK]${NC} $DOMAIN images built."
    ;;
  *)
    echo -e "${RED}[ERROR]${NC} Unknown command: $COMMAND"
    usage
    ;;
esac
