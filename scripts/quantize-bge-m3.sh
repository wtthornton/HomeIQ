#!/bin/bash
# BGE-M3 Model Quantization Script
# Epic 47, Story 47.1: BGE-M3 Model Download and Quantization
# Created: December 2025

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
MODEL_NAME="BAAI/bge-m3-base"
MODELS_DIR="${MODELS_DIR:-./models/bge-m3}"
CACHE_DIR="${CACHE_DIR:-./models/cache}"
TARGET_DIR="${MODELS_DIR}/bge-m3-base-int8"

echo -e "${BLUE}╔════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  BGE-M3 Embedding Model - Quantization Script     ║${NC}"
echo -e "${BLUE}║  Epic 47: BGE-M3 Embedding Upgrade (Phase 1)      ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════╝${NC}"
echo ""

# Create directories
echo -e "${YELLOW}📁 Creating model directories...${NC}"
mkdir -p "$TARGET_DIR"
mkdir -p "$CACHE_DIR"

# Check if optimum-cli is installed
if ! command -v optimum-cli &> /dev/null; then
    echo -e "${RED}❌ Error: optimum-cli not found${NC}"
    echo -e "${YELLOW}Please install: pip install optimum[openvino,intel]${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Directories created${NC}"
echo ""

# ============================================================================
# Quantize BGE-M3-base Model
# ============================================================================

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}📦 Quantizing BGE-M3-base Model...${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "Model: ${MODEL_NAME}"
echo -e "Task: feature-extraction"
echo -e "Quantization: INT8 weight quantization"
echo -e "Target: ~125MB (vs ~500MB FP32)"
echo -e "Dimensions: 1024 (vs 384 for all-MiniLM-L6-v2)"
echo ""

if [ -f "$TARGET_DIR/openvino_model.xml" ]; then
    echo -e "${GREEN}✅ BGE-M3 model already quantized (skipping)${NC}"
    echo -e "${YELLOW}To re-quantize, delete: ${TARGET_DIR}${NC}"
else
    echo -e "${YELLOW}Downloading and quantizing model (this may take several minutes)...${NC}"
    
    optimum-cli export openvino \
        --model "${MODEL_NAME}" \
        --task feature-extraction \
        --weight-format int8 \
        --cache-dir "$CACHE_DIR" \
        "$TARGET_DIR"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ BGE-M3 model quantized successfully!${NC}"
    else
        echo -e "${RED}❌ Failed to quantize BGE-M3 model${NC}"
        exit 1
    fi
fi

echo ""

# ============================================================================
# Verify Model
# ============================================================================

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}🔍 Verifying quantized model...${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

python3 << EOF
import sys
from pathlib import Path

try:
    from optimum.intel import OVModelForFeatureExtraction
    from transformers import AutoTokenizer
    
    model_dir = Path("${TARGET_DIR}")
    
    if not (model_dir / "openvino_model.xml").exists():
        print("❌ Model file not found")
        sys.exit(1)
    
    print("Loading quantized model...")
    model = OVModelForFeatureExtraction.from_pretrained(str(model_dir))
    tokenizer = AutoTokenizer.from_pretrained("${MODEL_NAME}", cache_dir="${CACHE_DIR}")
    
    # Test embedding generation
    test_texts = ["test embedding"]
    inputs = tokenizer(test_texts, return_tensors='pt', padding=True, truncation=True)
    outputs = model(**inputs)
    embeddings = outputs.last_hidden_state.mean(dim=1)
    
    embedding_dim = embeddings.shape[1]
    print(f"✅ Model loaded successfully")
    print(f"   Embedding dimension: {embedding_dim}")
    
    if embedding_dim == 1024:
        print("✅ Embedding dimension correct (1024)")
    else:
        print(f"⚠️  Expected 1024 dimensions, got {embedding_dim}")
        sys.exit(1)
        
except Exception as e:
    print(f"❌ Error verifying model: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
EOF

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Model verification failed${NC}"
    exit 1
fi

echo ""

# ============================================================================
# Summary
# ============================================================================

echo -e "${BLUE}╔════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║        BGE-M3 Quantization Complete!              ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${GREEN}📊 Model Information:${NC}"
echo -e "┌────────────────────────────────────────────────────┐"
echo -e "│ Property                    │ Value                │"
echo -e "├────────────────────────────────────────────────────┤"

if [ -d "$TARGET_DIR" ]; then
    MODEL_SIZE=$(du -sh "$TARGET_DIR" | cut -f1)
    echo -e "│ Model Size                  │ ${MODEL_SIZE}               │"
fi

echo -e "│ Embedding Dimensions        │ 1024                 │"
echo -e "│ Quantization                │ INT8                  │"
echo -e "│ Model Path                  │ ${TARGET_DIR} │"
echo -e "└────────────────────────────────────────────────────┘"
echo ""

echo -e "${GREEN}✅ Next steps:${NC}"
echo -e "   1. Update OpenVINO service to use BGE-M3 (Story 47.2)"
echo -e "   2. Update RAG client for 1024-dim embeddings (Story 47.3)"
echo -e "   3. Create database migration (Story 47.4)"
echo -e "   4. Run tests and validation (Story 47.5)"
echo ""

echo -e "${BLUE}╔════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Ready for BGE-M3 Integration! 🚀                ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════╝${NC}"

