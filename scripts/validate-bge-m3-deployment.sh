#!/bin/bash
# BGE-M3 Deployment Validation Script
# Epic 47: Validates BGE-M3 deployment and configuration
# Created: December 2025

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

OPENVINO_URL="${OPENVINO_URL:-http://localhost:8019}"

echo -e "${BLUE}╔════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  BGE-M3 Deployment Validation                     ║${NC}"
echo -e "${BLUE}║  Epic 47: BGE-M3 Embedding Upgrade               ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if OpenVINO service is running
echo -e "${YELLOW}1. Checking OpenVINO service...${NC}"
if ! curl -s -f "${OPENVINO_URL}/health" > /dev/null 2>&1; then
    echo -e "${RED}❌ OpenVINO service is not running at ${OPENVINO_URL}${NC}"
    echo -e "${YELLOW}   Start it with: docker-compose up -d openvino-service${NC}"
    exit 1
fi
echo -e "${GREEN}✅ OpenVINO service is running${NC}"
echo ""

# Check model status
echo -e "${YELLOW}2. Checking model status...${NC}"
STATUS=$(curl -s "${OPENVINO_URL}/models/status")
MODEL_NAME=$(echo "$STATUS" | grep -o '"embedding_model":"[^"]*"' | cut -d'"' -f4)
DIMENSION=$(echo "$STATUS" | grep -o '"embedding_dimension":[0-9]*' | cut -d':' -f2)
LOADED=$(echo "$STATUS" | grep -o '"embedding_loaded":[^,}]*' | cut -d':' -f2)

if [ "$MODEL_NAME" != "BAAI/bge-m3-base" ]; then
    echo -e "${RED}❌ Wrong embedding model: ${MODEL_NAME} (expected: BAAI/bge-m3-base)${NC}"
    exit 1
fi

if [ "$DIMENSION" != "1024" ]; then
    echo -e "${RED}❌ Wrong embedding dimension: ${DIMENSION} (expected: 1024)${NC}"
    exit 1
fi

if [ "$LOADED" != "true" ]; then
    echo -e "${YELLOW}⚠️  Model not loaded yet (may be lazy-loading)${NC}"
else
    echo -e "${GREEN}✅ Model loaded: ${MODEL_NAME} (${DIMENSION}-dim)${NC}"
fi
echo ""

# Test embedding generation
echo -e "${YELLOW}3. Testing embedding generation...${NC}"
RESPONSE=$(curl -s -X POST "${OPENVINO_URL}/embeddings" \
    -H "Content-Type: application/json" \
    -d '{"texts": ["test embedding"], "normalize": true}')

EMBEDDING_COUNT=$(echo "$RESPONSE" | grep -o '"embeddings":\[\[[^]]*\]\]' | grep -o ',' | wc -l || echo "0")
EMBEDDING_DIM=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(len(data['embeddings'][0]))" 2>/dev/null || echo "0")

if [ "$EMBEDDING_DIM" != "1024" ]; then
    echo -e "${RED}❌ Wrong embedding dimension: ${EMBEDDING_DIM} (expected: 1024)${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Embedding generation works (${EMBEDDING_DIM}-dim)${NC}"
echo ""

# Performance test
echo -e "${YELLOW}4. Performance test...${NC}"
START_TIME=$(date +%s%N)
curl -s -X POST "${OPENVINO_URL}/embeddings" \
    -H "Content-Type: application/json" \
    -d '{"texts": ["performance test"], "normalize": true}" > /dev/null
END_TIME=$(date +%s%N)
DURATION_MS=$(( (END_TIME - START_TIME) / 1000000 ))

if [ "$DURATION_MS" -gt 200 ]; then
    echo -e "${YELLOW}⚠️  Latency: ${DURATION_MS}ms (target: <100ms, acceptable: <200ms)${NC}"
else
    echo -e "${GREEN}✅ Latency: ${DURATION_MS}ms (acceptable)${NC}"
fi
echo ""

# Summary
echo -e "${BLUE}╔════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║           Validation Complete!                    ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}✅ BGE-M3 deployment validated successfully${NC}"
echo -e "   Model: ${MODEL_NAME}"
echo -e "   Dimension: ${DIMENSION}"
echo -e "   Latency: ${DURATION_MS}ms"
echo ""

