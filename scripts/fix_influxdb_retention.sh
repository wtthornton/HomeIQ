#!/bin/bash
# Fix InfluxDB retention policies
# Sets retention policies for buckets to prevent unbounded growth

set -e

INFLUXDB_URL="${INFLUXDB_URL:-http://localhost:8086}"
INFLUXDB_TOKEN="${INFLUXDB_TOKEN:-homeiq-token}"
INFLUXDB_ORG="${INFLUXDB_ORG:-homeiq}"

echo "=================================================================================="
echo "FIXING INFLUXDB RETENTION POLICIES"
echo "=================================================================================="
echo ""
echo "URL: $INFLUXDB_URL"
echo "Org: $INFLUXDB_ORG"
echo ""

# Check if influx CLI is available
if ! command -v influx &> /dev/null; then
    echo "❌ ERROR: influx CLI not found"
    echo "   Install InfluxDB CLI or use Python script instead"
    exit 1
fi

# Update home_assistant_events bucket retention to 90 days
echo "Step 1: Setting retention for home_assistant_events bucket"
echo "-------------------------------------------------------------------"
if influx bucket list --host "$INFLUXDB_URL" --token "$INFLUXDB_TOKEN" --org "$INFLUXDB_ORG" | grep -q "home_assistant_events"; then
    echo "  Found home_assistant_events bucket"
    influx bucket update \
        --name home_assistant_events \
        --retention 90d \
        --host "$INFLUXDB_URL" \
        --token "$INFLUXDB_TOKEN" \
        --org "$INFLUXDB_ORG"
    echo "  ✅ Set retention to 90 days"
else
    echo "  ⚠️  home_assistant_events bucket not found"
fi
echo ""

# Update weather_data bucket retention to 365 days
echo "Step 2: Setting retention for weather_data bucket"
echo "-------------------------------------------------------------------"
if influx bucket list --host "$INFLUXDB_URL" --token "$INFLUXDB_TOKEN" --org "$INFLUXDB_ORG" | grep -q "weather_data"; then
    echo "  Found weather_data bucket"
    influx bucket update \
        --name weather_data \
        --retention 365d \
        --host "$INFLUXDB_URL" \
        --token "$INFLUXDB_TOKEN" \
        --org "$INFLUXDB_ORG"
    echo "  ✅ Set retention to 365 days"
else
    echo "  ⚠️  weather_data bucket not found"
fi
echo ""

# Verify changes
echo "Step 3: Verifying retention policies"
echo "-------------------------------------------------------------------"
influx bucket list --host "$INFLUXDB_URL" --token "$INFLUXDB_TOKEN" --org "$INFLUXDB_ORG" | grep -E "(name|retention)" || true
echo ""

echo "=================================================================================="
echo "COMPLETE"
echo "=================================================================================="

