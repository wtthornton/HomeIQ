#!/bin/bash

# Deployment Verification Script
# This script verifies that all components are working correctly after deployment
#
# Run from the repository root. Admin API is expected on port 8004 (see domains/core-platform/admin-api).

set -e  # Exit on any error

echo "🚀 Starting deployment verification..."
echo "=================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2${NC}"
    else
        echo -e "${RED}❌ $2${NC}"
        exit 1
    fi
}

# Function to test API endpoint
test_endpoint() {
    local url=$1
    local expected_field=$2
    local expected_value=$3
    
    echo "Testing: $url"
    response=$(curl -s -f "$url" 2>/dev/null)
    if [ $? -eq 0 ]; then
        if [ -n "$expected_field" ] && [ -n "$expected_value" ]; then
            actual_value=$(echo "$response" | jq -r ".$expected_field" 2>/dev/null)
            if [ "$actual_value" = "$expected_value" ]; then
                print_status 0 "Endpoint $url returns correct $expected_field: $actual_value"
            else
                echo -e "${RED}❌ Endpoint $url returned $expected_field: $actual_value (expected: $expected_value)${NC}"
                exit 1
            fi
        else
            print_status 0 "Endpoint $url is accessible"
        fi
    else
        echo -e "${RED}❌ Endpoint $url is not accessible${NC}"
        exit 1
    fi
}

# Function to test dashboard
test_dashboard() {
    echo "Testing dashboard functionality..."
    
    # Test dashboard loads
    response=$(curl -s -f "http://localhost:3000" 2>/dev/null)
    if [ $? -eq 0 ]; then
        print_status 0 "Dashboard loads successfully"
    else
        echo -e "${RED}❌ Dashboard is not accessible${NC}"
        exit 1
    fi
    
    # Test dashboard API calls (simulate what frontend does)
    echo "Testing dashboard API integration..."
    
    # Test enhanced health endpoint
    health_response=$(curl -s "http://localhost:8004/api/v1/health" 2>/dev/null)
    if echo "$health_response" | jq -e '.dependencies' > /dev/null 2>&1; then
        print_status 0 "Enhanced health endpoint returns dependency information"
    else
        echo -e "${RED}❌ Enhanced health endpoint missing dependency information${NC}"
        exit 1
    fi
    
    # Test stats endpoint
    stats_response=$(curl -s "http://localhost:8004/api/v1/stats" 2>/dev/null)
    if echo "$stats_response" | jq -e '.metrics' > /dev/null 2>&1; then
        print_status 0 "Stats endpoint returns metrics information"
    else
        echo -e "${RED}❌ Stats endpoint missing metrics information${NC}"
        exit 1
    fi
}

# Function to check service logs
check_service_logs() {
    echo "Checking service logs for errors..."
    
    # Check admin-api logs
    admin_errors=$(docker logs homeiq-admin 2>&1 | grep -i "error\|exception\|failed" | tail -5)
    if [ -n "$admin_errors" ]; then
        echo -e "${YELLOW}⚠️  Admin API has recent errors:${NC}"
        echo "$admin_errors"
    else
        print_status 0 "Admin API logs are clean"
    fi
    
    # Check dashboard logs
    dashboard_errors=$(docker logs homeiq-dashboard 2>&1 | grep -i "error\|exception\|failed" | tail -5)
    if [ -n "$dashboard_errors" ]; then
        echo -e "${YELLOW}⚠️  Dashboard has recent errors:${NC}"
        echo "$dashboard_errors"
    else
        print_status 0 "Dashboard logs are clean"
    fi
}

# Function to verify TypeScript types
verify_types() {
    echo "Verifying TypeScript types..."
    
    # Check if health types are properly defined
    if grep -q "ServiceHealthResponse" domains/core-platform/health-dashboard/src/types/health.ts; then
        print_status 0 "ServiceHealthResponse type is defined"
    else
        echo -e "${RED}❌ ServiceHealthResponse type is missing${NC}"
        exit 1
    fi
    
    if grep -q "DependencyHealth" domains/core-platform/health-dashboard/src/types/health.ts; then
        print_status 0 "DependencyHealth type is defined"
    else
        echo -e "${RED}❌ DependencyHealth type is missing${NC}"
        exit 1
    fi
}

# Main verification process
echo "1. Verifying service health..."
test_endpoint "http://localhost:8004/health" "status" "healthy"
test_endpoint "http://localhost:8004/api/health" "status" "healthy"

echo ""
echo "2. Verifying enhanced health endpoint..."
test_endpoint "http://localhost:8004/api/v1/health" "status" "healthy"

echo ""
echo "3. Verifying stats endpoint..."
test_endpoint "http://localhost:8004/api/v1/stats" "timestamp" ""

echo ""
echo "4. Verifying alerts endpoint..."
test_endpoint "http://localhost:8004/api/v1/alerts" "" ""

echo ""
echo "5. Verifying dashboard..."
test_dashboard

echo ""
echo "6. Checking service logs..."
check_service_logs

echo ""
echo "7. Verifying TypeScript types..."
verify_types

echo ""
echo "=================================="
echo -e "${GREEN}🎉 Deployment verification completed successfully!${NC}"
echo "All systems are operational and the dashboard should be working correctly."
echo ""
echo "Next steps:"
echo "- Open http://localhost:3000 in your browser"
echo "- Verify the dashboard shows 'ALL SYSTEMS OPERATIONAL'"
echo "- Check that all core system components show healthy status"
echo "- Test navigation between dashboard tabs"
