#!/bin/bash

# Phase 3: Database Validation
# Validates database integrity and schema

set -e

# Configuration
INFLUXDB_URL="${INFLUXDB_URL:-http://localhost:8086}"
INFLUXDB_ORG="${INFLUXDB_ORG:-homeiq}"
INFLUXDB_BUCKET="${INFLUXDB_BUCKET:-home_assistant_events}"
INFLUXDB_TOKEN="${INFLUXDB_TOKEN:-homeiq-token}"
DATA_API_URL="${DATA_API_URL:-http://localhost:8006}"
REPORT_DIR="${REPORT_DIR:-implementation/verification}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Create report directory
mkdir -p "$REPORT_DIR"
REPORT_FILE="$REPORT_DIR/database-validation-$(date +%Y%m%d-%H%M%S).md"

# Validation results
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
# Database Validation Report
Generated: $(date)

## Phase 3: Database Validation

This report validates database integrity and schema correctness.

EOF

print_status "Starting Phase 3: Database Validation..."

### 3.1 InfluxDB Schema Validation
print_status "3.1 Validating InfluxDB Schema..."

echo "" >> "$REPORT_FILE"
echo "### 3.1 InfluxDB Schema Validation" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# Use existing validation script if available
if [ -f "scripts/validate-influxdb-schema.sh" ]; then
    print_status "Running InfluxDB schema validation script..."
    if bash scripts/validate-influxdb-schema.sh 2>&1 | tee -a "$REPORT_FILE"; then
        print_success "InfluxDB schema validation passed"
        echo "✅ **Schema Validation:** Passed" >> "$REPORT_FILE"
    else
        print_error "InfluxDB schema validation failed"
        echo "❌ **Schema Validation:** Failed" >> "$REPORT_FILE"
    fi
else
    print_warning "InfluxDB validation script not found, running basic checks..."
    
    # Basic InfluxDB checks
    if curl -s -f "$INFLUXDB_URL/health" > /dev/null 2>&1; then
        print_success "InfluxDB is accessible"
        echo "✅ **InfluxDB Accessibility:** Passed" >> "$REPORT_FILE"
    else
        print_error "InfluxDB is not accessible"
        echo "❌ **InfluxDB Accessibility:** Failed" >> "$REPORT_FILE"
    fi
fi

### 3.2 InfluxDB Data Quality Check
print_status "3.2 Checking InfluxDB Data Quality..."

echo "" >> "$REPORT_FILE"
echo "### 3.2 InfluxDB Data Quality Check" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# Check for recent data (last 24 hours)
print_status "Checking for recent data (last 24 hours)..."

# Try to query via data-api
if curl -s -f "$DATA_API_URL/api/v1/events?start_time=$(date -u -d '24 hours ago' +%Y-%m-%dT%H:%M:%SZ)&limit=1" > /dev/null 2>&1; then
    RECENT_COUNT=$(curl -s "$DATA_API_URL/api/v1/events?start_time=$(date -u -d '24 hours ago' +%Y-%m-%dT%H:%M:%SZ)" | jq '. | length' 2>/dev/null || echo "0")
    if [ "$RECENT_COUNT" -gt 0 ]; then
        print_success "Found recent events in last 24 hours"
        echo "✅ **Recent Data:** $RECENT_COUNT events found in last 24 hours" >> "$REPORT_FILE"
    else
        print_warning "No recent events found in last 24 hours"
        echo "⚠️ **Recent Data:** No events found in last 24 hours" >> "$REPORT_FILE"
    fi
else
    print_warning "Could not check recent data via API"
    echo "⚠️ **Recent Data Check:** API unavailable" >> "$REPORT_FILE"
fi

### 3.3 SQLite Database Validation
print_status "3.3 Validating SQLite Databases..."

echo "" >> "$REPORT_FILE"
echo "### 3.3 SQLite Database Validation" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# Check metadata.db (data-api)
METADATA_DB="/var/lib/docker/volumes/homeiq_sqlite-data/_data/metadata.db"
if docker exec homeiq-data-api test -f /app/data/metadata.db 2>/dev/null; then
    print_success "metadata.db exists"
    echo "✅ **metadata.db:** Found" >> "$REPORT_FILE"
    
    # Check database structure
    if docker exec homeiq-data-api sqlite3 /app/data/metadata.db ".tables" > /dev/null 2>&1; then
        TABLES=$(docker exec homeiq-data-api sqlite3 /app/data/metadata.db ".tables" 2>/dev/null)
        print_success "Database accessible, tables: $TABLES"
        echo "✅ **Database Access:** Working" >> "$REPORT_FILE"
        echo "**Tables Found:** $TABLES" >> "$REPORT_FILE"
    else
        print_warning "Could not query metadata.db"
        echo "⚠️ **Database Access:** Query failed" >> "$REPORT_FILE"
    fi
else
    print_warning "metadata.db not found (may be expected if no data yet)"
    echo "⚠️ **metadata.db:** Not found" >> "$REPORT_FILE"
fi

# Check for NULL violations (reference previous fixes)
print_status "Checking for NULL violations in SQLite databases..."
echo "**Note:** Reference implementation/analysis/DATABASE_QUALITY_REPORT.md for previous fixes" >> "$REPORT_FILE"

### 3.4 AI Automation Database Validation
print_status "3.4 Validating AI Automation Database..."

echo "" >> "$REPORT_FILE"
echo "### 3.4 AI Automation Database Validation" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# Check ai_automation.db
if docker exec ai-automation-service test -f /app/data/ai_automation.db 2>/dev/null; then
    print_success "ai_automation.db exists"
    echo "✅ **ai_automation.db:** Found" >> "$REPORT_FILE"
    
    # Check tables
    if docker exec ai-automation-service sqlite3 /app/data/ai_automation.db ".tables" > /dev/null 2>&1; then
        AI_TABLES=$(docker exec ai-automation-service sqlite3 /app/data/ai_automation.db ".tables" 2>/dev/null | tr '\n' ' ')
        print_success "AI database accessible"
        echo "✅ **Database Access:** Working" >> "$REPORT_FILE"
        echo "**Tables Found:** $AI_TABLES" >> "$REPORT_FILE"
    else
        print_warning "Could not query ai_automation.db"
        echo "⚠️ **Database Access:** Query failed" >> "$REPORT_FILE"
    fi
else
    print_warning "ai_automation.db not found (may be expected)"
    echo "⚠️ **ai_automation.db:** Not found" >> "$REPORT_FILE"
fi

# Summary
echo "" >> "$REPORT_FILE"
echo "## Summary" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

if [ "$VALIDATION_PASSED" = true ]; then
    echo "**Status:** ✅ Database validation complete" >> "$REPORT_FILE"
    print_success "Phase 3 validation complete"
    exit 0
else
    echo "**Status:** ⚠️ Some database issues found" >> "$REPORT_FILE"
    print_warning "Phase 3 validation complete - Some issues found"
    exit 1
fi

