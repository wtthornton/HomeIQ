#!/bin/bash
# Home Assistant Ingestor - Smoke Test Execution Script
# This script runs comprehensive smoke tests to validate system health

set -e  # Exit on any error

# Default values
# Admin API production port mapping is 8004 (domains/core-platform/compose.yml)
ADMIN_URL="http://localhost:8004"
VERBOSE=false
JSON_OUTPUT=false
TIMEOUT=30

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --admin-url)
            ADMIN_URL="$2"
            shift 2
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --json)
            JSON_OUTPUT=true
            shift
            ;;
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --admin-url URL    Admin API URL (default: http://localhost:8004)"
            echo "  --verbose          Enable verbose output"
            echo "  --json             Output results in JSON format"
            echo "  --timeout SECONDS  Test timeout in seconds (default: 30)"
            echo "  -h, --help         Show this help message"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}🧪 Home Assistant Ingestor - Smoke Test Suite${NC}"
echo -e "${BLUE}=================================================${NC}"

# Check if Python is available
if ! command -v python &> /dev/null; then
    print_error "Python not found! Please install Python to run smoke tests."
    exit 1
fi

python_version=$(python --version 2>&1)
print_status "Python detected: $python_version"

# Check if smoke test script exists
if [ ! -f "tests/smoke_tests.py" ]; then
    print_error "Smoke test script not found: tests/smoke_tests.py"
    exit 1
fi

# Build command arguments
args=("tests/smoke_tests.py" "--admin-url" "$ADMIN_URL" "--timeout" "$TIMEOUT")

if [ "$VERBOSE" = true ]; then
    args+=("--verbose")
fi

if [ "$JSON_OUTPUT" = true ]; then
    args+=("--output" "json")
fi

# Run smoke tests
print_status "Running comprehensive smoke tests..."
print_status "Admin API URL: $ADMIN_URL"
print_status "Timeout: ${TIMEOUT}s"

if python "${args[@]}"; then
    print_success "🎉 All smoke tests passed! System is healthy and deployment ready."
    exit 0
else
    print_error "❌ Smoke tests failed! System has issues that need attention."
    print_warning "Please review the test results above and fix critical issues."
    exit 1
fi
