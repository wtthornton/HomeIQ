#!/bin/bash

#
# Ask AI E2E Test Runner
# 
# Runs comprehensive E2E tests for Ask AI feature
# Tests query submission, test execution, approval workflow, and bug fixes
#

set -e

echo "========================================"
echo "Ask AI E2E Test Suite"
echo "========================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if services are running
echo "📋 Checking service health..."

check_service() {
    local name=$1
    local url=$2
    
    if curl -sf "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} $name is healthy"
        return 0
    else
        echo -e "${RED}✗${NC} $name is not responding"
        return 1
    fi
}

# Check AI Automation UI
if ! check_service "AI Automation UI" "http://localhost:3001"; then
    echo -e "${RED}ERROR: AI Automation UI (port 3001) is not running${NC}"
    echo "Start it with: docker-compose up -d ai-automation-ui"
    exit 1
fi

# Check AI Automation Service
if ! check_service "AI Automation Service" "http://localhost:8018/health"; then
    echo -e "${YELLOW}WARNING: AI Automation Service (port 8018) is not responding${NC}"
    echo "Some tests may fail. Start it with: docker-compose up -d ai-automation-service"
fi

# Check Home Assistant (optional)
if curl -sf "http://192.168.1.86:8123/api/" > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Home Assistant is reachable"
else
    echo -e "${YELLOW}⚠${NC}  Home Assistant is not reachable (test automations won't execute)"
fi

echo ""
echo "========================================"
echo "Running Ask AI E2E Tests"
echo "========================================"
echo ""

# Change to test directory
cd "$(dirname "$0")"

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing test dependencies..."
    npm install
fi

# Run tests
echo "🧪 Running tests..."
echo ""

# Default: Run all Ask AI tests
TEST_FILE=${1:-"ask-ai-complete.spec.ts"}

npx playwright test "$TEST_FILE" \
    --reporter=html \
    --reporter=list \
    --output=test-results/ask-ai \
    "$@"

TEST_EXIT_CODE=$?

echo ""
echo "========================================"
echo "Test Results"
echo "========================================"
echo ""

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
else
    echo -e "${RED}❌ Some tests failed${NC}"
fi

echo ""
echo "📊 View detailed results:"
echo "   npx playwright show-report"
echo ""
echo "🎥 Screenshots and videos (on failure):"
echo "   test-results/ask-ai/"
echo ""

exit $TEST_EXIT_CODE

