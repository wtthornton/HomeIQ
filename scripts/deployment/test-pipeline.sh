#!/bin/bash
#
# Test Deployment Pipeline
# Validates all pipeline components in test environment
#
# Usage:
#   ./scripts/deployment/test-pipeline.sh
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASSED=0
FAILED=0

# Test function
test_component() {
    local name=$1
    local command=$2
    
    echo -n "Testing $name... "
    if eval "$command" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ PASSED${NC}"
        PASSED=$((PASSED + 1))
        return 0
    else
        echo -e "${RED}❌ FAILED${NC}"
        FAILED=$((FAILED + 1))
        return 1
    fi
}

# Main test execution
main() {
    echo "=========================================="
    echo "HomeIQ Deployment Pipeline Test"
    echo "=========================================="
    echo ""
    
    # Test 1: Validate deployment script exists
    test_component "Deployment validation script" \
        "test -f scripts/deployment/validate-deployment.py"
    
    # Test 2: Validate health check script exists
    test_component "Health check script" \
        "test -f scripts/deployment/health-check.sh"
    
    # Test 3: Validate rollback script exists
    test_component "Rollback script" \
        "test -f scripts/deployment/rollback.sh"
    
    # Test 4: Validate tracking script exists
    test_component "Deployment tracking script" \
        "test -f scripts/deployment/track-deployment.py"
    
    # Test 5: Validate deployment workflow exists
    test_component "Deployment workflow" \
        "test -f .github/workflows/deploy-production.yml"
    
    # Test 6: Validate notification workflow exists
    test_component "Notification workflow" \
        "test -f .github/workflows/deployment-notify.yml"
    
    # Test 7: Validate Docker Compose config
    test_component "Docker Compose config" \
        "docker compose config --quiet"
    
    # Test 8: Validate deployment validation script syntax
    if command -v python &> /dev/null; then
        test_component "Deployment validation script syntax" \
            "python -m py_compile scripts/deployment/validate-deployment.py"
    else
        echo -e "${YELLOW}⚠️ Python not found, skipping syntax check${NC}"
    fi
    
    # Test 9: Validate tracking script syntax
    if command -v python &> /dev/null; then
        test_component "Tracking script syntax" \
            "python -m py_compile scripts/deployment/track-deployment.py"
    else
        echo -e "${YELLOW}⚠️ Python not found, skipping syntax check${NC}"
    fi
    
    # Test 10: Validate health check script is executable (on Unix)
    if [[ "$OSTYPE" != "msys" && "$OSTYPE" != "win32" ]]; then
        test_component "Health check script executable" \
            "test -x scripts/deployment/health-check.sh"
    fi
    
    # Test 11: Validate rollback script is executable (on Unix)
    if [[ "$OSTYPE" != "msys" && "$OSTYPE" != "win32" ]]; then
        test_component "Rollback script executable" \
            "test -x scripts/deployment/rollback.sh"
    fi
    
    # Test 12: Validate documentation exists
    test_component "Pipeline documentation" \
        "test -f docs/deployment/DEPLOYMENT_PIPELINE.md"
    
    test_component "Runbook documentation" \
        "test -f docs/deployment/DEPLOYMENT_RUNBOOK.md"
    
    # Summary
    echo ""
    echo "=========================================="
    echo "Test Summary"
    echo "=========================================="
    echo -e "${GREEN}Passed: $PASSED${NC}"
    echo -e "${RED}Failed: $FAILED${NC}"
    echo "Total: $((PASSED + FAILED))"
    echo ""
    
    if [[ $FAILED -eq 0 ]]; then
        echo -e "${GREEN}✅ All pipeline tests passed!${NC}"
        exit 0
    else
        echo -e "${RED}❌ Some tests failed. Please review and fix.${NC}"
        exit 1
    fi
}

# Run main function
main "$@"

