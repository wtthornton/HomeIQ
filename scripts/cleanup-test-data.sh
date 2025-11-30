#!/bin/bash

# Phase 4: Data Cleanup
# Identifies and removes test/bad data from databases

set -e

# Configuration
INFLUXDB_URL="${INFLUXDB_URL:-http://localhost:8086}"
INFLUXDB_ORG="${INFLUXDB_ORG:-homeiq}"
INFLUXDB_BUCKET="${INFLUXDB_BUCKET:-home_assistant_events}"
INFLUXDB_TOKEN="${INFLUXDB_TOKEN:-homeiq-token}"
DRY_RUN="${DRY_RUN:-true}"
REPORT_DIR="${REPORT_DIR:-implementation/verification}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Create report directory
mkdir -p "$REPORT_DIR"
REPORT_FILE="$REPORT_DIR/data-cleanup-$(date +%Y%m%d-%H%M%S).md"

# Validation results
CLEANUP_ITEMS=0
ITEMS_DELETED=0

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
# Data Cleanup Report
Generated: $(date)
Dry Run: $DRY_RUN

## Phase 4: Data Cleanup

This report documents the identification and cleanup of test/bad data.

**⚠️ WARNING:** This script modifies data. Always run with DRY_RUN=true first to review what will be deleted.

EOF

print_status "Starting Phase 4: Data Cleanup..."
print_warning "Dry run mode: $DRY_RUN (set DRY_RUN=false to actually delete)"

if [ "$DRY_RUN" = "true" ]; then
    print_warning "DRY RUN MODE - No data will be deleted"
    echo "**Mode:** DRY RUN (no deletions will be performed)" >> "$REPORT_FILE"
else
    print_warning "LIVE MODE - Data will be deleted!"
    echo "**Mode:** LIVE (deletions will be performed)" >> "$REPORT_FILE"
    read -p "Are you sure you want to proceed? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        print_error "Aborted by user"
        exit 1
    fi
fi

### 4.1 Identify Test/Bad Data
print_status "4.1 Identifying test/bad data..."

echo "" >> "$REPORT_FILE"
echo "### 4.1 Test/Bad Data Identification" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# Test patterns to search for
TEST_PATTERNS=("test" "demo" "validation" "sample" "mock" "fake")

echo "**Search Patterns:**" >> "$REPORT_FILE"
for pattern in "${TEST_PATTERNS[@]}"; do
    echo "- $pattern" >> "$REPORT_FILE"
done
echo "" >> "$REPORT_FILE"

# Identify test data in InfluxDB
print_status "Searching InfluxDB for test data..."

# Note: This requires influx CLI or API access
# For now, document the approach
echo "### InfluxDB Test Data" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "To identify test data in InfluxDB, use the following queries:" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "\`\`\`bash" >> "$REPORT_FILE"
echo "# Find entities with test patterns" >> "$REPORT_FILE"
echo "influx query --org $INFLUXDB_ORG --token $INFLUXDB_TOKEN \\" >> "$REPORT_FILE"
echo "  \"from(bucket: \\\"$INFLUXDB_BUCKET\\\") \\" >> "$REPORT_FILE"
echo "    |> range(start: -30d) \\" >> "$REPORT_FILE"
echo "    |> filter(fn: (r) => r.entity_id =~ /test|demo|validation|sample|mock/) \\" >> "$REPORT_FILE"
echo "    |> count()\"" >> "$REPORT_FILE"
echo "\`\`\`" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

print_warning "InfluxDB cleanup requires manual review (see commands above)"

# Identify test data in SQLite
print_status "Searching SQLite databases for test data..."

echo "### SQLite Test Data" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# Check metadata.db for test devices/entities
if docker exec homeiq-data-api sqlite3 /app/data/metadata.db ".tables" > /dev/null 2>&1; then
    print_status "Checking metadata.db for test data..."
    
    for pattern in "${TEST_PATTERNS[@]}"; do
        COUNT=$(docker exec homeiq-data-api sqlite3 /app/data/metadata.db \
            "SELECT COUNT(*) FROM entities WHERE entity_id LIKE '%$pattern%';" 2>/dev/null || echo "0")
        
        if [ "$COUNT" -gt 0 ]; then
            CLEANUP_ITEMS=$((CLEANUP_ITEMS + COUNT))
            print_warning "Found $COUNT entities with pattern '$pattern' in metadata.db"
            echo "- **Pattern '$pattern':** $COUNT entities found" >> "$REPORT_FILE"
            
            # Show examples
            EXAMPLES=$(docker exec homeiq-data-api sqlite3 /app/data/metadata.db \
                "SELECT entity_id FROM entities WHERE entity_id LIKE '%$pattern%' LIMIT 5;" 2>/dev/null || echo "")
            if [ -n "$EXAMPLES" ]; then
                echo "  - Examples: $EXAMPLES" >> "$REPORT_FILE"
            fi
        fi
    done
fi

### 4.2 InfluxDB Data Cleanup
print_status "4.2 InfluxDB Data Cleanup..."

echo "" >> "$REPORT_FILE"
echo "### 4.2 InfluxDB Data Cleanup" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

if [ "$DRY_RUN" = "false" ]; then
    print_warning "InfluxDB cleanup commands (REQUIRES MANUAL EXECUTION):"
    echo "**Cleanup Commands:**" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    echo "⚠️ **Manual Step Required:** Execute the following commands to delete test data:" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    echo "\`\`\`bash" >> "$REPORT_FILE"
    echo "# Delete test entities (REVIEW BEFORE RUNNING)" >> "$REPORT_FILE"
    echo "influx delete --bucket $INFLUXDB_BUCKET \\" >> "$REPORT_FILE"
    echo "  --org $INFLUXDB_ORG \\" >> "$REPORT_FILE"
    echo "  --token $INFLUXDB_TOKEN \\" >> "$REPORT_FILE"
    echo "  --start 2024-01-01T00:00:00Z \\" >> "$REPORT_FILE"
    echo "  --stop $(date -u +%Y-%m-%dT%H:%M:%SZ) \\" >> "$REPORT_FILE"
    echo "  --predicate 'entity_id=~ /test|demo|validation|sample|mock/'" >> "$REPORT_FILE"
    echo "\`\`\`" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    print_warning "InfluxDB cleanup requires manual execution with proper review"
else
    print_status "DRY RUN: Would execute InfluxDB cleanup commands (see report)"
    echo "**Status:** DRY RUN - Commands documented but not executed" >> "$REPORT_FILE"
fi

### 4.3 SQLite Data Cleanup
print_status "4.3 SQLite Data Cleanup..."

echo "" >> "$REPORT_FILE"
echo "### 4.3 SQLite Data Cleanup" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

if [ "$DRY_RUN" = "false" ] && [ "$CLEANUP_ITEMS" -gt 0 ]; then
    print_status "Cleaning up SQLite test data..."
    
    # Backup first
    print_status "Creating backup of metadata.db..."
    BACKUP_FILE="$REPORT_DIR/metadata-backup-$(date +%Y%m%d-%H%M%S).db"
    docker exec homeiq-data-api sqlite3 /app/data/metadata.db ".backup /tmp/backup.db" 2>/dev/null || true
    docker cp homeiq-data-api:/tmp/backup.db "$BACKUP_FILE" 2>/dev/null || true
    
    if [ -f "$BACKUP_FILE" ]; then
        print_success "Backup created: $BACKUP_FILE"
        echo "✅ **Backup Created:** $BACKUP_FILE" >> "$REPORT_FILE"
    else
        print_warning "Could not create backup"
        echo "⚠️ **Backup:** Failed" >> "$REPORT_FILE"
    fi
    
    # Delete test data
    for pattern in "${TEST_PATTERNS[@]}"; do
        COUNT=$(docker exec homeiq-data-api sqlite3 /app/data/metadata.db \
            "SELECT COUNT(*) FROM entities WHERE entity_id LIKE '%$pattern%';" 2>/dev/null || echo "0")
        
        if [ "$COUNT" -gt 0 ]; then
            print_status "Deleting $COUNT entities with pattern '$pattern'..."
            docker exec homeiq-data-api sqlite3 /app/data/metadata.db \
                "DELETE FROM entities WHERE entity_id LIKE '%$pattern%';" 2>/dev/null
            
            if [ $? -eq 0 ]; then
                ITEMS_DELETED=$((ITEMS_DELETED + COUNT))
                print_success "Deleted $COUNT entities with pattern '$pattern'"
                echo "✅ **Deleted:** $COUNT entities (pattern: $pattern)" >> "$REPORT_FILE"
            else
                print_error "Failed to delete entities with pattern '$pattern'"
                echo "❌ **Failed:** Could not delete entities (pattern: $pattern)" >> "$REPORT_FILE"
            fi
        fi
    done
else
    print_status "DRY RUN: Would delete $CLEANUP_ITEMS items from SQLite"
    echo "**Status:** DRY RUN - $CLEANUP_ITEMS items identified for deletion" >> "$REPORT_FILE"
fi

### 4.4 Verification After Cleanup
print_status "4.4 Verifying cleanup didn't break anything..."

echo "" >> "$REPORT_FILE"
echo "### 4.4 Post-Cleanup Verification" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

if [ "$DRY_RUN" = "false" ] && [ "$ITEMS_DELETED" -gt 0 ]; then
    # Check service health
    if curl -s -f "http://localhost:8003/health" > /dev/null 2>&1; then
        print_success "Services still healthy after cleanup"
        echo "✅ **Service Health:** All services healthy" >> "$REPORT_FILE"
    else
        print_error "Some services unhealthy after cleanup"
        echo "❌ **Service Health:** Issues detected" >> "$REPORT_FILE"
    fi
    
    # Check recent data still flowing
    if curl -s -f "http://localhost:8006/api/v1/events?limit=1" > /dev/null 2>&1; then
        print_success "Recent data still accessible"
        echo "✅ **Data Access:** Working" >> "$REPORT_FILE"
    else
        print_error "Data access issues after cleanup"
        echo "❌ **Data Access:** Failed" >> "$REPORT_FILE"
    fi
else
    print_status "DRY RUN: Verification skipped"
    echo "**Status:** DRY RUN - Verification not performed" >> "$REPORT_FILE"
fi

# Summary
echo "" >> "$REPORT_FILE"
echo "## Summary" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "- **Items Identified:** $CLEANUP_ITEMS" >> "$REPORT_FILE"
echo "- **Items Deleted:** $ITEMS_DELETED" >> "$REPORT_FILE"
echo "- **Dry Run:** $DRY_RUN" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

if [ "$DRY_RUN" = "true" ]; then
    echo "**Status:** ✅ Dry run complete - Review report before executing cleanup" >> "$REPORT_FILE"
    print_success "Dry run complete - Review report: $REPORT_FILE"
else
    echo "**Status:** ✅ Cleanup complete" >> "$REPORT_FILE"
    print_success "Cleanup complete"
fi

exit 0

