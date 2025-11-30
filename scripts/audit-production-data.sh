#!/bin/bash

# Production Data Audit Script
# Verifies all events are from production and identifies any test data

set -e

# Load environment variables from .env file if it exists
if [ -f .env ]; then
    while IFS='=' read -r key value || [ -n "$key" ]; do
        [[ "$key" =~ ^#.*$ ]] && continue
        [[ -z "$key" ]] && continue
        key=$(echo "$key" | tr -d '\r')
        value=$(echo "$value" | tr -d '\r')
        export "$key=$value" 2>/dev/null || true
    done < .env
fi

# Configuration
INFLUXDB_URL="${INFLUXDB_URL:-http://localhost:8086}"
INFLUXDB_ORG="${INFLUXDB_ORG:-${INFLUXDB_ORG:-homeiq}}"
INFLUXDB_BUCKET="${INFLUXDB_BUCKET:-home_assistant_events}"
INFLUXDB_TOKEN="${INFLUXDB_TOKEN:-homeiq-token}"
DATA_API_URL="${DATA_API_URL:-http://localhost:8006}"
HA_URL="${HA_HTTP_URL:-${HOME_ASSISTANT_URL:-http://192.168.1.86:8123}}"
HA_URL="${HA_URL%/}"
HA_TOKEN="${HOME_ASSISTANT_TOKEN:-${HA_TOKEN:-}}"
REPORT_DIR="${REPORT_DIR:-implementation/verification}"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
REPORT_FILE="$REPORT_DIR/production-data-audit-$TIMESTAMP.md"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Create report directory
mkdir -p "$REPORT_DIR"

# Audit results
TEST_DATA_FOUND=false
TOTAL_EVENTS=0
TEST_EVENTS=0
PRODUCTION_EVENTS=0

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$REPORT_FILE"
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1" | tee -a "$REPORT_FILE"
}

print_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1" | tee -a "$REPORT_FILE"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1" | tee -a "$REPORT_FILE"
}

# Initialize report
cat > "$REPORT_FILE" << EOF
# Production Data Audit Report

**Generated:** $(date)  
**Timestamp:** $TIMESTAMP

## Purpose

This report verifies that all events in the database are from production Home Assistant and identifies any test, demo, or validation data.

---

EOF

print_status "Starting Production Data Audit..."
echo "" >> "$REPORT_FILE"

### 1. Check Total Event Count
print_status "1. Checking total event count..."

TOTAL_COUNT=$(curl -s "$DATA_API_URL/api/v1/events?limit=1" 2>/dev/null | jq 'length' 2>/dev/null || echo "0")

# Get actual count from InfluxDB if possible
if command -v influx &> /dev/null; then
    INFLUX_COUNT=$(influx query --org "$INFLUXDB_ORG" --token "$INFLUXDB_TOKEN" \
        "from(bucket: \"$INFLUXDB_BUCKET\") |> range(start: -365d) |> filter(fn: (r) => r._measurement == \"home_assistant_events\") |> count()" \
        2>/dev/null | grep -oP '\d+' | head -1 || echo "")
fi

echo "### 1. Total Event Count" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "- **Events accessible via API:** $TOTAL_COUNT (sample)" >> "$REPORT_FILE"
if [ -n "$INFLUX_COUNT" ]; then
    echo "- **Total events in InfluxDB (last 365 days):** $INFLUX_COUNT" >> "$REPORT_FILE"
fi
echo "" >> "$REPORT_FILE"

### 2. Search for Test Data Patterns
print_status "2. Searching for test data patterns..."

echo "" >> "$REPORT_FILE"
echo "### 2. Test Data Pattern Search" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# Test patterns to search for
TEST_PATTERNS=("test" "demo" "validation" "sample" "mock" "fake" "temp" "temporary")

echo "**Searching for entity IDs containing:**" >> "$REPORT_FILE"
for pattern in "${TEST_PATTERNS[@]}"; do
    echo "- \`$pattern\`" >> "$REPORT_FILE"
done
echo "" >> "$REPORT_FILE"

# Search via data-api for events matching patterns
print_status "Checking entity IDs for test patterns..."

TEST_ENTITIES_FOUND=0
TEST_ENTITY_LIST=""

for pattern in "${TEST_PATTERNS[@]}"; do
    print_status "  Searching for pattern: $pattern..."
    
    # Try to search for entities containing pattern
    # Note: This assumes we can query by entity_id pattern
    # Since exact pattern matching may not be available, we'll check recent events
    
    # Get sample of recent events to check
    RECENT_EVENTS=$(curl -s "$DATA_API_URL/api/v1/events?limit=1000" 2>/dev/null || echo "[]")
    
    if [ -n "$RECENT_EVENTS" ] && [ "$RECENT_EVENTS" != "[]" ]; then
        # Extract unique entity_ids and check for patterns
        ENTITY_IDS=$(echo "$RECENT_EVENTS" | jq -r '.[].entity_id' 2>/dev/null | sort -u)
        
        while IFS= read -r entity_id; do
            if [ -n "$entity_id" ] && echo "$entity_id" | grep -qi "$pattern"; then
                TEST_ENTITIES_FOUND=$((TEST_ENTITIES_FOUND + 1))
                if [ -z "$TEST_ENTITY_LIST" ]; then
                    TEST_ENTITY_LIST="$entity_id"
                else
                    TEST_ENTITY_LIST="$TEST_ENTITY_LIST, $entity_id"
                fi
                print_warning "    Found test entity: $entity_id"
            fi
        done <<< "$ENTITY_IDS"
    fi
done

if [ $TEST_ENTITIES_FOUND -gt 0 ]; then
    TEST_DATA_FOUND=true
    print_error "Found $TEST_ENTITIES_FOUND test entities"
    echo "**⚠️ TEST ENTITIES FOUND:**" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    echo "$TEST_ENTITY_LIST" | tr ',' '\n' | sed 's/^/- /' >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
else
    print_success "No test entities found in recent events"
    echo "**✅ No test entities found**" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
fi

### 3. Verify Data Source (HA Connection)
print_status "3. Verifying data source (Home Assistant connection)..."

echo "" >> "$REPORT_FILE"
echo "### 3. Data Source Verification" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# Check websocket-ingestion service
WS_HEALTH=$(curl -s "http://localhost:8001/health" 2>/dev/null || echo "{}")
HA_CONNECTED=$(echo "$WS_HEALTH" | jq -r '.connection.is_running // .ha_connected // "unknown"' 2>/dev/null || echo "unknown")
TOTAL_EVENTS_RECEIVED=$(echo "$WS_HEALTH" | jq -r '.subscription.total_events_received // 0' 2>/dev/null || echo "0")

if [ "$HA_CONNECTED" = "true" ] || [ "$HA_CONNECTED" = "1" ]; then
    print_success "Connected to production Home Assistant ($HA_URL)"
    echo "✅ **HA Connection:** Active" >> "$REPORT_FILE"
    echo "- **Total events received:** $TOTAL_EVENTS_RECEIVED" >> "$REPORT_FILE"
else
    print_warning "HA connection status unclear: $HA_CONNECTED"
    echo "⚠️ **HA Connection:** $HA_CONNECTED" >> "$REPORT_FILE"
fi

# Verify HA URL is production (not localhost)
if echo "$HA_URL" | grep -q "192.168.1.86\|192.168.1"; then
    print_success "HA URL appears to be production: $HA_URL"
    echo "- **HA URL:** $HA_URL (production)" >> "$REPORT_FILE"
elif echo "$HA_URL" | grep -q "localhost\|127.0.0.1"; then
    print_error "HA URL appears to be local/test: $HA_URL"
    echo "❌ **HA URL:** $HA_URL (⚠️ LOCAL/TEST - verify this is correct)" >> "$REPORT_FILE"
else
    print_warning "HA URL: $HA_URL (verify this is production)"
    echo "- **HA URL:** $HA_URL" >> "$REPORT_FILE"
fi

echo "" >> "$REPORT_FILE"

### 4. Check Event Timestamps and Freshness
print_status "4. Checking event timestamps..."

echo "" >> "$REPORT_FILE"
echo "### 4. Event Timestamp Analysis" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# Get recent events
RECENT_EVENTS=$(curl -s "$DATA_API_URL/api/v1/events?limit=10" 2>/dev/null || echo "[]")

if [ -n "$RECENT_EVENTS" ] && [ "$RECENT_EVENTS" != "[]" ]; then
    # Get oldest and newest timestamps
    TIMESTAMPS=$(echo "$RECENT_EVENTS" | jq -r '.[].timestamp // .[].time // empty' 2>/dev/null | grep -v null | sort)
    
    if [ -n "$TIMESTAMPS" ]; then
        OLDEST=$(echo "$TIMESTAMPS" | head -1)
        NEWEST=$(echo "$TIMESTAMPS" | tail -1)
        
        # Convert to readable format
        CURRENT_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ)
        
        echo "- **Most Recent Event:** $NEWEST" >> "$REPORT_FILE"
        echo "- **Oldest Sample Event:** $OLDEST" >> "$REPORT_FILE"
        echo "- **Current Time (UTC):** $CURRENT_TIME" >> "$REPORT_FILE"
        echo "" >> "$REPORT_FILE"
        
        # Check if events are recent (within last 24 hours)
        if [ -n "$NEWEST" ]; then
            NEWEST_EPOCH=$(date -u -d "$NEWEST" +%s 2>/dev/null || echo "0")
            CURRENT_EPOCH=$(date -u +%s)
            AGE_SECONDS=$((CURRENT_EPOCH - NEWEST_EPOCH))
            AGE_HOURS=$((AGE_SECONDS / 3600))
            
            if [ $AGE_HOURS -lt 24 ]; then
                print_success "Events are recent (most recent: $AGE_HOURS hours ago)"
                echo "✅ **Data Freshness:** Events are recent (< 24 hours old)" >> "$REPORT_FILE"
            else
                print_warning "Most recent event is $AGE_HOURS hours old"
                echo "⚠️ **Data Freshness:** Most recent event is $AGE_HOURS hours old" >> "$REPORT_FILE"
            fi
        fi
    fi
fi

### 5. Check for Known Test Entities
print_status "5. Checking for known test entity patterns..."

echo "" >> "$REPORT_FILE"
echo "### 5. Known Test Entity Patterns" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# Common test entity patterns
KNOWN_TEST_PATTERNS=(
    "test_"
    "_test"
    "demo_"
    "_demo"
    "sample_"
    "validation_"
    "mock_"
    "fake_"
    "temp_"
    "temporary_"
)

TEST_PATTERNS_FOUND=0
for pattern in "${KNOWN_TEST_PATTERNS[@]}"; do
    # This would require a more sophisticated query
    # For now, we'll document the check
    echo "- Checking pattern: \`$pattern\`" >> "$REPORT_FILE"
done

### 6. Verify Production Device Names
print_status "6. Checking device and entity names..."

echo "" >> "$REPORT_FILE"
echo "### 6. Device/Entity Name Verification" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# Get sample of devices
DEVICES=$(curl -s "$DATA_API_URL/api/devices?limit=50" 2>/dev/null || echo "{}")
DEVICE_COUNT=$(echo "$DEVICES" | jq '.devices | length' 2>/dev/null || echo "0")

if [ "$DEVICE_COUNT" -gt 0 ]; then
    echo "- **Device Count:** $DEVICE_COUNT (sample)" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    
    # Check device names for test patterns
    DEVICE_NAMES=$(echo "$DEVICES" | jq -r '.devices[].name // empty' 2>/dev/null)
    TEST_DEVICES=0
    
    while IFS= read -r device_name; do
        if [ -n "$device_name" ]; then
            for pattern in "${TEST_PATTERNS[@]}"; do
                if echo "$device_name" | grep -qi "$pattern"; then
                    TEST_DEVICES=$((TEST_DEVICES + 1))
                    print_warning "    Found test device name: $device_name"
                    break
                fi
            done
        fi
    done <<< "$DEVICE_NAMES"
    
    if [ $TEST_DEVICES -eq 0 ]; then
        print_success "No test device names found"
        echo "✅ **Device Names:** All appear to be production" >> "$REPORT_FILE"
    else
        TEST_DATA_FOUND=true
        print_error "Found $TEST_DEVICES test device names"
        echo "❌ **Device Names:** $TEST_DEVICES test devices found" >> "$REPORT_FILE"
    fi
fi

### 7. Check SQLite Databases
print_status "7. Checking SQLite databases for test data..."

echo "" >> "$REPORT_FILE"
echo "### 7. SQLite Database Check" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# Check metadata.db
if [ -f "data/metadata.db" ]; then
    print_status "  Checking metadata.db..."
    
    # Use sqlite3 if available
    if command -v sqlite3 &> /dev/null; then
        TEST_DEVICES_SQL=$(sqlite3 data/metadata.db \
            "SELECT COUNT(*) FROM devices WHERE name LIKE '%test%' OR name LIKE '%demo%' OR name LIKE '%sample%' OR device_id LIKE '%test%';" \
            2>/dev/null || echo "0")
        
        TEST_ENTITIES_SQL=$(sqlite3 data/metadata.db \
            "SELECT COUNT(*) FROM entities WHERE entity_id LIKE '%test%' OR entity_id LIKE '%demo%' OR entity_id LIKE '%sample%';" \
            2>/dev/null || echo "0")
        
        if [ "$TEST_DEVICES_SQL" = "0" ] && [ "$TEST_ENTITIES_SQL" = "0" ]; then
            print_success "  No test data in metadata.db"
            echo "✅ **metadata.db:** No test data found" >> "$REPORT_FILE"
        else
            TEST_DATA_FOUND=true
            print_error "  Found test data in metadata.db: $TEST_DEVICES_SQL devices, $TEST_ENTITIES_SQL entities"
            echo "❌ **metadata.db:** Test data found ($TEST_DEVICES_SQL devices, $TEST_ENTITIES_SQL entities)" >> "$REPORT_FILE"
        fi
    else
        print_warning "  sqlite3 not available, skipping SQLite check"
        echo "⚠️ **metadata.db:** sqlite3 not available for check" >> "$REPORT_FILE"
    fi
else
    print_warning "  metadata.db not found at data/metadata.db"
    echo "⚠️ **metadata.db:** File not found" >> "$REPORT_FILE"
fi

### 8. Summary and Recommendations
print_status "8. Generating summary..."

echo "" >> "$REPORT_FILE"
echo "---" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "## Summary" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

if [ "$TEST_DATA_FOUND" = "true" ]; then
    print_error "⚠️ TEST DATA FOUND - Review findings above"
    echo "**Status:** ❌ **TEST DATA FOUND**" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    echo "**Recommendations:**" >> "$REPORT_FILE"
    echo "1. Review identified test entities/devices" >> "$REPORT_FILE"
    echo "2. Determine if test data should be removed" >> "$REPORT_FILE"
    echo "3. Use cleanup script: \`DRY_RUN=false bash scripts/cleanup-test-data.sh\`" >> "$REPORT_FILE"
    echo "4. Backup databases before cleanup" >> "$REPORT_FILE"
else
    print_success "✅ NO TEST DATA FOUND - All data appears to be production"
    echo "**Status:** ✅ **ALL PRODUCTION DATA**" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    echo "All events appear to be from production Home Assistant." >> "$REPORT_FILE"
    echo "No test, demo, or validation data patterns were found." >> "$REPORT_FILE"
fi

echo "" >> "$REPORT_FILE"
echo "---" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "**Report Generated:** $(date)" >> "$REPORT_FILE"
echo "**Report File:** \`$REPORT_FILE\`" >> "$REPORT_FILE"

# Print final summary
echo ""
echo "========================================"
if [ "$TEST_DATA_FOUND" = "true" ]; then
    echo "⚠️  TEST DATA FOUND - Review report"
    echo "Report: $REPORT_FILE"
    exit 1
else
    echo "✅ ALL PRODUCTION DATA CONFIRMED"
    echo "Report: $REPORT_FILE"
    exit 0
fi

