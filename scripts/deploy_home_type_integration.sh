#!/bin/bash
# Deploy Home Type Integration Changes
# This script rebuilds and restarts the services with home type integration

set -e  # Exit on error

echo "=========================================="
echo "Home Type Integration Deployment"
echo "=========================================="
echo ""

# Services to rebuild
SERVICES=("ai-automation-service" "data-api" "websocket-ingestion")

echo "Step 1: Rebuilding Docker containers..."
echo ""

for service in "${SERVICES[@]}"; do
    echo "  → Rebuilding $service..."
    docker-compose build "$service"
    if [ $? -eq 0 ]; then
        echo "    ✅ $service rebuilt successfully"
    else
        echo "    ❌ Failed to rebuild $service"
        exit 1
    fi
done

echo ""
echo "Step 2: Restarting services..."
echo ""

for service in "${SERVICES[@]}"; do
    echo "  → Restarting $service..."
    docker-compose up -d "$service"
    if [ $? -eq 0 ]; then
        echo "    ✅ $service restarted successfully"
    else
        echo "    ❌ Failed to restart $service"
        exit 1
    fi
done

echo ""
echo "Step 3: Waiting for services to be healthy..."
sleep 10

echo ""
echo "Step 4: Verifying service health..."
echo ""

# Check ai-automation-service
if docker-compose ps ai-automation-service | grep -q "Up"; then
    echo "  ✅ ai-automation-service is running"
else
    echo "  ❌ ai-automation-service is not running"
fi

# Check data-api
if docker-compose ps data-api | grep -q "Up"; then
    echo "  ✅ data-api is running"
else
    echo "  ❌ data-api is not running"
fi

# Check websocket-ingestion
if docker-compose ps websocket-ingestion | grep -q "Up"; then
    echo "  ✅ websocket-ingestion is running"
else
    echo "  ❌ websocket-ingestion is not running"
fi

echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Check logs: docker-compose logs -f ai-automation-service"
echo "  2. Verify home type client: Look for '✅ Home Type Client initialized'"
echo "  3. Test endpoints:"
echo "     - curl http://localhost:8018/api/home-type/classify?home_id=default"
echo "     - curl http://localhost:8006/api/events/categories?hours=24"
echo ""

