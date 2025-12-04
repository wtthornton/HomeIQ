#!/bin/bash

# Deploy YAML Validation Consolidation Changes
# This script rebuilds and restarts the affected services

set -e  # Exit on error

echo "🚀 Deploying YAML Validation Consolidation Changes..."
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose not found. Please install docker-compose."
    exit 1
fi

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

cd "$PROJECT_ROOT"

echo -e "${BLUE}📋 Services to update:${NC}"
echo "  1. ai-automation-service (new validation router)"
echo "  2. ha-ai-agent-service (new client, updated validation)"
echo "  3. ai-automation-ui (updated API and Deployed page)"
echo ""

# Function to rebuild and restart a service
rebuild_service() {
    local service_name=$1
    local description=$2
    
    echo -e "${YELLOW}🔨 Rebuilding ${description}...${NC}"
    docker-compose build --no-cache "$service_name" || {
        echo -e "❌ Failed to build ${service_name}"
        return 1
    }
    
    echo -e "${GREEN}✅ ${description} rebuilt successfully${NC}"
    echo ""
}

# Function to restart a service (for services with mounted volumes)
restart_service() {
    local service_name=$1
    local description=$2
    
    echo -e "${YELLOW}🔄 Restarting ${description}...${NC}"
    docker-compose restart "$service_name" || {
        echo -e "❌ Failed to restart ${service_name}"
        return 1
    }
    
    echo -e "${GREEN}✅ ${description} restarted successfully${NC}"
    echo ""
}

# Function to stop, rebuild, and start a service
stop_rebuild_start() {
    local service_name=$1
    local description=$2
    
    echo -e "${YELLOW}🛑 Stopping ${description}...${NC}"
    docker-compose stop "$service_name" || true
    
    rebuild_service "$service_name" "$description"
    
    echo -e "${YELLOW}🚀 Starting ${description}...${NC}"
    docker-compose up -d "$service_name" || {
        echo -e "❌ Failed to start ${service_name}"
        return 1
    }
    
    echo -e "${GREEN}✅ ${description} started successfully${NC}"
    echo ""
}

# Check which services are running
echo -e "${BLUE}🔍 Checking service status...${NC}"
RUNNING_SERVICES=$(docker-compose ps --services --filter "status=running" 2>/dev/null || echo "")
echo ""

# Deploy ai-automation-service
# Note: This service has source code mounted, so we just need to restart
# However, if new dependencies were added, a rebuild might be needed
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}1/3: ai-automation-service${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Check if new files were added (new router needs to be in image)
if [ -f "services/ai-automation-service/src/api/yaml_validation_router.py" ]; then
    echo "New validation router detected - rebuilding service..."
    stop_rebuild_start "ai-automation-service" "AI Automation Service"
else
    echo "Source code is mounted - restarting service..."
    restart_service "ai-automation-service" "AI Automation Service"
fi

# Deploy ha-ai-agent-service
# This service doesn't have source mounted, so we need to rebuild
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}2/3: ha-ai-agent-service${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
stop_rebuild_start "ha-ai-agent-service" "HA AI Agent Service"

# Deploy ai-automation-ui
# UI needs to be rebuilt as it's built at build time
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}3/3: ai-automation-ui${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
stop_rebuild_start "ai-automation-ui" "AI Automation UI"

# Wait for services to be healthy
echo -e "${BLUE}⏳ Waiting for services to be healthy...${NC}"
sleep 5

# Check service health
echo ""
echo -e "${BLUE}🔍 Checking service health...${NC}"
docker-compose ps | grep -E "(ai-automation-service|ha-ai-agent-service|ai-automation-ui)" || true

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Deployment Complete!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Services deployed:"
echo "  • ai-automation-service - http://localhost:8024"
echo "  • ha-ai-agent-service - http://localhost:8030"
echo "  • ai-automation-ui - http://localhost:3001"
echo ""
echo "Check logs with:"
echo "  docker-compose logs -f ai-automation-service"
echo "  docker-compose logs -f ha-ai-agent-service"
echo "  docker-compose logs -f ai-automation-ui"
echo ""

