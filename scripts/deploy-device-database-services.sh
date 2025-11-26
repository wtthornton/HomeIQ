#!/bin/bash
# Deploy Device Database Enhancement Services
# This script builds and starts the 5 new Device Database services

set -e

echo "🚀 Deploying Device Database Enhancement Services..."

# Build new services
echo "📦 Building new services..."
docker compose build device-health-monitor device-context-classifier device-setup-assistant device-database-client device-recommender

# Run database migration for data-api (adds new device fields)
echo "🗄️  Running database migration..."
docker compose run --rm data-api alembic upgrade head

# Start new services
echo "▶️  Starting new services..."
docker compose up -d device-health-monitor device-context-classifier device-setup-assistant device-database-client device-recommender

# Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check service health
echo "🏥 Checking service health..."
curl -f http://localhost:8019/health && echo " ✅ device-health-monitor"
curl -f http://localhost:8032/health && echo " ✅ device-context-classifier"
curl -f http://localhost:8021/health && echo " ✅ device-setup-assistant"
curl -f http://localhost:8022/health && echo " ✅ device-database-client"
curl -f http://localhost:8023/health && echo " ✅ device-recommender"

echo ""
echo "✅ Device Database Enhancement Services deployed successfully!"
echo ""
echo "Services available at:"
echo "  - Device Health Monitor: http://localhost:8019"
echo "  - Device Context Classifier: http://localhost:8032"
echo "  - Device Setup Assistant: http://localhost:8021"
echo "  - Device Database Client: http://localhost:8022"
echo "  - Device Recommender: http://localhost:8023"
echo ""
echo "API endpoints available via Data API (http://localhost:8006):"
echo "  - GET /api/devices/{device_id}/health"
echo "  - POST /api/devices/{device_id}/classify"
echo "  - GET /api/devices/{device_id}/setup-guide"
echo "  - POST /api/devices/{device_id}/discover-capabilities"
echo "  - GET /api/devices/recommendations"

