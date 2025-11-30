#!/bin/bash

# Phase 1: Docker Service Validation
# Validates all Docker services are running and healthy

set -e

# Configuration
ADMIN_API_URL="${ADMIN_API_URL:-http://localhost:8003}"
REPORT_DIR="${REPORT_DIR:-implementation/verification}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Create report directory
mkdir -p "$REPORT_DIR"
REPORT_FILE="$REPORT_DIR/service-validation-$(date +%Y%m%d-%H%M%S).md"

# Validation results
SERVICES_HEALTHY=0
SERVICES_TOTAL=0
VALIDATION_PASSED=true

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$REPORT_FILE"
}

print_success() {
    echo -e "${GREEN}[✓ PASS]${NC} $1" | tee -a "$REPORT_FILE"
}

print_warning() {
    echo -e "${YELLOW}[⚠ WARN]${NC} $1" | tee -a "$REPORT_FILE"
}

print_error() {
    echo -e "${RED}[✗ FAIL]${NC} $1" | tee -a "$REPORT_FILE"
    VALIDATION_PASSED=false
}

# Initialize report
cat > "$REPORT_FILE" << EOF
# Service Validation Report
Generated: $(date)

## Phase 1: Docker Service Validation

EOF

print_status "Starting Phase 1: Docker Service Validation..."

### 1.1 Container Status Check
print_status "1.1 Checking container status..."

echo "" >> "$REPORT_FILE"
echo "### 1.1 Container Status Check" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# Get all containers
CONTAINERS=$(docker ps --format "{{.Names}}" | grep -E "^homeiq-|^ai-|^automation-")

CONTAINER_COUNT=$(echo "$CONTAINERS" | wc -l)
print_status "Found $CONTAINER_COUNT containers"

echo "**Total Containers:** $CONTAINER_COUNT" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "| Container Name | Status | Ports |" >> "$REPORT_FILE"
echo "|----------------|--------|-------|" >> "$REPORT_FILE"

while IFS= read -r container; do
    STATUS=$(docker ps --filter "name=$container" --format "{{.Status}}")
    PORTS=$(docker ps --filter "name=$container" --format "{{.Ports}}")
    
    if [ -n "$STATUS" ]; then
        print_success "Container $container: $STATUS"
        echo "| $container | $STATUS | $PORTS |" >> "$REPORT_FILE"
    else
        print_error "Container $container: NOT RUNNING"
        echo "| $container | NOT RUNNING | - |" >> "$REPORT_FILE"
        VALIDATION_PASSED=false
    fi
done <<< "$CONTAINERS"

# Check service health via admin-api
print_status "1.1.2 Checking service health via admin-api..."

if curl -s -f "$ADMIN_API_URL/api/v1/health/services" > /dev/null 2>&1; then
    print_success "Admin API health endpoint accessible"
    HEALTH_DATA=$(curl -s "$ADMIN_API_URL/api/v1/health/services")
    echo "" >> "$REPORT_FILE"
    echo "### Service Health Status (from Admin API)" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    echo '```json' >> "$REPORT_FILE"
    echo "$HEALTH_DATA" | jq '.' >> "$REPORT_FILE" 2>/dev/null || echo "$HEALTH_DATA" >> "$REPORT_FILE"
    echo '```' >> "$REPORT_FILE"
else
    print_error "Admin API health endpoint not accessible"
    VALIDATION_PASSED=false
fi

### 1.2 Health Endpoint Validation
print_status "1.2 Validating individual health endpoints..."

echo "" >> "$REPORT_FILE"
echo "### 1.2 Health Endpoint Validation" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "| Service | Port | Status | Response Time (ms) | Type |" >> "$REPORT_FILE"
echo "|---------|------|--------|-------------------|------|" >> "$REPORT_FILE"

# Define all services and their ports
# Define services - separate required from optional
declare -A REQUIRED_SERVICES=(
    ["websocket-ingestion"]="8001"
    ["data-api"]="8006"
    ["admin-api"]="8003"
    ["influxdb"]="8086"
    ["smart-meter"]="8014"
    ["ai-automation-service"]="8024"
    ["ai-core-service"]="8018"
    ["openvino-service"]="8026"
    ["ml-service"]="8025"
    ["ner-service"]="8031"
    ["openai-service"]="8020"
    ["device-intelligence-service"]="8028"
    ["device-health-monitor"]="8019"
    ["device-context-classifier"]="8032"
    ["device-setup-assistant"]="8021"
    ["device-database-client"]="8022"
    ["device-recommender"]="8023"
    ["energy-correlator"]="8017"
    ["log-aggregator"]="8015"
    ["ha-setup-service"]="8027"
    ["automation-miner"]="8029"
    ["ai-training-service"]="8033"
    ["ai-pattern-service"]="8034"
    ["ai-query-service"]="8035"
    ["ai-code-executor"]="8030"
    ["health-dashboard"]="3000"
    ["ai-automation-ui"]="3001"
)

# Optional services that need API keys (from docker-compose.yml profiles)
declare -A OPTIONAL_SERVICES=(
    ["weather-api"]="8009"
    ["carbon-intensity"]="8010"
    ["electricity-pricing"]="8011"
    ["air-quality"]="8012"
    ["data-retention"]="8080"
)

# Combine all services for checking
declare -A SERVICES=()
for service in "${!REQUIRED_SERVICES[@]}"; do
    SERVICES["$service"]="${REQUIRED_SERVICES[$service]}"
done
for service in "${!OPTIONAL_SERVICES[@]}"; do
    SERVICES["$service"]="${OPTIONAL_SERVICES[$service]}"
done

# Check required services (failures are critical)
for service in "${!REQUIRED_SERVICES[@]}"; do
    port="${REQUIRED_SERVICES[$service]}"
    SERVICES_TOTAL=$((SERVICES_TOTAL + 1))
    
    START_TIME=$(date +%s%N)
    
    if curl -s -f "http://localhost:$port/health" > /dev/null 2>&1; then
        END_TIME=$(date +%s%N)
        RESPONSE_TIME=$(( (END_TIME - START_TIME) / 1000000 ))
        
        SERVICES_HEALTHY=$((SERVICES_HEALTHY + 1))
        print_success "$service ($port): Healthy (${RESPONSE_TIME}ms)"
        echo "| $service | $port | ✓ Healthy | $RESPONSE_TIME | Required |" >> "$REPORT_FILE"
    else
        print_error "$service ($port): Unhealthy or not responding [REQUIRED]"
        echo "| $service | $port | ✗ Failed | - | Required |" >> "$REPORT_FILE"
        VALIDATION_PASSED=false
    fi
done

# Check optional services (failures are warnings, not errors)
for service in "${!OPTIONAL_SERVICES[@]}"; do
    port="${OPTIONAL_SERVICES[$service]}"
    SERVICES_TOTAL=$((SERVICES_TOTAL + 1))
    
    START_TIME=$(date +%s%N)
    
    if curl -s -f "http://localhost:$port/health" > /dev/null 2>&1; then
        END_TIME=$(date +%s%N)
        RESPONSE_TIME=$(( (END_TIME - START_TIME) / 1000000 ))
        
        SERVICES_HEALTHY=$((SERVICES_HEALTHY + 1))
        print_success "$service ($port): Healthy (${RESPONSE_TIME}ms) [Optional]"
        echo "| $service | $port | ✓ Healthy | $RESPONSE_TIME | Optional |" >> "$REPORT_FILE"
    else
        print_warning "$service ($port): Unhealthy or not responding [OPTIONAL - needs API key]"
        echo "| $service | $port | ⚠ Skipped | - | Optional |" >> "$REPORT_FILE"
        # Don't fail validation for optional services
    fi
done

### 1.3 Service Dependencies Validation
print_status "1.3 Validating service dependencies..."

echo "" >> "$REPORT_FILE"
echo "### 1.3 Service Dependencies Validation" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

if curl -s -f "$ADMIN_API_URL/api/v1/health/dependencies" > /dev/null 2>&1; then
    print_success "Dependency health check endpoint accessible"
    DEP_DATA=$(curl -s "$ADMIN_API_URL/api/v1/health/dependencies")
    echo '```json' >> "$REPORT_FILE"
    echo "$DEP_DATA" | jq '.' >> "$REPORT_FILE" 2>/dev/null || echo "$DEP_DATA" >> "$REPORT_FILE"
    echo '```' >> "$REPORT_FILE"
else
    print_warning "Dependency health check endpoint not accessible (may not be implemented)"
    echo "**Note:** Dependency endpoint may not be fully implemented" >> "$REPORT_FILE"
fi

### 1.4 Resource Usage Check
print_status "1.4 Checking resource usage..."

echo "" >> "$REPORT_FILE"
echo "### 1.4 Resource Usage Check" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

RESOURCE_FILE="$REPORT_DIR/resource-usage-$(date +%Y%m%d-%H%M%S).txt"
docker stats --no-stream > "$RESOURCE_FILE" 2>&1 || print_warning "Could not get resource stats"

if [ -f "$RESOURCE_FILE" ]; then
    print_success "Resource usage captured"
    echo "Resource usage details saved to: \`$RESOURCE_FILE\`" >> "$REPORT_FILE"
    
    # Check for high memory usage
    HIGH_MEMORY=$(grep -v "CONTAINER" "$RESOURCE_FILE" | awk '{if ($4+0 > 90) print $1, $4}' || true)
    if [ -n "$HIGH_MEMORY" ]; then
        print_warning "Some containers have high memory usage:"
        echo "$HIGH_MEMORY"
        echo "" >> "$REPORT_FILE"
        echo "**Warning:** High memory usage detected:" >> "$REPORT_FILE"
        echo "$HIGH_MEMORY" >> "$REPORT_FILE"
    fi
fi

# Summary
echo "" >> "$REPORT_FILE"
echo "## Summary" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "- **Total Services Checked:** $SERVICES_TOTAL" >> "$REPORT_FILE"
echo "- **Healthy Services:** $SERVICES_HEALTHY" >> "$REPORT_FILE"
echo "- **Failed Services:** $((SERVICES_TOTAL - SERVICES_HEALTHY))" >> "$REPORT_FILE"
echo "- **Success Rate:** $(awk "BEGIN {printf \"%.1f\", ($SERVICES_HEALTHY/$SERVICES_TOTAL)*100}")%" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

if [ "$VALIDATION_PASSED" = true ]; then
    echo "**Status:** ✅ All validations passed" >> "$REPORT_FILE"
    print_success "Phase 1 validation complete - All services healthy"
    exit 0
else
    echo "**Status:** ❌ Some validations failed" >> "$REPORT_FILE"
    print_error "Phase 1 validation complete - Some issues found"
    exit 1
fi

