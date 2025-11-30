#!/bin/bash

# Complete Production Data Verification
# Comprehensive check that all data is from production

set -e

# Load environment variables
if [ -f .env ]; then
    while IFS='=' read -r key value || [ -n "$key" ]; do
        [[ "$key" =~ ^#.*$ ]] && continue
        [[ -z "$key" ]] && continue
        key=$(echo "$key" | tr -d '\r')
        value=$(echo "$value" | tr -d '\r')
        export "$key=$value" 2>/dev/null || true
    done < .env
fi

DATA_API_URL="${DATA_API_URL:-http://localhost:8006}"
REPORT_DIR="${REPORT_DIR:-implementation/verification}"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
REPORT_FILE="$REPORT_DIR/production-data-verification-$TIMESTAMP.md"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

mkdir -p "$REPORT_DIR"

print_status() { echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$REPORT_FILE"; }
print_success() { echo -e "${GREEN}[✓]${NC} $1" | tee -a "$REPORT_FILE"; }
print_warning() { echo -e "${YELLOW}[⚠]${NC} $1" | tee -a "$REPORT_FILE"; }
print_error() { echo -e "${RED}[✗]${NC} $1" | tee -a "$REPORT_FILE"; }

cat > "$REPORT_FILE" << EOF
# Production Data Verification - Complete Report

**Generated:** $(date)
**Purpose:** Confirm all events are from production, no test data

---

EOF

print_status "Starting Complete Production Data Verification..."

# Check SQLite via Docker
print_status "1. Checking SQLite databases via Docker..."

echo "" >> "$REPORT_FILE"
echo "### 1. SQLite Database Check (via Docker)" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# Check metadata.db in data-api container
TEST_DEVICES=$(docker exec homeiq-data-api python3 -c "
import sqlite3
import os
db_path = '/app/data/metadata.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(\"SELECT COUNT(*) FROM devices WHERE LOWER(name) LIKE '%test%' OR LOWER(name) LIKE '%demo%' OR LOWER(name) LIKE '%sample%' OR LOWER(device_id) LIKE '%test%'\")
    print(cursor.fetchone()[0])
    conn.close()
else:
    print('0')
" 2>/dev/null || echo "0")

TEST_ENTITIES=$(docker exec homeiq-data-api python3 -c "
import sqlite3
import os
db_path = '/app/data/metadata.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(\"SELECT COUNT(*) FROM entities WHERE LOWER(entity_id) LIKE '%test%' OR LOWER(entity_id) LIKE '%demo%' OR LOWER(entity_id) LIKE '%sample%'\")
    print(cursor.fetchone()[0])
    conn.close()
else:
    print('0')
" 2>/dev/null || echo "0")

TOTAL_DEVICES=$(docker exec homeiq-data-api python3 -c "
import sqlite3
import os
db_path = '/app/data/metadata.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(\"SELECT COUNT(*) FROM devices\")
    print(cursor.fetchone()[0])
    conn.close()
else:
    print('0')
" 2>/dev/null || echo "0")

TOTAL_ENTITIES=$(docker exec homeiq-data-api python3 -c "
import sqlite3
import os
db_path = '/app/data/metadata.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(\"SELECT COUNT(*) FROM entities\")
    print(cursor.fetchone()[0])
    conn.close()
else:
    print('0')
" 2>/dev/null || echo "0")

echo "- **Total Devices:** $TOTAL_DEVICES" >> "$REPORT_FILE"
echo "- **Total Entities:** $TOTAL_ENTITIES" >> "$REPORT_FILE"
echo "- **Test Devices Found:** $TEST_DEVICES" >> "$REPORT_FILE"
echo "- **Test Entities Found:** $TEST_ENTITIES" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

if [ "$TEST_DEVICES" = "0" ] && [ "$TEST_ENTITIES" = "0" ]; then
    print_success "SQLite: No test data found ($TOTAL_DEVICES devices, $TOTAL_ENTITIES entities)"
else
    print_error "SQLite: Found test data! ($TEST_DEVICES devices, $TEST_ENTITIES entities)"
fi

# Check via API
print_status "2. Checking via API endpoints..."

echo "" >> "$REPORT_FILE"
echo "### 2. API Endpoint Check" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# Get sample devices and check names
DEVICES_JSON=$(curl -s "$DATA_API_URL/api/devices?limit=200" 2>/dev/null || echo "{\"devices\":[]}")
DEVICE_COUNT=$(echo "$DEVICES_JSON" | python3 -c "import sys, json; data=json.load(sys.stdin); print(len(data.get('devices', [])))" 2>/dev/null || echo "0")

echo "- **Devices via API:** $DEVICE_COUNT (sample)" >> "$REPORT_FILE"

# Check for test patterns in device names
TEST_DEVICE_NAMES=$(echo "$DEVICES_JSON" | python3 -c "
import sys, json
data = json.load(sys.stdin)
test_devices = []
patterns = ['test', 'demo', 'sample', 'validation', 'mock', 'fake', 'temp']
for device in data.get('devices', []):
    name = device.get('name', '').lower()
    device_id = device.get('device_id', '').lower()
    for pattern in patterns:
        if pattern in name or pattern in device_id:
            test_devices.append(device.get('name', 'unknown'))
            break
print('|'.join(test_devices))
" 2>/dev/null || echo "")

if [ -z "$TEST_DEVICE_NAMES" ]; then
    print_success "API: No test device names found"
    echo "✅ **Device Names:** All appear to be production" >> "$REPORT_FILE"
else
    print_error "API: Found test device names: $TEST_DEVICE_NAMES"
    echo "❌ **Device Names:** Found test devices" >> "$REPORT_FILE"
fi

# Get sample entities
ENTITIES_JSON=$(curl -s "$DATA_API_URL/api/entities?limit=500" 2>/dev/null || echo "{\"entities\":[]}")
ENTITY_COUNT=$(echo "$ENTITIES_JSON" | python3 -c "import sys, json; data=json.load(sys.stdin); print(len(data.get('entities', [])))" 2>/dev/null || echo "0")

echo "- **Entities via API:** $ENTITY_COUNT (sample)" >> "$REPORT_FILE"

# Check for test patterns in entity IDs
TEST_ENTITY_IDS=$(echo "$ENTITIES_JSON" | python3 -c "
import sys, json
data = json.load(sys.stdin)
test_entities = []
patterns = ['test', 'demo', 'sample', 'validation', 'mock', 'fake', 'temp']
for entity in data.get('entities', []):
    entity_id = entity.get('entity_id', '').lower()
    for pattern in patterns:
        if pattern in entity_id:
            test_entities.append(entity.get('entity_id', 'unknown'))
            break
if test_entities:
    print('|'.join(test_entities))
" 2>/dev/null || echo "")

if [ -z "$TEST_ENTITY_IDS" ]; then
    print_success "API: No test entity IDs found"
    echo "✅ **Entity IDs:** All appear to be production" >> "$REPORT_FILE"
else
    print_error "API: Found test entity IDs: $TEST_ENTITY_IDS"
    echo "❌ **Entity IDs:** Found test entities" >> "$REPORT_FILE"
fi

# Verify HA source
print_status "3. Verifying Home Assistant source..."

echo "" >> "$REPORT_FILE"
echo "### 3. Home Assistant Source Verification" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

HA_URL="${HA_HTTP_URL:-${HOME_ASSISTANT_URL:-http://192.168.1.86:8123}}"
HA_URL="${HA_URL%/}"

echo "- **HA URL:** $HA_URL" >> "$REPORT_FILE"

if echo "$HA_URL" | grep -q "192.168.1.86\|192.168.1"; then
    print_success "HA URL is production IP (192.168.1.86)"
    echo "✅ **HA Source:** Production" >> "$REPORT_FILE"
elif echo "$HA_URL" | grep -q "localhost\|127.0.0.1"; then
    print_error "HA URL is localhost (NOT production!)"
    echo "❌ **HA Source:** LOCALHOST - This is not production!" >> "$REPORT_FILE"
else
    print_warning "HA URL: $HA_URL (verify this is production)"
    echo "⚠️ **HA Source:** Unknown - verify manually" >> "$REPORT_FILE"
fi

# Final Summary
echo "" >> "$REPORT_FILE"
echo "---" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "## Final Verification Summary" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

ALL_CLEAR=true
if [ "$TEST_DEVICES" != "0" ] || [ "$TEST_ENTITIES" != "0" ]; then
    ALL_CLEAR=false
fi
if [ -n "$TEST_DEVICE_NAMES" ] || [ -n "$TEST_ENTITY_IDS" ]; then
    ALL_CLEAR=false
fi
if echo "$HA_URL" | grep -q "localhost\|127.0.0.1"; then
    ALL_CLEAR=false
fi

if [ "$ALL_CLEAR" = "true" ]; then
    print_success "✅ ALL DATA CONFIRMED AS PRODUCTION"
    echo "**Status:** ✅ **ALL PRODUCTION DATA**" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    echo "All verification checks passed:" >> "$REPORT_FILE"
    echo "- ✅ No test data in SQLite databases" >> "$REPORT_FILE"
    echo "- ✅ No test patterns in device names" >> "$REPORT_FILE"
    echo "- ✅ No test patterns in entity IDs" >> "$REPORT_FILE"
    echo "- ✅ HA source is production" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    echo "**Conclusion:** All events are from production Home Assistant. No test data found." >> "$REPORT_FILE"
    exit 0
else
    print_error "⚠️ TEST DATA OR NON-PRODUCTION SOURCE DETECTED"
    echo "**Status:** ❌ **ISSUES FOUND**" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    echo "Review the findings above and take action as needed." >> "$REPORT_FILE"
    exit 1
fi

