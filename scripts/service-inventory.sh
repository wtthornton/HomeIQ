#!/bin/bash
# Service Inventory Script
# Generates a comprehensive inventory of HomeIQ services for documentation verification

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=== HomeIQ Service Inventory ==="
echo "Generated: $(date)"
echo ""

# Count services defined in docker-compose.yml
echo "📋 Services Defined in docker-compose.yml:"
DEFINED_COUNT=$(cd "$PROJECT_ROOT" && docker compose config --services 2>/dev/null | wc -l | tr -d ' ')
echo "   Total: ${GREEN}${DEFINED_COUNT}${NC} services"
echo ""

# List all defined services
echo "   Services list:"
cd "$PROJECT_ROOT"
docker compose config --services 2>/dev/null | sort | nl -w2 -s'. ' | sed 's/^/      /'
echo ""

# Count running containers
echo "🚀 Currently Running Containers:"
RUNNING_COUNT=$(docker ps --format "{{.Names}}" 2>/dev/null | wc -l | tr -d ' ')
HOMEIQ_RUNNING=$(docker ps --filter "name=homeiq" --format "{{.Names}}" 2>/dev/null | wc -l | tr -d ' ')
echo "   Total running: ${GREEN}${RUNNING_COUNT}${NC} containers"
echo "   HomeIQ services: ${GREEN}${HOMEIQ_RUNNING}${NC} containers (with 'homeiq-' prefix)"
echo ""

# Show container status
echo "📊 Container Status:"
echo ""
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.State}}" 2>/dev/null | sed 's/^/   /'
echo ""

# Health status summary
echo "🏥 Health Status Summary:"
HEALTHY=$(docker ps --filter "health=healthy" --format "{{.Names}}" 2>/dev/null | wc -l | tr -d ' ')
UNHEALTHY=$(docker ps --filter "health=unhealthy" --format "{{.Names}}" 2>/dev/null | wc -l | tr -d ' ')
NO_HEALTH_CHECK=$(docker ps --format "{{.Names}}" 2>/dev/null | wc -l | tr -d ' ')
NO_HEALTH_CHECK=$((NO_HEALTH_CHECK - HEALTHY - UNHEALTHY))

echo "   Healthy: ${GREEN}${HEALTHY}${NC}"
if [ "$UNHEALTHY" -gt 0 ]; then
    echo "   Unhealthy: ${RED}${UNHEALTHY}${NC}"
    echo "   Unhealthy containers:"
    docker ps --filter "health=unhealthy" --format "      - {{.Names}}" 2>/dev/null
fi
echo "   No health check: ${YELLOW}${NO_HEALTH_CHECK}${NC}"
echo ""

# Check for containers without homeiq- prefix
echo "⚠️  Container Naming Check:"
NON_STANDARD=$(docker ps --format "{{.Names}}" 2>/dev/null | grep -v "^homeiq-" | grep -v "^NAMES$" | wc -l | tr -d ' ')
if [ "$NON_STANDARD" -gt 0 ]; then
    echo "   Containers without 'homeiq-' prefix: ${YELLOW}${NON_STANDARD}${NC}"
    docker ps --format "{{.Names}}" 2>/dev/null | grep -v "^homeiq-" | grep -v "^NAMES$" | sed 's/^/      - /'
else
    echo "   ${GREEN}✓ All containers use 'homeiq-' prefix${NC}"
fi
echo ""

# Profile-based services check
echo "📌 Profile-Based Services:"
PROFILE_SERVICES=$(cd "$PROJECT_ROOT" && docker compose config --services 2>/dev/null | while read -r service; do
    if grep -A 5 "^  ${service}:" docker-compose.yml 2>/dev/null | grep -q "profiles:"; then
        echo "$service"
    fi
done)

if [ -n "$PROFILE_SERVICES" ]; then
    echo "$PROFILE_SERVICES" | sed 's/^/      - /'
    echo "   Note: These services require --profile production to run"
else
    echo "   ${GREEN}✓ No profile-based services found${NC}"
fi
echo ""

# Summary
echo "📈 Summary:"
echo "   Defined: ${DEFINED_COUNT} services"
echo "   Running: ${RUNNING_COUNT} containers"
echo "   Healthy: ${HEALTHY} containers"
if [ "$RUNNING_COUNT" -ne "$DEFINED_COUNT" ]; then
    DIFF=$((RUNNING_COUNT - DEFINED_COUNT))
    if [ "$DIFF" -gt 0 ]; then
        echo "   ${YELLOW}⚠ Difference: +${DIFF} containers (may include test services or external containers)${NC}"
    else
        echo "   ${YELLOW}⚠ Difference: ${DIFF} containers (some services may be stopped)${NC}"
    fi
else
    echo "   ${GREEN}✓ All defined services are running${NC}"
fi
echo ""

echo "=== End of Service Inventory ==="
