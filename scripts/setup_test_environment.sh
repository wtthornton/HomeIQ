#!/bin/bash
# Epic 40: Test Environment Setup Script
# Creates test database directory and initializes InfluxDB test bucket

set -e

echo "=========================================="
echo "Epic 40: Test Environment Setup"
echo "=========================================="

# Create test data directory
echo "Creating test data directory..."
mkdir -p data/test
chmod 755 data/test

# Create test metadata.db if it doesn't exist
if [ ! -f "data/test/metadata.db" ]; then
  echo "Test database will be created on first service startup"
  touch data/test/metadata.db
  chmod 644 data/test/metadata.db
fi

echo "✅ Test data directory created: data/test/"

# Initialize InfluxDB test bucket (if InfluxDB is running)
echo ""
echo "Initializing InfluxDB test bucket..."
echo "Note: This requires InfluxDB to be running"

if command -v curl >/dev/null 2>&1; then
  # Check if InfluxDB is accessible
  if curl -f http://localhost:8086/health >/dev/null 2>&1; then
    echo "InfluxDB is accessible. Creating test bucket..."
    
    # Create test organization (if it doesn't exist)
    influx org create \
      --name "homeiq-test" \
      --description "Home Assistant Test Data Organization" \
      --token "homeiq-test-token" \
      --host http://localhost:8086 2>/dev/null || echo "Test org may already exist"
    
    # Create test bucket (if it doesn't exist)
    influx bucket create \
      --name "home_assistant_events_test" \
      --org "homeiq-test" \
      --retention 7d \
      --token "homeiq-test-token" \
      --host http://localhost:8086 2>/dev/null || echo "Test bucket may already exist"
    
    echo "✅ InfluxDB test bucket initialized"
  else
    echo "⚠️  InfluxDB is not accessible. Test bucket will be created on first service startup."
    echo "   Make sure InfluxDB is running before starting test services."
  fi
else
  echo "⚠️  curl not found. Test bucket will be created on first service startup."
fi

echo ""
echo "=========================================="
echo "Test Environment Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Copy infrastructure/env.test to .env"
echo "2. Update .env with your test configuration"
echo "3. Start test deployment: docker-compose --profile test up -d"
echo ""

