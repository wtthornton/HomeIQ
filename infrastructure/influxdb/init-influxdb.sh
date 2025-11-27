#!/bin/bash

# InfluxDB Initialization Script
# This script sets up the initial InfluxDB configuration

set -e

echo "Initializing InfluxDB..."

# Wait for InfluxDB to be ready
echo "Waiting for InfluxDB to be ready..."
until curl -f http://localhost:8086/health; do
  echo "InfluxDB is not ready yet. Waiting..."
  sleep 5
done

echo "InfluxDB is ready!"

# Create organization and bucket if they don't exist
echo "Setting up organization and bucket..."

# Use influx CLI to create organization and bucket
influx org create \
  --name "${INFLUXDB_ORG:-homeiq}" \
  --description "Home Assistant Data Ingestion Organization" \
  --token "${INFLUXDB_TOKEN:-homeiq-token}" \
  --host http://localhost:8086

influx bucket create \
  --name "${INFLUXDB_BUCKET:-home_assistant_events}" \
  --org "${INFLUXDB_ORG:-homeiq}" \
  --retention 30d \
  --token "${INFLUXDB_TOKEN:-homeiq-token}" \
  --host http://localhost:8086

# Create test organization and bucket if DEPLOYMENT_MODE is test or if test bucket doesn't exist
if [ "${DEPLOYMENT_MODE:-production}" = "test" ] || [ -n "${CREATE_TEST_BUCKET:-}" ]; then
  echo "Setting up test organization and bucket..."
  
  influx org create \
    --name "homeiq-test" \
    --description "Home Assistant Test Data Organization" \
    --token "homeiq-test-token" \
    --host http://localhost:8086 || echo "Test org may already exist"
  
  influx bucket create \
    --name "home_assistant_events_test" \
    --org "homeiq-test" \
    --retention 7d \
    --token "homeiq-test-token" \
    --host http://localhost:8086 || echo "Test bucket may already exist"
  
  echo "Test bucket initialization complete!"
fi

echo "InfluxDB initialization complete!"
