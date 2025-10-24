#!/bin/bash
# Deploy Phase 1 Containerized AI Services

echo "🚀 Deploying Phase 1 Containerized AI Services..."

# Navigate to the root of the project
SCRIPT_DIR=$(dirname "$(realpath "$0")")
PROJECT_ROOT=$(realpath "$SCRIPT_DIR/../../..")
cd "$PROJECT_ROOT" || exit

echo "📦 Building new services..."

# Build all new services
echo "Building OpenVINO Service..."
docker-compose build openvino-service

echo "Building ML Service..."
docker-compose build ml-service

echo "Building AI Core Service..."
docker-compose build ai-core-service

echo "Building existing services..."
docker-compose build ner-service openai-service ai-automation-service

echo "🔄 Starting services..."

# Start services in dependency order
echo "Starting base services..."
docker-compose up -d influxdb data-api

echo "Waiting for base services to be healthy..."
sleep 30

echo "Starting model services..."
docker-compose up -d ner-service openai-service openvino-service ml-service

echo "Waiting for model services to be healthy..."
sleep 60

echo "Starting orchestrator services..."
docker-compose up -d ai-core-service ai-automation-service

echo "Waiting for orchestrator services to be healthy..."
sleep 30

echo "Starting UI..."
docker-compose up -d ai-automation-ui

echo "✅ Deployment complete!"

echo ""
echo "📊 Service Status:"
docker-compose ps

echo ""
echo "🔍 Service Health Checks:"
echo "OpenVINO Service: http://localhost:8019/health"
echo "ML Service: http://localhost:8021/health"
echo "AI Core Service: http://localhost:8018/health"
echo "NER Service: http://localhost:8019/health"
echo "OpenAI Service: http://localhost:8020/health"
echo "AI Automation Service: http://localhost:8017/health"
echo "AI Automation UI: http://localhost:3001"

echo ""
echo "📝 Logs:"
echo "docker-compose logs -f openvino-service"
echo "docker-compose logs -f ml-service"
echo "docker-compose logs -f ai-core-service"
echo "docker-compose logs -f ai-automation-service"
