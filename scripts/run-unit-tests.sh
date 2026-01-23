#!/bin/bash
# HomeIQ Unit Testing Framework
# Simple script to run all unit tests with coverage

set -e  # Exit on any error

echo "🧪 HomeIQ Unit Testing Framework"
echo "================================="

# Check if we're in the right directory
if [ ! -f "scripts/run-unit-tests.py" ]; then
    echo "❌ Error: Please run this script from the project root directory"
    echo "   Current directory: $(pwd)"
    echo "   Expected files: scripts/run-unit-tests.py"
    exit 1
fi

# Check Python installation
if ! command -v python &> /dev/null; then
    echo "❌ Error: Python is not installed or not in PATH"
    exit 1
fi

# Check Node.js installation (for TypeScript tests)
if ! command -v node &> /dev/null; then
    echo "⚠️  Warning: Node.js not found, TypeScript tests will be skipped"
fi

# Create test results directory
mkdir -p test-results/coverage/python
mkdir -p test-results/coverage/typescript

echo "📁 Created test results directories"
echo ""

# Parse command line arguments
VERBOSE=""
PYTHON_ONLY=""
TYPESCRIPT_ONLY=""
COVERAGE_ONLY=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose)
            VERBOSE="--verbose"
            shift
            ;;
        --python-only)
            PYTHON_ONLY="--python-only"
            shift
            ;;
        --typescript-only)
            TYPESCRIPT_ONLY="--typescript-only"
            shift
            ;;
        --coverage-only)
            COVERAGE_ONLY="--coverage-only"
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -v, --verbose        Verbose output"
            echo "  --python-only        Run only Python unit tests"
            echo "  --typescript-only    Run only TypeScript unit tests"
            echo "  --coverage-only      Generate coverage reports only"
            echo "  -h, --help           Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                   # Run all unit tests"
            echo "  $0 --verbose         # Run with verbose output"
            echo "  $0 --python-only     # Run only Python tests"
            echo "  $0 --typescript-only # Run only TypeScript tests"
            exit 0
            ;;
        *)
            echo "❌ Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Run the unit testing framework
echo "🚀 Starting unit tests..."
echo ""

python scripts/run-unit-tests.py $VERBOSE $PYTHON_ONLY $TYPESCRIPT_ONLY $COVERAGE_ONLY

EXIT_CODE=$?

echo ""
echo "================================="

if [ $EXIT_CODE -eq 0 ]; then
    echo "🎉 All unit tests passed!"
    echo ""
    echo "📊 Coverage reports available in:"
    echo "   • test-results/coverage/python/     (Python coverage)"
    echo "   • test-results/coverage/typescript/  (TypeScript coverage)"
    echo "   • test-results/unit-test-report.html (Summary report)"
else
    echo "❌ Some unit tests failed!"
    echo ""
    echo "📋 Check the detailed reports:"
    echo "   • test-results/unit-test-results.json"
    echo "   • test-results/unit-test-report.html"
fi

exit $EXIT_CODE
