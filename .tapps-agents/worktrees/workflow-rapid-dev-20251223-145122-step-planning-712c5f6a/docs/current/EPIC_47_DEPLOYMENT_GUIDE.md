# Epic 47: BGE-M3 Deployment Guide

**Epic:** Epic 47 - BGE-M3 Embedding Model Upgrade  
**Status:** ✅ Complete - Ready for Deployment  
**Date:** December 2025

---

## Overview

This guide covers deploying the BGE-M3 embedding model upgrade. The upgrade replaces `all-MiniLM-L6-v2` (384-dim) with `BAAI/bge-m3-base` (1024-dim) for improved RAG accuracy.

---

## Prerequisites

- Docker and Docker Compose installed
- Linux environment (or WSL/Docker) for quantization script
- `optimum-cli` installed (for quantization)
- OpenVINO service access

---

## Deployment Steps

### Step 1: Quantize BGE-M3 Model

**Option A: Using the Quantization Script (Recommended)**

```bash
# Run quantization script (requires Linux/WSL/Docker)
bash scripts/quantize-bge-m3.sh
```

This will:
- Download `BAAI/bge-m3-base` from HuggingFace
- Quantize to INT8 format (~125MB)
- Save to `./models/bge-m3/bge-m3-base-int8/`
- Verify 1024-dim embeddings

**Option B: Manual Quantization**

```bash
# Install optimum-cli if needed
pip install optimum[openvino,intel]

# Create model directory
mkdir -p ./models/bge-m3/bge-m3-base-int8

# Quantize model
optimum-cli export openvino \
    --model BAAI/bge-m3-base \
    --task feature-extraction \
    --weight-format int8 \
    --cache-dir ./models/cache \
    ./models/bge-m3/bge-m3-base-int8
```

**Option C: Docker Container (If on Windows)**

```bash
# Run quantization in Docker container
docker run --rm -it \
    -v "$(pwd)/models:/app/models" \
    -v "$(pwd)/scripts:/app/scripts" \
    python:3.12-slim bash -c "
        pip install optimum[openvino,intel] transformers &&
        bash /app/scripts/quantize-bge-m3.sh
    "
```

### Step 2: Deploy OpenVINO Service

```bash
# Start OpenVINO service
docker-compose up -d openvino-service

# Check service health
curl http://localhost:8019/health

# Verify model status
curl http://localhost:8019/models/status
```

**Expected Response:**
```json
{
  "embedding_model": "BAAI/bge-m3-base",
  "embedding_dimension": 1024,
  "embedding_loaded": true,
  ...
}
```

### Step 3: Validate Deployment

**Option A: Using Validation Script**

```bash
bash scripts/validate-bge-m3-deployment.sh
```

**Option B: Manual Validation**

```bash
# Test embedding generation
curl -X POST http://localhost:8019/embeddings \
  -H "Content-Type: application/json" \
  -d '{"texts": ["test embedding"], "normalize": true}'

# Verify response has 1024-dim embeddings
# Check: "embeddings": [[...1024 values...]]
```

### Step 4: Regenerate Existing Embeddings (If Needed)

If you have existing 384-dim embeddings in the database:

**Option 1: Delete and Regenerate On-Demand**
```python
# Old embeddings will be regenerated automatically when accessed
# via RAG client
```

**Option 2: Batch Regeneration Script** (Create if needed)
```python
# Script to regenerate all embeddings with BGE-M3
# (To be created if batch regeneration is needed)
```

---

## Verification Checklist

- [ ] BGE-M3 model quantized and saved to `./models/bge-m3/bge-m3-base-int8/`
- [ ] OpenVINO service running and healthy
- [ ] Model status shows `BAAI/bge-m3-base` with 1024-dim
- [ ] Embedding generation produces 1024-dim vectors
- [ ] Latency is acceptable (<200ms per query)
- [ ] All tests passing (`pytest tests/`)

---

## Troubleshooting

### Model Not Loading

**Issue:** Model fails to load in OpenVINO service

**Solutions:**
1. Check model path: `./models/bge-m3/bge-m3-base-int8/openvino_model.xml` exists
2. Check service logs: `docker-compose logs openvino-service`
3. Verify model was quantized correctly
4. Check disk space (model is ~125MB)

### Wrong Embedding Dimension

**Issue:** Embeddings are 384-dim instead of 1024-dim

**Solutions:**
1. Verify model status: `curl http://localhost:8019/models/status`
2. Check service is using BGE-M3 (should show `BAAI/bge-m3-base`)
3. Restart service: `docker-compose restart openvino-service`

### High Latency

**Issue:** Embedding generation takes >200ms

**Solutions:**
1. Check system resources (CPU, memory)
2. Verify INT8 quantization (should be ~125MB)
3. Check for other processes using CPU
4. Consider preloading models: `OPENVINO_PRELOAD_MODELS=true`

---

## Performance Expectations

- **Model Size:** ~125MB INT8 (vs ~20MB for all-MiniLM-L6-v2)
- **Latency:** 50-150ms per query (vs 30-100ms for all-MiniLM-L6-v2)
- **Accuracy:** 10-15% improvement in semantic similarity
- **Memory:** ~125MB RAM for model (vs ~20MB)

---

## Rollback (If Needed)

If you need to rollback to all-MiniLM-L6-v2:

1. **Note:** This requires code changes (backward compatibility was removed for Alpha)
2. Revert Epic 47 code changes
3. Redeploy OpenVINO service
4. Regenerate embeddings if needed

---

## Next Steps

After successful deployment:

1. **Monitor Performance:** Track embedding generation latency and accuracy
2. **Measure Accuracy:** Compare RAG retrieval accuracy before/after upgrade
3. **Optimize:** Fine-tune if needed (Phase 2 - future epic)

---

## References

- **Epic Document:** `docs/prd/epic-47-bge-m3-embedding-upgrade.md`
- **Implementation:** `implementation/EPIC_47_BGE_M3_UPGRADE_COMPLETE.md`
- **Quantization Script:** `scripts/quantize-bge-m3.sh`
- **Validation Script:** `scripts/validate-bge-m3-deployment.sh`

---

**Status:** ✅ Ready for Deployment  
**Last Updated:** December 2025

