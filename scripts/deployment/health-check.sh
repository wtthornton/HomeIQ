#!/bin/bash
#
# Comprehensive Deployment Health Check Script
# Checks health of all HomeIQ services for deployment validation
#
# Usage:
#   ./scripts/deployment/health-check.sh
#   ./scripts/deployment/health-check.sh --json
#   ./scripts/deployment/health-check.sh --critical-only
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
TIMEOUT=15
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

# Service definitions: name|health_url|port|critical
# Critical services are required for basic functionality
declare -A SERVICES
SERVICES[influxdb]="http://localhost:8086/health|8086|true"
SERVICES[websocket-ingestion]="http://localhost:8001/health|8001|true"
SERVICES[data-api]="http://localhost:8006/health|8006|true"
SERVICES[admin-api]="http://localhost:8004/health|8004|true"
SERVICES[health-dashboard]="http://localhost:3000|3000|true"
SERVICES[data-retention]="http://localhost:8080/health|8080|false"
SERVICES[weather-api]="http://localhost:8009/health|8009|false"
SERVICES[carbon-intensity]="http://localhost:8010/health|8010|false"
SERVICES[electricity-pricing]="http://localhost:8011/health|8011|false"
SERVICES[air-quality]="http://localhost:8012/health|8012|false"
SERVICES[calendar]="http://localhost:8013/health|8013|false"
SERVICES[smart-meter]="http://localhost:8014/health|8014|false"
SERVICES[log-aggregator]="http://localhost:8015/health|8015|false"
SERVICES[energy-correlator]="http://localhost:8017/health|8017|false"
SERVICES[ai-core-service]="http://localhost:8018/health|8018|false"
SERVICES[device-health-monitor]="http://localhost:8019/health|8019|false"
SERVICES[openai-service]="http://localhost:8020/health|8020|false"
SERVICES[device-setup-assistant]="http://localhost:8021/health|8021|false"
SERVICES[device-database-client]="http://localhost:8022/health|8022|false"
SERVICES[device-recommender]="http://localhost:8023/health|8023|false"
SERVICES[ml-service]="http://localhost:8025/health|8025|false"
SERVICES[openvino-service]="http://localhost:8026/health|8026|false"
SERVICES[ha-setup-service]="http://localhost:8027/health|8027|false"
SERVICES[device-intelligence]="http://localhost:8028/health|8028|false"
SERVICES[automation-miner]="http://localhost:8029/health|8029|false"
SERVICES[ha-ai-agent-service]="http://localhost:8030/health|8030|false"
SERVICES[proactive-agent-service]="http://localhost:8031/health|8031|false"
SERVICES[device-context-classifier]="http://localhost:8032/health|8032|false"
SERVICES[ai-training-service]="http://localhost:8033/health|8033|false"
SERVICES[ai-query-service]="http://localhost:8035/health|8035|false"
SERVICES[ai-automation-service-new]="http://localhost:8036/health|8036|false"
SERVICES[yaml-validation-service]="http://localhost:8037/health|8037|false"
SERVICES[ai-automation-ui]="http://localhost:3001|3001|false"

# Results
declare -A RESULTS
TOTAL=0
PASSED=0
FAILED=0
CRITICAL_PASSED=0
CRITICAL_FAILED=0

# Check container status
check_container() {
    local container_name=$1
    local status=$(docker ps --filter "name=${container_name}" --format "{{.Status}}" 2>/dev/null || echo "")
    if [[ -n "$status" ]] && [[ "$status" == *"Up"* ]]; then
        return 0
    fi
    return 1
}

# Check service health endpoint
check_service_health() {
    local service_name=$1
    local url=$2
    local port=$3
    local critical=$4
    
    TOTAL=$((TOTAL + 1))
    
    local result=""
    local status_code=0
    local response_time=0
    local container_status="unknown"
    
    # Skip non-critical if critical-only mode
    if [[ "$CRITICAL_ONLY" == "true" && "$critical" == "false" ]]; then
        return
    fi
    
    # Check container status first
    local container_name="homeiq-${service_name}"
    if check_container "$container_name"; then
        container_status="running"
    else
        # Try alternative container name patterns
        if check_container "${service_name}"; then
            container_status="running"
        else
            container_status="stopped"
            result="error"
            status_code="000"
            FAILED=$((FAILED + 1))
            if [[ "$critical" == "true" ]]; then
                CRITICAL_FAILED=$((CRITICAL_FAILED + 1))
            fi
            RESULTS["${service_name}_status"]=$result
            RESULTS["${service_name}_code"]=$status_code
            RESULTS["${service_name}_time"]=$response_time
            RESULTS["${service_name}_critical"]=$critical
            RESULTS["${service_name}_container"]=$container_status
            return
        fi
    fi
    
    # Measure response time and check health endpoint
    local start_time=$(date +%s%N)
    
    # Make request
    if response=$(curl -s -w "\n%{http_code}" --max-time "$TIMEOUT" "$url" 2>&1); then
        status_code=$(echo "$response" | tail -n1)
        response_time=$(($(date +%s%N) - start_time))
        response_time=$((response_time / 1000000)) # Convert to milliseconds
        
        if [[ "$status_code" == "200" ]] || [[ "$status_code" == "204" ]]; then
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
    RESULTS["${service_name}_container"]=$container_status
}

# Check database connectivity
check_database() {
    echo "Checking database connectivity..."
    
    # Check InfluxDB
    if curl -f -s --max-time "$TIMEOUT" "http://localhost:8086/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ InfluxDB is accessible${NC}"
    else
        echo -e "${RED}❌ InfluxDB is not accessible${NC}"
        FAILED=$((FAILED + 1))
        CRITICAL_FAILED=$((CRITICAL_FAILED + 1))
    fi
    
    # Check SQLite databases (via data-api)
    if curl -f -s --max-time "$TIMEOUT" "http://localhost:8006/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Data API (SQLite) is accessible${NC}"
    else
        echo -e "${RED}❌ Data API (SQLite) is not accessible${NC}"
        FAILED=$((FAILED + 1))
        CRITICAL_FAILED=$((CRITICAL_FAILED + 1))
    fi
}

# Main execution
main() {
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    
    echo "=========================================="
    echo "HomeIQ Deployment Health Check"
    echo "=========================================="
    echo "Timestamp: $timestamp"
    echo ""
    
    # Check database connectivity first
    check_database
    echo ""
    
    # Check all services
    echo "Checking services..."
    for service in "${!SERVICES[@]}"; do
        IFS='|' read -r url port critical <<< "${SERVICES[$service]}"
        check_service_health "$service" "$url" "$port" "$critical"
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
        echo "      \"status\": \"${RESULTS[${service}_status]:-unknown}\","
        echo "      \"status_code\": ${RESULTS[${service}_code]:-0},"
        echo "      \"response_time_ms\": ${RESULTS[${service}_time]:-0},"
        echo "      \"critical\": ${RESULTS[${service}_critical]},"
        echo "      \"container_status\": \"${RESULTS[${service}_container]:-unknown}\""
        echo "    }"
    done
    
    echo "  ]"
    echo "}"
}

# Text output
output_text() {
    local timestamp=$1
    local overall_status=$2
    
    echo ""
    echo "=========================================="
    echo "Health Check Summary"
    echo "=========================================="
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
        
        local status="${RESULTS[${service}_status]:-unknown}"
        local code="${RESULTS[${service}_code]:-0}"
        local time="${RESULTS[${service}_time]:-0}"
        local critical="${RESULTS[${service}_critical]}"
        local container="${RESULTS[${service}_container]:-unknown}"
        
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
        echo "      Container: $container"
    done
    
    echo ""
    echo "=========================================="
}

# Run main function
main "$@"

