#!/bin/bash

# Docker E2E Test Runner for HA Ingestor
# This script runs comprehensive end-to-end tests against the Docker deployment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DOCKER_COMPOSE_FILE="docker-compose.yml"
TEST_RESULTS_DIR="test-results"
REPORTS_DIR="test-reports"

echo -e "${BLUE}🚀 HA Ingestor Docker E2E Test Runner${NC}"
echo "=================================="

# Function to print status messages
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check prerequisites
echo "Checking prerequisites..."

# Check if Docker is running
if ! docker ps > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker first."
    exit 1
fi
print_status "Docker is running"

# Check if Docker Compose is available
if ! command -v docker-compose > /dev/null 2>&1; then
    print_error "Docker Compose is not installed or not in PATH."
    exit 1
fi
print_status "Docker Compose is available"

# Check if the HA Ingestor deployment exists
if [ ! -f "$DOCKER_COMPOSE_FILE" ]; then
    print_error "Docker Compose file not found: $DOCKER_COMPOSE_FILE"
    exit 1
fi
print_status "Docker Compose file found"

# Check if required containers are running
echo "Checking Docker containers..."
# Epic 31: enrichment-pipeline deprecated
REQUIRED_CONTAINERS=(
    "homeiq-influxdb"
    "homeiq-websocket"
    "homeiq-admin"
    "homeiq-dashboard"
)

for container in "${REQUIRED_CONTAINERS[@]}"; do
    if docker ps --format "{{.Names}}" | grep -q "^${container}$"; then
        print_status "$container is running"
    else
        print_error "$container is not running"
        echo "Please start the HA Ingestor deployment first:"
        echo "  docker-compose up -d"
        exit 1
    fi
done

# Wait for services to be healthy
echo "Waiting for services to be healthy..."
sleep 10

# Check service health endpoints
SERVICES=(
    "InfluxDB:http://localhost:8086/health"
    "WebSocket:http://localhost:8001/health"
    "Data API:http://localhost:8006/health"
    "Admin API:http://localhost:8004/api/v1/health"
    "Dashboard:http://localhost:3000"
)

for service in "${SERVICES[@]}"; do
    IFS=':' read -r name url <<< "$service"
    if curl -s -f "$url" > /dev/null 2>&1; then
        print_status "$name is healthy"
    else
        print_warning "$name health check failed (this might be normal during startup)"
    fi
done

# Create test results directory
mkdir -p "$TEST_RESULTS_DIR"
mkdir -p "$REPORTS_DIR"

echo ""
echo "Running E2E Tests..."
echo "==================="

# Install Playwright browsers if not already installed
echo "Ensuring Playwright browsers are installed..."
npx playwright install --with-deps

# Run different test suites
echo ""
echo "1. System Health Tests"
echo "----------------------"
npx playwright test tests/e2e/system-health.spec.ts \
    --config=tests/e2e/docker-deployment.config.ts \
    --project=docker-chromium \
    --reporter=html,json,junit

echo ""
echo "2. Dashboard Functionality Tests"
echo "--------------------------------"
npx playwright test tests/e2e/dashboard-functionality.spec.ts \
    --config=tests/e2e/docker-deployment.config.ts \
    --project=docker-chromium \
    --reporter=html,json,junit

echo ""
echo "3. Monitoring Screen Tests"
echo "--------------------------"
npx playwright test tests/e2e/monitoring-screen.spec.ts \
    --config=tests/e2e/docker-deployment.config.ts \
    --project=docker-chromium \
    --reporter=html,json,junit

echo ""
echo "4. Settings Screen Tests"
echo "------------------------"
npx playwright test tests/e2e/settings-screen.spec.ts \
    --config=tests/e2e/docker-deployment.config.ts \
    --project=docker-chromium \
    --reporter=html,json,junit

echo ""
echo "5. Visual Regression Tests"
echo "--------------------------"
npx playwright test tests/e2e/visual-regression.spec.ts \
    --config=tests/e2e/docker-deployment.config.ts \
    --project=docker-chromium \
    --reporter=html,json,junit

echo ""
echo "6. Integration Tests"
echo "--------------------"
npx playwright test tests/e2e/integration.spec.ts \
    --config=tests/e2e/docker-deployment.config.ts \
    --project=docker-chromium \
    --reporter=html,json,junit

echo ""
echo "7. Performance Tests"
echo "--------------------"
npx playwright test tests/e2e/performance.spec.ts \
    --config=tests/e2e/docker-deployment.config.ts \
    --project=docker-chromium \
    --reporter=html,json,junit

echo ""
echo "8. API Endpoints Tests"
echo "----------------------"
npx playwright test tests/e2e/api-endpoints.spec.ts \
    --config=tests/e2e/docker-deployment.config.ts \
    --project=docker-chromium \
    --reporter=html,json,junit

echo ""
echo "9. Frontend UI Comprehensive Tests"
echo "----------------------------------"
npx playwright test tests/e2e/frontend-ui-comprehensive.spec.ts \
    --config=tests/e2e/docker-deployment.config.ts \
    --project=docker-chromium \
    --reporter=html,json,junit

echo ""
echo "10. Enhanced Integration & Performance Tests"
echo "--------------------------------------------"
npx playwright test tests/e2e/integration-performance-enhanced.spec.ts \
    --config=tests/e2e/docker-deployment.config.ts \
    --project=docker-chromium \
    --reporter=html,json,junit

echo ""
echo "11. Dashboard Data Loading Tests"
echo "-------------------------------"
npx playwright test tests/e2e/dashboard-data-loading.spec.ts \
    --config=tests/e2e/docker-deployment.config.ts \
    --project=docker-chromium \
    --reporter=html,json,junit

echo ""
echo "12. Comprehensive Error Handling Tests"
echo "-------------------------------------"
npx playwright test tests/e2e/error-handling-comprehensive.spec.ts \
    --config=tests/e2e/docker-deployment.config.ts \
    --project=docker-chromium \
    --reporter=html,json,junit

# Run cross-browser tests (optional)
if [ "$1" = "--cross-browser" ]; then
    echo ""
    echo "13. Cross-Browser Tests"
    echo "----------------------"
    npx playwright test \
        --config=tests/e2e/docker-deployment.config.ts \
        --project=docker-firefox,docker-webkit \
        --reporter=html,json,junit
fi

# Run mobile tests (optional)
if [ "$1" = "--mobile" ]; then
    echo ""
    echo "14. Mobile Tests"
    echo "---------------"
    npx playwright test \
        --config=tests/e2e/docker-deployment.config.ts \
        --project=docker-mobile-chrome,docker-mobile-safari \
        --reporter=html,json,junit
fi

# Generate comprehensive report
echo ""
echo "Generating Test Reports..."
echo "========================="

# Copy test results to reports directory
cp -r test-results/* "$REPORTS_DIR/" 2>/dev/null || true

# Generate summary report
cat > "$REPORTS_DIR/test-summary.md" << EOF
# HA Ingestor E2E Test Summary

## Test Execution Details
- **Date**: $(date)
- **Docker Compose File**: $DOCKER_COMPOSE_FILE
- **Test Configuration**: docker-deployment.config.ts

## Test Suites Executed
1. ✅ System Health Tests
2. ✅ Dashboard Functionality Tests
3. ✅ Monitoring Screen Tests
4. ✅ Settings Screen Tests
5. ✅ Visual Regression Tests
6. ✅ Integration Tests
7. ✅ Performance Tests
8. ✅ API Endpoints Tests
9. ✅ Frontend UI Comprehensive Tests
10. ✅ Enhanced Integration & Performance Tests
11. ✅ Dashboard Data Loading Tests
12. ✅ Comprehensive Error Handling Tests

## Test Results
- **Results Directory**: $TEST_RESULTS_DIR
- **HTML Report**: $REPORTS_DIR/html-report/index.html
- **JSON Results**: $TEST_RESULTS_DIR/results.json
- **JUnit Results**: $TEST_RESULTS_DIR/results.xml

## Docker Environment
- **InfluxDB**: http://localhost:8086
- **WebSocket Ingestion**: http://localhost:8001
- **Enrichment Pipeline**: http://localhost:8002
- **Admin API**: http://localhost:8004
- **Health Dashboard**: http://localhost:3000
- **Data Retention**: http://localhost:8080

## Next Steps
1. Review the HTML report for detailed test results
2. Check failed tests and investigate issues
3. Update baseline screenshots if visual regression tests fail
4. Optimize performance if performance tests fail

EOF

print_status "Test execution completed"
print_status "Results saved to: $REPORTS_DIR/"
print_status "HTML report: $REPORTS_DIR/html-report/index.html"

echo ""
echo "🎉 E2E Testing Complete!"
echo "======================="
echo ""
echo "To view the test results:"
echo "  open $REPORTS_DIR/html-report/index.html"
echo ""
echo "To run specific test suites:"
echo "  npx playwright test tests/e2e/system-health.spec.ts --config=tests/e2e/docker-deployment.config.ts"
echo ""
echo "To run with different options:"
echo "  ./tests/e2e/run-docker-tests.sh --cross-browser  # Include cross-browser tests"
echo "  ./tests/e2e/run-docker-tests.sh --mobile         # Include mobile tests"
