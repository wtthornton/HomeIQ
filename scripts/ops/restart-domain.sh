#!/usr/bin/env bash
# restart-domain.sh <domain> — Graceful restart of a domain group with health verification
set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'
BOLD='\033[1m'

DOMAIN=${1:-""}
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE_FILE="domains/${DOMAIN}/compose.yml"
PROJECT_NAME="homeiq-${DOMAIN}"

VALID_DOMAINS="core-platform data-collectors ml-engine automation-core blueprints energy-analytics device-management pattern-analysis frontends"

if [ -z "$DOMAIN" ] || ! echo "$VALID_DOMAINS" | grep -qw "$DOMAIN"; then
  echo -e "${RED}Usage: $0 <domain>${NC}"
  echo -e "Valid domains: ${BLUE}${VALID_DOMAINS}${NC}"
  exit 1
fi

if [ ! -f "$COMPOSE_FILE" ]; then
  echo -e "${RED}Compose file not found: ${COMPOSE_FILE}${NC}"
  exit 1
fi

echo -e "${BOLD}${BLUE}Restarting domain: ${DOMAIN}${NC}"
echo ""

# Step 1: Graceful stop
echo -e "${YELLOW}[1/4] Stopping ${DOMAIN} services...${NC}"
docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" --profile production stop --timeout 30

# Step 2: Start services
echo -e "${YELLOW}[2/4] Starting ${DOMAIN} services...${NC}"
"${SCRIPT_DIR}/ensure-network.sh" 2>/dev/null || true
docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" --profile production up -d

# Step 3: Wait for health
echo -e "${YELLOW}[3/4] Waiting for services to become healthy...${NC}"
TIMEOUT=120
ELAPSED=0
INTERVAL=5

while [ "$ELAPSED" -lt "$TIMEOUT" ]; do
  UNHEALTHY=$(docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" ps --format json 2>/dev/null | \
    python3 -c "
import sys, json
unhealthy = 0
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    try:
        svc = json.loads(line)
        state = svc.get('Health', svc.get('State', ''))
        if state not in ('healthy', 'running'):
            unhealthy += 1
    except json.JSONDecodeError:
        pass
print(unhealthy)
" 2>/dev/null || echo "0")

  if [ "$UNHEALTHY" = "0" ]; then
    break
  fi

  echo -e "  Waiting... (${ELAPSED}s elapsed, ${UNHEALTHY} services not ready)"
  sleep "$INTERVAL"
  ELAPSED=$((ELAPSED + INTERVAL))
done

# Step 4: Verify
echo -e "${YELLOW}[4/4] Verifying service status...${NC}"
echo ""
docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" ps

if [ "$ELAPSED" -ge "$TIMEOUT" ]; then
  echo ""
  echo -e "${RED}WARNING: Some services may not be healthy after ${TIMEOUT}s timeout${NC}"
  exit 1
fi

echo ""
echo -e "${GREEN}${BOLD}✓ Domain '${DOMAIN}' restarted successfully${NC}"
