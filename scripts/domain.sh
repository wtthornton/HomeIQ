#!/bin/bash
# domain.sh — Per-domain Docker Compose helper for HomeIQ.
# Usage: ./scripts/domain.sh <command> <domain> [service]
#
# Commands:
#   start    Start a domain's services
#   stop     Stop a domain's services
#   restart  Restart a domain's services
#   status   Show running containers for a domain
#   logs     Tail service logs (optional: specific service name)
#   build    Build domain images
#   list     Print valid domain names

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
  echo "Usage: $0 <command> <domain> [service]"
  echo ""
  echo "Commands:"
  echo "  start    Start a domain's services"
  echo "  stop     Stop a domain's services"
  echo "  restart  Restart a domain's services"
  echo "  status   Show running containers for a domain"
  echo "  logs     Tail service logs (optional: specific service name)"
  echo "  build    Build domain images"
  echo "  list     Print valid domain names"
  echo ""
  echo "Valid domains:"
  for d in "${VALID_DOMAINS[@]}"; do
    echo "  $d"
  done
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

# All other commands require a domain
if [[ -z "$DOMAIN" ]]; then
  usage
fi

validate_domain "$DOMAIN"

COMPOSE_FILE="$PROJECT_ROOT/domains/$DOMAIN/compose.yml"

if [[ ! -f "$COMPOSE_FILE" ]]; then
  echo -e "${RED}[ERROR]${NC} Compose file not found: $COMPOSE_FILE"
  exit 1
fi

case "$COMMAND" in
  start)
    echo -e "${GREEN}[START]${NC} Starting $DOMAIN..."
    "$SCRIPT_DIR/ensure-network.sh"
    docker compose -f "$COMPOSE_FILE" up -d
    echo -e "${GREEN}[OK]${NC} $DOMAIN started."
    ;;
  stop)
    echo -e "${YELLOW}[STOP]${NC} Stopping $DOMAIN..."
    docker compose -f "$COMPOSE_FILE" down
    echo -e "${GREEN}[OK]${NC} $DOMAIN stopped."
    ;;
  restart)
    echo -e "${YELLOW}[RESTART]${NC} Restarting $DOMAIN..."
    "$SCRIPT_DIR/ensure-network.sh"
    docker compose -f "$COMPOSE_FILE" restart
    echo -e "${GREEN}[OK]${NC} $DOMAIN restarted."
    ;;
  status)
    docker compose -f "$COMPOSE_FILE" ps
    ;;
  logs)
    if [[ -n "$SERVICE" ]]; then
      docker compose -f "$COMPOSE_FILE" logs -f "$SERVICE"
    else
      docker compose -f "$COMPOSE_FILE" logs -f
    fi
    ;;
  build)
    echo -e "${GREEN}[BUILD]${NC} Building $DOMAIN images..."
    docker compose -f "$COMPOSE_FILE" build
    echo -e "${GREEN}[OK]${NC} $DOMAIN images built."
    ;;
  *)
    echo -e "${RED}[ERROR]${NC} Unknown command: $COMMAND"
    usage
    ;;
esac
