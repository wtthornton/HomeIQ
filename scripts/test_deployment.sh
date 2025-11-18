#!/bin/bash
# Quick deployment test script

echo "=========================================="
echo "DEPLOYMENT STATUS CHECK"
echo "=========================================="
echo ""

echo "1. Checking services..."
docker-compose -f docker-compose.dev.yml ps websocket-ingestion data-api influxdb | grep -E "NAME|websocket|data-api|influxdb"

echo ""
echo "2. Testing service health..."
curl -s http://localhost:8001/health | jq -r '.status // "ERROR"'
curl -s http://localhost:8006/health | jq -r '.status // "ERROR"'

echo ""
echo "3. Testing discovery..."
DISCOVERY_RESULT=$(curl -s -X POST http://localhost:8001/api/v1/discovery/trigger)
echo "Discovery result: $DISCOVERY_RESULT"

echo ""
echo "4. Checking database..."
python scripts/check_device_names.py | head -20

echo ""
echo "5. Running E2E test..."
python scripts/e2e_device_verification.py

echo ""
echo "=========================================="
echo "DEPLOYMENT CHECK COMPLETE"
echo "=========================================="

