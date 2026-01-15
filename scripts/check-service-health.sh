#!/bin/bash
#
# Service Health Check Script
# Checks health of all HomeIQ services and reports status
#
# Usage:
#   ./scripts/check-service-health.sh
#   ./scripts/check-service-health.sh --json
#   ./scripts/check-service-health.sh --critical-only
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
TIMEOUT=10
JSON_OUTPUT=false
CRITICAL_ONLY=false
OUTPUT_FILE=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --json)
            JSON_OUTPUT=true
            shift
            ;;
        --critical-only)
            CRITICAL_ONLY=true
            shift
            ;;
        --output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--json] [--critical-only] [--output FILE] [--timeout SECONDS]"
            exit 1
            ;;
    esac
done

# Service definitions
declare -A SERVICES
SERVICES[websocket-ingestion]="http://localhost:8001/health|true"
SERVICES[data-api]="http://localhost:8006/health|true"
SERVICES[admin-api]="http://localhost:8003/api/v1/health|true"
SERVICES[influxdb]="http://localhost:8086/health|true"
SERVICES[health-dashboard]="http://localhost:3000|true"
SERVICES[ai-automation-service]="http://localhost:8024/health|false"
SERVICES[homeiq-ai-automation-service-new]="http://localhost:8025/health|false"
SERVICES[homeiq-ai-pattern-service]="http://localhost:8034/health|false"
SERVICES[device-intelligence]="http://localhost:8028/health|false"
SERVICES[weather-api]="http://localhost:8009/health|false"
SERVICES[carbon-intensity]="http://localhost:8010/health|false"
SERVICES[air-quality]="http://localhost:8012/health|false"

# Results
declare -A RESULTS
TOTAL=0
PASSED=0
FAILED=0
CRITICAL_PASSED=0
CRITICAL_FAILED=0

# Check service health
check_service() {
    local service_name=$1
    local url=$2
    local critical=$3
    
    TOTAL=$((TOTAL + 1))
    
    local result=""
    local status_code=0
    local response_time=0
    
    # Skip non-critical if critical-only mode
    if [[ "$CRITICAL_ONLY" == "true" && "$critical" == "false" ]]; then
        return
    fi
    
    # Measure response time
    local start_time=$(date +%s%N)
    
    # Make request
    if response=$(curl -s -w "\n%{http_code}" --max-time "$TIMEOUT" "$url" 2>&1); then
        status_code=$(echo "$response" | tail -n1)
        response_time=$(($(date +%s%N) - start_time))
        response_time=$((response_time / 1000000)) # Convert to milliseconds
        
        if [[ "$status_code" == "200" ]]; then
            result="healthy"
            PASSED=$((PASSED + 1))
            if [[ "$critical" == "true" ]]; then
                CRITICAL_PASSED=$((CRITICAL_PASSED + 1))
            fi
        else
            result="unhealthy"
            FAILED=$((FAILED + 1))
            if [[ "$critical" == "true" ]]; then
                CRITICAL_FAILED=$((CRITICAL_FAILED + 1))
            fi
        fi
    else
        result="error"
        status_code="000"
        response_time=0
        FAILED=$((FAILED + 1))
        if [[ "$critical" == "true" ]]; then
            CRITICAL_FAILED=$((CRITICAL_FAILED + 1))
        fi
    fi
    
    RESULTS["${service_name}_status"]=$result
    RESULTS["${service_name}_code"]=$status_code
    RESULTS["${service_name}_time"]=$response_time
    RESULTS["${service_name}_critical"]=$critical
}

# Main execution
main() {
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    
    # Check all services
    for service in "${!SERVICES[@]}"; do
        IFS='|' read -r url critical <<< "${SERVICES[$service]}"
        check_service "$service" "$url" "$critical"
    done
    
    # Determine overall status
    local overall_status="pass"
    if [[ $CRITICAL_FAILED -gt 0 ]]; then
        overall_status="fail"
    elif [[ $FAILED -gt 0 ]]; then
        overall_status="degraded"
    fi
    
    # Output results
    if [[ "$JSON_OUTPUT" == "true" ]]; then
        output_json "$timestamp" "$overall_status"
    else
        output_text "$timestamp" "$overall_status"
    fi
    
    # Save to file if requested
    if [[ -n "$OUTPUT_FILE" ]]; then
        output_json "$timestamp" "$overall_status" > "$OUTPUT_FILE"
    fi
    
    # Exit with appropriate code
    if [[ "$overall_status" == "fail" ]]; then
        exit 1
    elif [[ "$overall_status" == "degraded" ]]; then
        exit 2
    else
        exit 0
    fi
}

# JSON output
output_json() {
    local timestamp=$1
    local overall_status=$2
    
    echo "{"
    echo "  \"timestamp\": \"$timestamp\","
    echo "  \"overall_status\": \"$overall_status\","
    echo "  \"summary\": {"
    echo "    \"total\": $TOTAL,"
    echo "    \"passed\": $PASSED,"
    echo "    \"failed\": $FAILED,"
    echo "    \"critical_passed\": $CRITICAL_PASSED,"
    echo "    \"critical_failed\": $CRITICAL_FAILED"
    echo "  },"
    echo "  \"services\": ["
    
    local first=true
    for service in "${!SERVICES[@]}"; do
        if [[ "$CRITICAL_ONLY" == "true" && "${RESULTS[${service}_critical]}" == "false" ]]; then
            continue
        fi
        
        if [[ "$first" == "false" ]]; then
            echo ","
        fi
        first=false
        
        echo "    {"
        echo "      \"name\": \"$service\","
        echo "      \"status\": \"${RESULTS[${service}_status]}\","
        echo "      \"status_code\": ${RESULTS[${service}_code]},"
        echo "      \"response_time_ms\": ${RESULTS[${service}_time]},"
        echo "      \"critical\": ${RESULTS[${service}_critical]}"
        echo "    }"
    done
    
    echo "  ]"
    echo "}"
}

# Text output
output_text() {
    local timestamp=$1
    local overall_status=$2
    
    echo "=========================================="
    echo "HomeIQ Service Health Check"
    echo "=========================================="
    echo "Timestamp: $timestamp"
    echo "Overall Status: $overall_status"
    echo ""
    echo "Summary:"
    echo "  Total Services: $TOTAL"
    echo "  Passed: $PASSED"
    echo "  Failed: $FAILED"
    echo "  Critical Passed: $CRITICAL_PASSED"
    echo "  Critical Failed: $CRITICAL_FAILED"
    echo ""
    echo "Service Details:"
    
    for service in "${!SERVICES[@]}"; do
        if [[ "$CRITICAL_ONLY" == "true" && "${RESULTS[${service}_critical]}" == "false" ]]; then
            continue
        fi
        
        local status="${RESULTS[${service}_status]}"
        local code="${RESULTS[${service}_code]}"
        local time="${RESULTS[${service}_time]}"
        local critical="${RESULTS[${service}_critical]}"
        
        local status_color=""
        local status_icon=""
        if [[ "$status" == "healthy" ]]; then
            status_color=$GREEN
            status_icon="✅"
        else
            status_color=$RED
            status_icon="❌"
        fi
        
        local critical_marker=""
        if [[ "$critical" == "true" ]]; then
            critical_marker=" [CRITICAL]"
        fi
        
        echo -e "  $status_icon $status_color$service$NC$critical_marker"
        echo "      Status: $status (HTTP $code)"
        echo "      Response Time: ${time}ms"
    done
    
    echo ""
    echo "=========================================="
}

# Run main function
main "$@"

