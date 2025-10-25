#!/bin/bash
# Setup InfluxDB Buckets for Epic AI-5 Pattern Aggregates
# Story AI5.1: Multi-Layer Storage Design & Schema

set -e

# Configuration
INFLUXDB_URL="${INFLUXDB_URL:-http://localhost:8086}"
INFLUXDB_TOKEN="${INFLUXDB_TOKEN:-homeiq-token}"
INFLUXDB_ORG="${INFLUXDB_ORG:-homeiq}"

echo "=========================================="
echo "Epic AI-5: InfluxDB Bucket Setup"
echo "=========================================="
echo "InfluxDB URL: $INFLUXDB_URL"
echo "Organization: $INFLUXDB_ORG"
echo ""

# Function to create bucket
create_bucket() {
    local bucket_name=$1
    local retention_days=$2
    local description=$3
    
    echo "Creating bucket: $bucket_name"
    echo "  Description: $description"
    echo "  Retention: $retention_days days"
    
    curl -X POST \
        "$INFLUXDB_URL/api/v2/buckets" \
        -H "Authorization: Token $INFLUXDB_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{
            \"orgID\": \"$(influx org find -n $INFLUXDB_ORG --json | jq -r '.[0].id')\",
            \"name\": \"$bucket_name\",
            \"description\": \"$description\",
            \"retentionRules\": [{
                \"type\": \"expire\",
                \"everySeconds\": $(($retention_days * 24 * 60 * 60))
            }]
        }" || echo "  ⚠️  Bucket may already exist or creation failed"
    
    echo ""
}

# Create buckets for Epic AI-5
echo "Creating Layer 2: Daily Aggregates..."
create_bucket \
    "pattern_aggregates_daily" \
    90 \
    "Daily pattern aggregates for 10 detector types (Epic AI-5)"

echo "Creating Layer 3: Weekly/Monthly Aggregates..."
create_bucket \
    "pattern_aggregates_weekly" \
    365 \
    "Weekly and monthly pattern aggregates for long-term analysis (Epic AI-5)"

echo "=========================================="
echo "✅ InfluxDB bucket setup complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Verify buckets exist in InfluxDB UI"
echo "2. Run integration tests"
echo "3. Begin Story AI5.3: Convert detectors to incremental processing"
