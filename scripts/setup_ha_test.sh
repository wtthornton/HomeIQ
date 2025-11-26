#!/bin/bash
# Setup script for Home Assistant test container
# Creates initial configuration and long-lived access token

set -e

echo "Setting up Home Assistant test container..."

# Wait for HA to be ready
echo "Waiting for Home Assistant to be ready..."
timeout=300
elapsed=0
while [ $elapsed -lt $timeout ]; do
    if curl -f -s http://localhost:8124/api/ > /dev/null 2>&1; then
        echo "✅ Home Assistant is ready!"
        break
    fi
    echo "  Waiting... ($elapsed/$timeout seconds)"
    sleep 5
    elapsed=$((elapsed + 5))
done

if [ $elapsed -ge $timeout ]; then
    echo "❌ Timeout waiting for Home Assistant"
    exit 1
fi

# Check if token already exists
if [ -f .env.test ] && grep -q "HA_TEST_TOKEN" .env.test; then
    echo "✅ Test token already exists in .env.test"
    exit 0
fi

# Create long-lived access token
echo "Creating long-lived access token..."
TOKEN=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -d '{"name": "HomeIQ Test Token", "client_name": "HomeIQ Test", "type": "long_lived_access_token", "lifespan": 3650}' \
    http://localhost:8124/auth/providers/homeassistant/login \
    2>/dev/null | jq -r '.access_token' || echo "")

if [ -z "$TOKEN" ] || [ "$TOKEN" == "null" ]; then
    echo "⚠️  Could not create token automatically. Please create one manually:"
    echo "   1. Open http://localhost:8124"
    echo "   2. Go to Profile → Long-Lived Access Tokens"
    echo "   3. Create token named 'HomeIQ Test Token'"
    echo "   4. Add to .env.test: HA_TEST_TOKEN=your_token_here"
    exit 1
fi

# Create .env.test file
cat > .env.test <<EOF
# Home Assistant Test Configuration
HA_TEST_URL=http://localhost:8124
HA_TEST_TOKEN=${TOKEN}
HA_TEST_WS_URL=ws://localhost:8124/api/websocket
INFLUXDB_TEST_BUCKET=home_assistant_events_test
EOF

echo "✅ Test token created and saved to .env.test"
echo "   Token: ${TOKEN:0:20}..."
echo ""
echo "Next steps:"
echo "  1. Review .env.test file"
echo "  2. Load test dataset: python scripts/load_dataset_to_ha.py --dataset assist-mini"
echo "  3. Run tests: pytest tests/datasets/ -v"

