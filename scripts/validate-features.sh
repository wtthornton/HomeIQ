#!/bin/bash

# Phase 2: Feature Validation
# Validates all features are implemented and working correctly

set -e

# Load environment variables from .env file if it exists
if [ -f .env ]; then
    set -a
    export $(grep -v '^#' .env | grep -v '^$' | sed 's/\r$//' | xargs) 2>/dev/null || true
    set +a
fi

# Configuration
DATA_API_URL="${DATA_API_URL:-http://localhost:8006}"
ADMIN_API_URL="${ADMIN_API_URL:-http://localhost:8003}"
WEBSOCKET_URL="${WEBSOCKET_URL:-http://localhost:8001}"
HA_URL="${HA_HTTP_URL:-${HOME_ASSISTANT_URL:-http://192.168.1.86:8123}}"
REPORT_DIR="${REPORT_DIR:-implementation/verification}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Create report directory
mkdir -p "$REPORT_DIR"
REPORT_FILE="$REPORT_DIR/feature-validation-$(date +%Y%m%d-%H%M%S).md"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

# Validation results
FEATURES_TESTED=0
FEATURES_PASSED=0
VALIDATION_PASSED=true

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$REPORT_FILE"
}

print_success() {
    echo -e "${GREEN}[✓ PASS]${NC} $1" | tee -a "$REPORT_FILE"
    FEATURES_PASSED=$((FEATURES_PASSED + 1))
}

print_warning() {
    echo -e "${YELLOW}[⚠ WARN]${NC} $1" | tee -a "$REPORT_FILE"
}

print_error() {
    echo -e "${RED}[✗ FAIL]${NC} $1" | tee -a "$REPORT_FILE"
    VALIDATION_PASSED=false
}

test_endpoint() {
    local url=$1
    local description=$2
    local method=${3:-GET}
    
    FEATURES_TESTED=$((FEATURES_TESTED + 1))
    
    if [ "$method" = "GET" ]; then
        if curl -s -f -w "\n%{http_code}" "$url" > /tmp/response.txt 2>/dev/null; then
            HTTP_CODE=$(tail -n 1 /tmp/response.txt)
            if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "201" ]; then
                print_success "$description - HTTP $HTTP_CODE"
                return 0
            else
                print_error "$description - HTTP $HTTP_CODE"
                return 1
            fi
        else
            print_error "$description - Connection failed"
            return 1
        fi
    else
        # POST request
        if curl -s -f -X POST -w "\n%{http_code}" "$url" > /tmp/response.txt 2>/dev/null; then
            HTTP_CODE=$(tail -n 1 /tmp/response.txt)
            if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "201" ]; then
                print_success "$description - HTTP $HTTP_CODE"
                return 0
            else
                print_error "$description - HTTP $HTTP_CODE"
                return 1
            fi
        else
            print_error "$description - Connection failed"
            return 1
        fi
    fi
}

# Initialize report
cat > "$REPORT_FILE" << EOF
# Feature Validation Report
Generated: $(date)

## Phase 2: Feature Validation

This report validates all features are implemented and working correctly.

EOF

print_status "Starting Phase 2: Feature Validation..."

### 2.1 Event Ingestion
print_status "2.1 Validating Event Ingestion (websocket-ingestion)..."

echo "" >> "$REPORT_FILE"
echo "### 2.1 Event Ingestion" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# Check WebSocket connection status
if test_endpoint "$WEBSOCKET_URL/health" "WebSocket service health"; then
    HEALTH_RESPONSE=$(curl -s "$WEBSOCKET_URL/health")
    echo "**WebSocket Health Response:**" >> "$REPORT_FILE"
    echo '```json' >> "$REPORT_FILE"
    echo "$HEALTH_RESPONSE" | jq '.' >> "$REPORT_FILE" 2>/dev/null || echo "$HEALTH_RESPONSE" >> "$REPORT_FILE"
    echo '```' >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    
    # Check HA connection status
    if echo "$HEALTH_RESPONSE" | grep -q "ha_connected\|connected" || echo "$HEALTH_RESPONSE" | jq -e '.ha_connected // .connected' > /dev/null 2>&1; then
        print_success "Home Assistant connection active"
        echo "✅ **HA Connection:** Active" >> "$REPORT_FILE"
    else
        print_warning "Home Assistant connection status unclear"
        echo "⚠️ **HA Connection:** Status unclear" >> "$REPORT_FILE"
    fi
fi

# Check for recent events in InfluxDB (via data-api)
print_status "Checking for recent events..."
if test_endpoint "$DATA_API_URL/api/v1/events?limit=10" "Recent events query"; then
    EVENTS_RESPONSE=$(curl -s "$DATA_API_URL/api/v1/events?limit=10")
    EVENT_COUNT=$(echo "$EVENTS_RESPONSE" | jq '. | length' 2>/dev/null || echo "0")
    if [ "$EVENT_COUNT" -gt 0 ]; then
        print_success "Found $EVENT_COUNT recent events"
        echo "✅ **Recent Events:** $EVENT_COUNT events found" >> "$REPORT_FILE"
        
        # Check Epic 23 fields
        FIRST_EVENT=$(echo "$EVENTS_RESPONSE" | jq '.[0]' 2>/dev/null)
        if [ -n "$FIRST_EVENT" ]; then
            HAS_CONTEXT_ID=$(echo "$FIRST_EVENT" | jq 'has("context_id")' 2>/dev/null || echo "false")
            HAS_DEVICE_ID=$(echo "$FIRST_EVENT" | jq 'has("device_id")' 2>/dev/null || echo "false")
            HAS_AREA_ID=$(echo "$FIRST_EVENT" | jq 'has("area_id")' 2>/dev/null || echo "false")
            
            if [ "$HAS_CONTEXT_ID" = "true" ] && [ "$HAS_DEVICE_ID" = "true" ] && [ "$HAS_AREA_ID" = "true" ]; then
                print_success "Epic 23 fields present (context_id, device_id, area_id)"
                echo "✅ **Epic 23 Fields:** Present" >> "$REPORT_FILE"
            else
                print_warning "Some Epic 23 fields missing"
                echo "⚠️ **Epic 23 Fields:** Some missing" >> "$REPORT_FILE"
            fi
        fi
    else
        print_warning "No recent events found"
        echo "⚠️ **Recent Events:** None found" >> "$REPORT_FILE"
    fi
fi

### 2.2 Data API Endpoints
print_status "2.2 Validating Data API Endpoints..."

echo "" >> "$REPORT_FILE"
echo "### 2.2 Data API Endpoints" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "| Endpoint | Method | Status |" >> "$REPORT_FILE"
echo "|----------|--------|--------|" >> "$REPORT_FILE"

# Events endpoints
test_endpoint "$DATA_API_URL/api/v1/events" "GET /api/v1/events" && echo "| GET /api/v1/events | GET | ✓ |" >> "$REPORT_FILE" || echo "| GET /api/v1/events | GET | ✗ |" >> "$REPORT_FILE"
test_endpoint "$DATA_API_URL/api/v1/events/stats" "GET /api/v1/events/stats" && echo "| GET /api/v1/events/stats | GET | ✓ |" >> "$REPORT_FILE" || echo "| GET /api/v1/events/stats | GET | ✗ |" >> "$REPORT_FILE"

# Devices endpoints (correct paths)
test_endpoint "$DATA_API_URL/api/devices" "GET /api/devices" && echo "| GET /api/devices | GET | ✓ |" >> "$REPORT_FILE" || echo "| GET /api/devices | GET | ✗ |" >> "$REPORT_FILE"
test_endpoint "$DATA_API_URL/api/entities" "GET /api/entities" && echo "| GET /api/entities | GET | ✓ |" >> "$REPORT_FILE" || echo "| GET /api/entities | GET | ✗ |" >> "$REPORT_FILE"

# Analytics endpoints (check correct paths)
test_endpoint "$DATA_API_URL/api/v1/analytics/realtime" "GET /api/v1/analytics/realtime" && echo "| GET /api/v1/analytics/realtime | GET | ✓ |" >> "$REPORT_FILE" || echo "| GET /api/v1/analytics/realtime | GET | ✗ |" >> "$REPORT_FILE"
test_endpoint "$DATA_API_URL/api/v1/analytics/entity-activity" "GET /api/v1/analytics/entity-activity" && echo "| GET /api/v1/analytics/entity-activity | GET | ✓ |" >> "$REPORT_FILE" || echo "| GET /api/v1/analytics/entity-activity | GET | ✗ |" >> "$REPORT_FILE"

### 2.3 Device Intelligence Features
print_status "2.3 Validating Device Intelligence Features..."

echo "" >> "$REPORT_FILE"
echo "### 2.3 Device Intelligence Features" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

test_endpoint "http://localhost:8028/health" "Device Intelligence Service health" && echo "✅ Device Intelligence Service: Healthy" >> "$REPORT_FILE" || echo "✗ Device Intelligence Service: Unhealthy" >> "$REPORT_FILE"
test_endpoint "http://localhost:8019/health" "Device Health Monitor health" && echo "✅ Device Health Monitor: Healthy" >> "$REPORT_FILE" || echo "✗ Device Health Monitor: Unhealthy" >> "$REPORT_FILE"
test_endpoint "http://localhost:8032/health" "Device Context Classifier health" && echo "✅ Device Context Classifier: Healthy" >> "$REPORT_FILE" || echo "✗ Device Context Classifier: Unhealthy" >> "$REPORT_FILE"

### 2.4 AI Automation Features
print_status "2.4 Validating AI Automation Features..."

echo "" >> "$REPORT_FILE"
echo "### 2.4 AI Automation Features" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

test_endpoint "http://localhost:8024/health" "AI Automation Service health" && echo "✅ AI Automation Service: Healthy" >> "$REPORT_FILE" || echo "✗ AI Automation Service: Unhealthy" >> "$REPORT_FILE"
test_endpoint "http://localhost:8018/health" "AI Core Service health" && echo "✅ AI Core Service: Healthy" >> "$REPORT_FILE" || echo "✗ AI Core Service: Unhealthy" >> "$REPORT_FILE"

### 2.5 Frontend Dashboards
print_status "2.5 Validating Frontend Dashboards..."

echo "" >> "$REPORT_FILE"
echo "### 2.5 Frontend Dashboards" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

test_endpoint "http://localhost:3000" "Health Dashboard" && echo "✅ Health Dashboard: Accessible" >> "$REPORT_FILE" || echo "✗ Health Dashboard: Not accessible" >> "$REPORT_FILE"
test_endpoint "http://localhost:3001" "AI Automation UI" && echo "✅ AI Automation UI: Accessible" >> "$REPORT_FILE" || echo "✗ AI Automation UI: Not accessible" >> "$REPORT_FILE"

### 2.6 External Service Integrations
print_status "2.6 Validating External Service Integrations..."

echo "" >> "$REPORT_FILE"
echo "### 2.6 External Service Integrations" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

test_endpoint "http://localhost:8009/health" "Weather API" && echo "✅ Weather API: Healthy" >> "$REPORT_FILE" || echo "⚠️ Weather API: Not healthy (may be optional)" >> "$REPORT_FILE"
test_endpoint "http://localhost:8010/health" "Carbon Intensity Service" && echo "✅ Carbon Intensity Service: Healthy" >> "$REPORT_FILE" || echo "⚠️ Carbon Intensity Service: Not healthy (may be optional)" >> "$REPORT_FILE"
test_endpoint "http://localhost:8011/health" "Electricity Pricing Service" && echo "✅ Electricity Pricing Service: Healthy" >> "$REPORT_FILE" || echo "⚠️ Electricity Pricing Service: Not healthy (may be optional)" >> "$REPORT_FILE"
test_endpoint "http://localhost:8012/health" "Air Quality Service" && echo "✅ Air Quality Service: Healthy" >> "$REPORT_FILE" || echo "⚠️ Air Quality Service: Not healthy (may be optional)" >> "$REPORT_FILE"
test_endpoint "http://localhost:8014/health" "Smart Meter Service" && echo "✅ Smart Meter Service: Healthy" >> "$REPORT_FILE" || echo "⚠️ Smart Meter Service: Not healthy (may be optional)" >> "$REPORT_FILE"

# Summary
echo "" >> "$REPORT_FILE"
echo "## Summary" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "- **Features Tested:** $FEATURES_TESTED" >> "$REPORT_FILE"
echo "- **Features Passed:** $FEATURES_PASSED" >> "$REPORT_FILE"
echo "- **Success Rate:** $(awk "BEGIN {printf \"%.1f\", ($FEATURES_PASSED/$FEATURES_TESTED)*100}")%" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

if [ "$VALIDATION_PASSED" = true ]; then
    echo "**Status:** ✅ All critical features validated" >> "$REPORT_FILE"
    print_success "Phase 2 validation complete"
    exit 0
else
    echo "**Status:** ⚠️ Some features need attention" >> "$REPORT_FILE"
    print_warning "Phase 2 validation complete - Some issues found"
    exit 1
fi

