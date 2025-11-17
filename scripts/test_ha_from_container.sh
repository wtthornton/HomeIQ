#!/bin/bash
# Test HA connection from within Docker container

echo "Testing HA connection from container..."
echo "HA_URL: $HA_URL"
echo "HA_TOKEN: ${HA_TOKEN:0:20}..."

# Test network connectivity
echo ""
echo "[1] Testing network connectivity..."
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" "$HA_URL/api/" || echo "Network unreachable"

# Test with authentication
echo ""
echo "[2] Testing /api/config with authentication..."
curl -s -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/config" | head -c 200
echo ""

