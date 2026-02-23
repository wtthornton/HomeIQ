#!/bin/bash

# Comprehensive E2E Test Runner for HA Ingestor Dashboard

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
RESET='\033[0m'

# Default options
SUITE="full"
BROWSER="chromium"
UI_MODE=false
HEADED=false
DEBUG=false
REPORT=false

# Print header
print_header() {
    echo ""
    echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${RESET}"
    echo -e "${BLUE}║  HA Ingestor Dashboard - E2E Test Runner              ║${RESET}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${RESET}"
    echo ""
}

# Show help
show_help() {
    print_header
    echo "Usage: ./run-tests.sh [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -s, --suite <name>     Test suite: full, services, all, quick (default: full)"
    echo "  -b, --browser <name>   Browser: chromium, firefox, webkit, all (default: chromium)"
    echo "  -u, --ui               Run in UI mode (interactive)"
    echo "  -h, --headed           Run with visible browser"
    echo "  -d, --debug            Run in debug mode"
    echo "  -r, --report           Show test report"
    echo "  --help                 Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./run-tests.sh"
    echo "  ./run-tests.sh --suite full --browser chromium"
    echo "  ./run-tests.sh --ui"
    echo "  ./run-tests.sh --report"
    echo ""
    exit 0
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -s|--suite)
            SUITE="$2"
            shift 2
            ;;
        -b|--browser)
            BROWSER="$2"
            shift 2
            ;;
        -u|--ui)
            UI_MODE=true
            shift
            ;;
        -h|--headed)
            HEADED=true
            shift
            ;;
        -d|--debug)
            DEBUG=true
            shift
            ;;
        -r|--report)
            REPORT=true
            shift
            ;;
        --help)
            show_help
            ;;
        *)
            echo -e "${RED}Unknown option: $1${RESET}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

print_header

# Check if we're in the right directory
if [ ! -f "package.json" ]; then
    echo -e "${RED}❌ Error: package.json not found${RESET}"
    echo -e "${YELLOW}Please run this script from the services/health-dashboard directory${RESET}"
    exit 1
fi

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}⚠️  node_modules not found. Running npm install...${RESET}"
    npm install
fi

# Check if Playwright is installed
if [ ! -d "node_modules/@playwright" ]; then
    echo -e "${YELLOW}⚠️  Playwright not found. Installing...${RESET}"
    npm install @playwright/test
    npx playwright install
fi

# Check if backend services are running
echo -e "${BLUE}🔍 Checking backend services...${RESET}"
if curl -f -s -o /dev/null --max-time 5 http://localhost:3000/api/health; then
    echo -e "${GREEN}✅ Backend services are running${RESET}"
else
    echo -e "${RED}❌ Backend services not responding${RESET}"
    echo -e "${YELLOW}   Please ensure the dashboard is running:${RESET}"
    echo -e "${YELLOW}   1. Start backend: docker-compose up -d${RESET}"
    echo -e "${YELLOW}   2. Start dashboard: npm run dev${RESET}"
    echo ""
    read -p "Continue anyway? (y/N): " continue_choice
    if [[ ! "$continue_choice" =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""

# Show report if requested
if [ "$REPORT" = true ]; then
    echo -e "${BLUE}📊 Opening test report...${RESET}"
    npx playwright show-report
    exit 0
fi

# Build test command
TEST_CMD="npx playwright test"

# Add UI mode
if [ "$UI_MODE" = true ]; then
    echo -e "${BLUE}🎮 Launching UI mode (interactive)...${RESET}"
    TEST_CMD="$TEST_CMD --ui"
fi

# Add headed mode
if [ "$HEADED" = true ]; then
    echo -e "${BLUE}👀 Running with visible browser...${RESET}"
    TEST_CMD="$TEST_CMD --headed"
fi

# Add debug mode
if [ "$DEBUG" = true ]; then
    echo -e "${BLUE}🐛 Running in debug mode...${RESET}"
    TEST_CMD="$TEST_CMD --debug"
fi

# Add browser selection
if [ "$BROWSER" != "all" ]; then
    echo -e "${BLUE}🌐 Browser: $BROWSER${RESET}"
    TEST_CMD="$TEST_CMD --project=$BROWSER"
else
    echo -e "${BLUE}🌐 Running on all browsers${RESET}"
fi

# Add test suite selection
echo -e "${BLUE}📝 Test Suite: $SUITE${RESET}"
case $SUITE in
    "full")
        echo -e "${GREEN}   Running comprehensive full dashboard tests${RESET}"
        TEST_CMD="$TEST_CMD dashboard-full"
        ;;
    "services")
        echo -e "${GREEN}   Running services tab tests${RESET}"
        TEST_CMD="$TEST_CMD services-tab"
        ;;
    "quick")
        echo -e "${GREEN}   Running quick smoke tests${RESET}"
        TEST_CMD="$TEST_CMD --grep 'should load dashboard|should verify NO mock data'"
        ;;
    "all")
        echo -e "${GREEN}   Running all test suites${RESET}"
        # Run all tests
        ;;
esac

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${RESET}"
echo -e "${BLUE}  Starting Tests...${RESET}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${RESET}"
echo ""

# Run tests
START_TIME=$(date +%s)
eval $TEST_CMD
EXIT_CODE=$?
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${RESET}"

if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed!${RESET}"
    echo -e "${GREEN}   Duration: ${DURATION}s${RESET}"
    echo ""
    echo -e "${BLUE}📊 To view detailed report:${RESET}"
    echo -e "${YELLOW}   ./run-tests.sh --report${RESET}"
else
    echo -e "${RED}❌ Some tests failed${RESET}"
    echo -e "${RED}   Duration: ${DURATION}s${RESET}"
    echo ""
    echo -e "${BLUE}📊 To view test results:${RESET}"
    echo -e "${YELLOW}   ./run-tests.sh --report${RESET}"
    echo ""
    echo -e "${BLUE}🐛 To debug:${RESET}"
    echo -e "${YELLOW}   ./run-tests.sh --debug${RESET}"
fi

echo -e "${BLUE}═══════════════════════════════════════════════════════${RESET}"
echo ""

exit $EXIT_CODE

