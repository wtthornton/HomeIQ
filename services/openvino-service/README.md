# OpenVINO Service

**Port:** 8019
**Purpose:** Optimized model inference using Intel OpenVINO INT8 quantization
**Status:** Production Ready

## Overview

The OpenVINO Service provides hardware-accelerated, optimized inference for transformer-based models using Intel's OpenVINO toolkit. All models are quantized to INT8 for 3-4x faster inference with minimal accuracy loss compared to full-precision models.

## Key Features

- **INT8 Quantization**: 3-4x faster inference than FP32
- **Model Optimization**: OpenVINO's graph optimization for CPUs
- **Lazy Loading**: Models load on first request (fast startup)
- **Three Optimized Models**: Embeddings, re-ranking, classification
- **Batch Processing**: Efficient batch inference support
- **Low Latency**: <100ms for most operations
- **Small Memory Footprint**: INT8 models are 4x smaller

## Optimized Models

### 1. all-MiniLM-L6-v2 (INT8) - Embeddings
- **Purpose**: Convert text to 384-dimensional embeddings
- **Size**: ~23MB (vs ~90MB FP32)
- **Latency**: 20-50ms per batch
- **Use case**: Semantic similarity, entity matching

### 2. bge-reranker-base (INT8) - Re-ranking
- **Purpose**: Re-rank candidates based on query relevance
- **Size**: ~100MB (vs ~400MB FP32)
- **Latency**: 30-80ms per batch
- **Use case**: Search result ranking, entity disambiguation

### 3. flan-t5-small (INT8) - Classification
- **Purpose**: Pattern classification and categorization
- **Size**: ~77MB (vs ~300MB FP32)
- **Latency**: 40-100ms per inference
- **Use case**: Pattern category detection, intent classification

## API Endpoints

### Health Check
```
GET /health
```

### Text Embeddings
```
POST /embed
Body: {
  "texts": ["office light", "living room lamp"],
  "normalize": true
}
Response: {
  "embeddings": [[0.1, -0.3, ...], [0.2, 0.1, ...]],
  "model_name": "all-MiniLM-L6-v2-int8",
  "processing_time": 0.035
}
```

### Candidate Re-ranking
```
POST /rerank
Body: {
  "query": "office light 1",
  "candidates": [
    {"entity_id": "light.office_1", "name": "Office Front Left"},
    {"entity_id": "light.bedroom_1", "name": "Bedroom Light"}
  ],
  "top_k": 5
}
Response: {
  "ranked_candidates": [
    {"entity_id": "light.office_1", "score": 0.92, ...},
    {"entity_id": "light.bedroom_1", "score": 0.34, ...}
  ],
  "model_name": "bge-reranker-base-int8",
  "processing_time": 0.058
}
```

### Pattern Classification
```
POST /classify
Body: {
  "pattern_description": "Turn on office lights at 6 PM on weekdays"
}
Response: {
  "category": "time_based_automation",
  "priority": "medium",
  "model_name": "flan-t5-small-int8",
  "processing_time": 0.067
}
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8019` | Service port |
| `MODEL_CACHE_DIR` | `/app/models` | Directory for model storage |
| `LOG_LEVEL` | `INFO` | Logging level |
| `DEVICE` | `CPU` | OpenVINO device (CPU/GPU) |

## Architecture

```
┌──────────────────────┐
│  OpenVINO Service    │
│    (Port 8019)       │
└──────────┬───────────┘
           │
    ┌──────┴─────┬─────────┐
    │            │         │
    ▼            ▼         ▼
┌─────────┐  ┌────────┐  ┌──────────┐
│MiniLM   │  │BGE     │  │FLAN-T5   │
│INT8     │  │Reranker│  │Small INT8│
│Embedding│  │INT8    │  │Classifier│
└─────────┘  └────────┘  └──────────┘
```

## Model Loading Strategy

**Lazy Loading** (default):
- Models DON'T load on service startup
- First request triggers model load (~2-5s delay)
- Subsequent requests are fast (<100ms)
- Reduces startup time from 5 minutes to <5 seconds

**Pre-loading** (optional):
```python
# Uncomment in main.py to pre-load all models
await openvino_manager.initialize()
```

## Performance

| Operation | Cold Start | Warm Inference | Speedup vs FP32 |
|-----------|-----------|----------------|-----------------|
| Embeddings (10 texts) | 2-3s | 20-50ms | 3.5x |
| Re-ranking (20 candidates) | 3-5s | 30-80ms | 4.2x |
| Classification | 2-4s | 40-100ms | 3.8x |

**Memory Usage**:
- Idle: ~100MB
- All models loaded: ~400MB (vs ~1.5GB FP32)

## Development

### Running Locally
```bash
cd services/openvino-service
docker-compose up --build
```

### Testing
```bash
# Health check
curl http://localhost:8019/health

# Generate embeddings
curl -X POST http://localhost:8019/embed \
  -H "Content-Type: application/json" \
  -d '{"texts": ["office light", "bedroom lamp"]}'

# Re-rank candidates
curl -X POST http://localhost:8019/rerank \
  -H "Content-Type: application/json" \
  -d '{
    "query": "office light",
    "candidates": [
      {"entity_id": "light.office", "name": "Office Light"},
      {"entity_id": "light.garage", "name": "Garage Light"}
    ]
  }'

# Classify pattern
curl -X POST http://localhost:8019/classify \
  -H "Content-Type: application/json" \
  -d '{"pattern_description": "Turn on lights at sunset"}'
```

## Dependencies

- FastAPI (web framework)
- openvino (Intel OpenVINO toolkit)
- optimum-intel (Hugging Face OpenVINO integration)
- transformers (model loading)
- numpy (numerical operations)

## Quantization Details

### INT8 vs FP32

| Metric | FP32 (Full Precision) | INT8 (Quantized) |
|--------|----------------------|------------------|
| **Model Size** | 100% | 25% |
| **Inference Speed** | 1x | 3-4x |
| **Memory** | 100% | 25% |
| **Accuracy** | 100% | 98-99% |
| **Hardware** | Any | CPU optimized |

### Quantization Process
Models are quantized using OpenVINO's Post-Training Quantization (PTQ):
1. Load FP32 model from Hugging Face
2. Calibrate on representative dataset
3. Convert to OpenVINO IR format (INT8)
4. Optimize graph for CPU inference

## Use Cases

### 1. Entity Resolution (Embeddings)
```python
# Convert entity names to embeddings for similarity matching
texts = ["Office Front Left", "Office light 1"]
embeddings = await get_embeddings(texts)
similarity = cosine_similarity(embeddings[0], embeddings[1])
# Result: 0.87 (high similarity)
```

### 2. Search Re-ranking (BGE Reranker)
```python
# Re-rank Home Assistant entities by relevance
query = "office light 1"
candidates = [
  {"entity_id": "light.hue_go_1", "name": "Office Front Left"},
  {"entity_id": "light.garage_2", "name": "Garage Light 2"}
]
ranked = await rerank(query, candidates)
# Result: light.hue_go_1 (0.92), light.garage_2 (0.15)
```

### 3. Pattern Classification (FLAN-T5)
```python
# Classify automation pattern type
description = "Turn on office lights when motion detected"
category = await classify(description)
# Result: {"category": "motion_triggered", "priority": "high"}
```

## Monitoring

Logs structured JSON with:
- Model load times (cold start)
- Inference latency (per model)
- Batch sizes
- Error rates
- Memory usage

## Related Services

- [AI Core Service](../ai-core-service/README.md) - Orchestrates OpenVINO calls
- [ML Service](../ml-service/README.md) - Classical ML algorithms
- [AI Automation Service](../ai-automation-service/README.md) - Consumer of embeddings

## When to Use OpenVINO vs ML Service

| Use OpenVINO Service | Use ML Service |
|---------------------|----------------|
| Text embeddings | Clustering |
| Semantic similarity | Anomaly detection |
| Natural language tasks | Numerical data |
| Re-ranking | Feature importance |
| Classification | Fast prototyping |

## Optimization Tips

1. **Batch Requests**: Process multiple texts together for better throughput
2. **Normalize Embeddings**: Set `normalize=true` for cosine similarity
3. **Limit Top-K**: Re-ranking 5-10 candidates is optimal
4. **Cache Embeddings**: Store frequently used embeddings in Redis
5. **Monitor Cold Starts**: First request is slow (model loading)

## Troubleshooting

### Slow first request
- Expected behavior (lazy loading)
- Consider pre-loading models if needed
- Warm up models on startup with dummy requests

### High memory usage
- All 3 models loaded: ~400MB expected
- Check for memory leaks with `docker stats`
- Restart service if memory grows unbounded

### Poor embedding quality
- Ensure text is clean (no special characters)
- Use descriptive text (not just IDs)
- Normalize embeddings for cosine similarity

### Low accuracy
- INT8 quantization: 98-99% of FP32 accuracy expected
- Check if calibration dataset matches use case
- Consider FP32 models if accuracy critical
