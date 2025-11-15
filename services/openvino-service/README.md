# OpenVINO Service

**Transformer-Based Embeddings and Re-ranking Service**

**Port:** 8019
**Technology:** Python 3.11+, FastAPI 0.121, sentence-transformers 3.3, PyTorch 2.3 (CPU)
**Container:** `homeiq-openvino-service`

## Overview

The OpenVINO Service provides transformer-based model inference for embeddings, re-ranking, and classification tasks. Originally designed for Intel OpenVINO optimization, it currently uses sentence-transformers with CPU-optimized PyTorch for broad compatibility.

**Note:** Service name retained for API compatibility. OpenVINO quantization temporarily removed due to dependency conflicts; currently using standard sentence-transformers models.

### Key Features

- **Text Embeddings** - all-MiniLM-L6-v2 for semantic similarity
- **Re-ranking** - BGE reranker for search result ranking
- **Classification** - FLAN-T5 for pattern categorization
- **Concurrency-Safe Loading** - Async locks prevent duplicate downloads and OOM spikes
- **Guardrails & Timeouts** - Input limits plus inference timeouts to prevent hangs/DoS
- **Lazy Loading** - Models load on first request (fast startup) with optional preloading
- **CPU Optimized** - PyTorch CPU-only (no CUDA, saves 8.5GB)
- **Low Latency** - <100ms for most operations
- **Batch Processing** - Efficient multi-text processing

## Quick Start

### Prerequisites

- Python 3.11+
- PyTorch 2.3+ (CPU)
- sentence-transformers 3.3+

### Running Locally

```bash
cd services/openvino-service

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start service
uvicorn src.main:app --reload --port 8019
```

### Running with Docker

```bash
# Build and start
docker compose up -d openvino-service

# View logs
docker compose logs -f openvino-service

# Check health
curl http://localhost:8019/health
```

## API Endpoints

### Health & Status

#### `GET /health`
Service health check
```bash
curl http://localhost:8019/health
```

### Text Embeddings

#### `POST /embeddings`
Convert text to 384-dimensional embeddings (max 100 texts, 4,000 chars each by default)

```bash
curl -X POST http://localhost:8019/embeddings \
  -H "Content-Type: application/json" \
  -d '{
    "texts": ["office light", "bedroom lamp"],
    "normalize": true
  }'
```

**Request:**
```json
{
  "texts": ["office light", "living room lamp"],
  "normalize": true
}
```

**Response:**
```json
{
  "embeddings": [[0.1, -0.3, ...], [0.2, 0.1, ...]],
  "model_name": "all-MiniLM-L6-v2",
  "processing_time": 0.035
}
```

### Candidate Re-ranking

#### `POST /rerank`
Re-rank candidates based on query relevance (max 200 candidates / top_k capped at 50)

```bash
curl -X POST http://localhost:8019/rerank \
  -H "Content-Type: application/json" \
  -d '{
    "query": "office light 1",
    "candidates": [
      {"entity_id": "light.office_1", "name": "Office Front Left"},
      {"entity_id": "light.bedroom_1", "name": "Bedroom Light"}
    ],
    "top_k": 5
  }'
```

**Request:**
```json
{
  "query": "office light 1",
  "candidates": [
    {"entity_id": "light.office_1", "name": "Office Front Left"},
    {"entity_id": "light.bedroom_1", "name": "Bedroom Light"}
  ],
  "top_k": 5
}
```

**Response:**
```json
{
  "ranked_candidates": [
    {"entity_id": "light.office_1", "score": 0.92, "name": "Office Front Left"},
    {"entity_id": "light.bedroom_1", "score": 0.34, "name": "Bedroom Light"}
  ],
  "model_name": "bge-reranker-base",
  "processing_time": 0.058
}
```

### Pattern Classification

#### `POST /classify`
Classify automation patterns (pattern description up to 4,000 chars by default)

```bash
curl -X POST http://localhost:8019/classify \
  -H "Content-Type: application/json" \
  -d '{
    "pattern_description": "Turn on office lights at 6 PM on weekdays"
  }'
```

**Request:**
```json
{
  "pattern_description": "Turn on office lights at 6 PM on weekdays"
}
```

**Response:**
```json
{
  "category": "time_based_automation",
  "priority": "medium",
  "model_name": "flan-t5-small",
  "processing_time": 0.067
}
```

## Safety Guardrails (2025)

- **Request Limits**  
  - Embeddings: up to `OPENVINO_MAX_EMBEDDING_TEXTS` (default 100) texts, 4,000 characters each  
  - Re-rank: up to `OPENVINO_MAX_RERANK_CANDIDATES` (default 200) candidates, `top_k` capped at 50  
  - Classify: pattern descriptions limited to 4,000 characters
- **Inference Timeouts**  
  `OPENVINO_MODEL_LOAD_TIMEOUT` and `OPENVINO_INFERENCE_TIMEOUT` prevent hung downloads or forward passes (default 180s / 30s)
- **Concurrency Locks**  
  Async `asyncio.Lock` per model prevents duplicate loads that previously caused OOM spikes
- **Deterministic Cleanup**  
  Explicit tensor deletion + `gc.collect()` and optional cache purge (`OPENVINO_CLEAR_CACHE_ON_CLEANUP`) keep the 1.5 GB container within limits
- **Health Reporting**  
  `/health` now reports `ready`, `warming`, and per-model state so upstream services can gate requests correctly

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8019` | Service port |
| `MODEL_CACHE_DIR` | `/app/models` | Model storage directory |
| `LOG_LEVEL` | `INFO` | Logging level |
| `DEVICE` | `CPU` | Device for inference |
| `OPENVINO_PRELOAD_MODELS` | `false` | Pre-load models during startup instead of lazy loading |
| `OPENVINO_MODEL_LOAD_TIMEOUT` | `180` | Seconds to wait for model downloads/compilation |
| `OPENVINO_INFERENCE_TIMEOUT` | `30` | Seconds to wait for inference before aborting |
| `OPENVINO_MAX_EMBEDDING_TEXTS` | `100` | Max texts accepted by `/embeddings` |
| `OPENVINO_MAX_TEXT_LENGTH` | `4000` | Max characters per text / query |
| `OPENVINO_MAX_RERANK_CANDIDATES` | `200` | Max candidates accepted by `/rerank` |
| `OPENVINO_MAX_RERANK_TOP_K` | `50` | Hard cap on `top_k` for reranking |
| `OPENVINO_MAX_PATTERN_LENGTH` | `4000` | Max characters accepted by `/classify` |
| `OPENVINO_CLEAR_CACHE_ON_CLEANUP` | `false` | Purge cached HuggingFace artifacts on shutdown |

### Example `.env`

```bash
PORT=8019
MODEL_CACHE_DIR=/app/models
LOG_LEVEL=INFO
DEVICE=CPU
OPENVINO_PRELOAD_MODELS=false
OPENVINO_INFERENCE_TIMEOUT=30
OPENVINO_MAX_EMBEDDING_TEXTS=100
```

## Architecture

### Component Architecture

```
┌──────────────────────────────┐
│   OpenVINO Service           │
│   (Port 8019)                │
│                              │
│  ┌────────────────────────┐ │
│  │ Model Manager          │ │
│  │ (Lazy Loading)         │ │
│  └───────────┬────────────┘ │
│              │              │
│  ┌───────────┼────────────┐ │
│  │           │            │ │
│  ▼           ▼            ▼ │
│ ┌────┐    ┌────┐    ┌─────┐│
│ │Mini│    │BGE │    │FLAN ││
│ │LM  │    │Rank│    │T5   ││
│ └────┘    └────┘    └─────┘│
└──────────────────────────────┘
```

### Supported Models

#### 1. all-MiniLM-L6-v2 - Embeddings
- **Purpose:** Text to 384-dim embeddings
- **Size:** ~90MB
- **Latency:** 20-50ms per batch
- **Use case:** Semantic similarity, entity matching

#### 2. bge-reranker-base - Re-ranking
- **Purpose:** Re-rank candidates by relevance
- **Size:** ~400MB
- **Latency:** 30-80ms per batch
- **Use case:** Search ranking, disambiguation

#### 3. flan-t5-small - Classification
- **Purpose:** Pattern classification
- **Size:** ~300MB
- **Latency:** 40-100ms per inference
- **Use case:** Category detection, intent classification

### Model Loading Strategy

**Lazy Loading** (default / `OPENVINO_PRELOAD_MODELS=false`):
- Models DON'T load on service startup (service responds immediately)
- First request per model triggers download/compile (~2-5s delay)
- Async locks guarantee only one download per model to avoid double allocation
- Subsequent requests stay <100 ms with in-memory cache

**Pre-loading** (optional / `OPENVINO_PRELOAD_MODELS=true`):
- Models load once during FastAPI startup via the lifespan hook
- Guarantees `/health` reports `ready` before other services connect
- Recommended if you prefer predictable cold-start latency and can tolerate longer container boot time (~3-5 minutes)

## Use Cases

### 1. Entity Resolution (Embeddings)
Convert entity names to embeddings for similarity matching:
```python
texts = ["Office Front Left", "Office light 1"]
embeddings = await get_embeddings(texts)
similarity = cosine_similarity(embeddings[0], embeddings[1])
# Result: 0.87 (high similarity)
```

### 2. Search Re-ranking (BGE Reranker)
Re-rank Home Assistant entities by relevance:
```python
query = "office light 1"
candidates = [
  {"entity_id": "light.hue_go_1", "name": "Office Front Left"},
  {"entity_id": "light.garage_2", "name": "Garage Light 2"}
]
ranked = await rerank(query, candidates)
# Result: light.hue_go_1 (0.92), light.garage_2 (0.15)
```

### 3. Pattern Classification (FLAN-T5)
Classify automation pattern type:
```python
description = "Turn on office lights when motion detected"
category = await classify(description)
# Result: {"category": "motion_triggered", "priority": "high"}
```

## Performance

### Performance Targets

| Operation | Cold Start | Warm Inference | Target |
|-----------|-----------|----------------|--------|
| Embeddings (10 texts) | 2-3s | 20-50ms | <100ms |
| Re-ranking (20 candidates) | 3-5s | 30-80ms | <150ms |
| Classification | 2-4s | 40-100ms | <200ms |

### Resource Usage

- **Idle:** ~100MB
- **All models loaded:** ~800MB
- **CPU:** <10% typical, <50% during inference

## Development

### Testing

```bash
# Health check
curl http://localhost:8019/health

# Generate embeddings
curl -X POST http://localhost:8019/embed \
  -H "Content-Type: application/json" \
  -d '{"texts": ["office light", "bedroom lamp"], "normalize": true}'

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

### Core

```
fastapi==0.121.2              # Web framework
uvicorn[standard]==0.38.0     # ASGI server
pydantic==2.12.4              # Data validation
pydantic-settings==2.12.0     # Settings management
```

### Machine Learning

```
sentence-transformers==3.3.1  # Embeddings (all-MiniLM-L6-v2)
transformers==4.46.1          # HuggingFace models
torch==2.3.1+cpu              # PyTorch CPU-only (1.5GB vs 10GB with CUDA)
sentencepiece                 # T5 tokenizer
```

### Data Processing

```
pandas==2.3.3                 # Data analysis
numpy==2.3.4                  # Numerical computing
```

### Utilities

```
httpx==0.27.2                 # HTTP client
python-dotenv==1.2.1          # Environment variables
tenacity==8.2.3               # Retry logic
```

### Testing

```
pytest==8.3.3                 # Testing framework
pytest-asyncio==0.23.0        # Async test support
```

## Monitoring

### Structured Logging

Logs include:
- Model load times (cold start)
- Inference latency (per model)
- Batch sizes
- Error rates
- Memory usage

### Metrics

- Request latency per model
- Model usage distribution
- Batch processing efficiency
- Error rates

## Troubleshooting

### Slow First Request

**Symptoms:**
- First request takes 2-5 seconds

**Solution:**
- Expected behavior (lazy loading)
- Consider pre-loading models if needed
- Warm up models on startup with dummy requests

### High Memory Usage

**Symptoms:**
- Service using >1GB memory

**Solutions:**
- All 3 models loaded: ~800MB expected
- Check for memory leaks with `docker stats`
- Restart service if memory grows unbounded

### Poor Embedding Quality

**Symptoms:**
- Low similarity scores for similar text

**Solutions:**
- Ensure text is clean (no special characters)
- Use descriptive text (not just IDs)
- Normalize embeddings for cosine similarity

### Model Loading Errors

**Symptoms:**
- Models fail to download or load

**Solutions:**
- Check internet connectivity (models download from HuggingFace)
- Verify disk space in `MODEL_CACHE_DIR`
- Check HuggingFace API status

## OpenVINO Service vs ML Service

| Use OpenVINO Service | Use ML Service |
|---------------------|----------------|
| Text embeddings | Clustering |
| Semantic similarity | Anomaly detection |
| Natural language tasks | Numerical data |
| Re-ranking | Feature importance |
| Classification | Fast prototyping |

## Optimization Tips

1. **Batch Requests** - Process multiple texts together for better throughput
2. **Normalize Embeddings** - Set `normalize=true` for cosine similarity
3. **Limit Top-K** - Re-ranking 5-10 candidates is optimal
4. **Cache Embeddings** - Store frequently used embeddings in Redis
5. **Monitor Cold Starts** - First request is slow (model loading)

## Related Documentation

- [AI Core Service](../ai-core-service/README.md) - Orchestrates OpenVINO calls
- [ML Service](../ml-service/README.md) - Classical ML algorithms
- [AI Automation Service](../ai-automation-service/README.md) - Consumer of embeddings
- [API Reference](../../docs/api/API_REFERENCE.md)
- [CLAUDE.md](../../CLAUDE.md)

## Support

- **Issues:** https://github.com/wtthornton/HomeIQ/issues
- **Documentation:** `/docs` directory
- **Health Check:** http://localhost:8019/health
- **API Docs:** http://localhost:8019/docs

## Version History

### 2.1 (November 15, 2025)
- Updated documentation to 2025 standards
- Noted OpenVINO removal (dependency conflicts)
- Now using sentence-transformers with CPU-optimized PyTorch
- Enhanced troubleshooting and dependency documentation
- Corrected model sizes and performance characteristics

### 2.0 (October 2025)
- INT8 quantization with OpenVINO (deprecated)
- 3-4x performance improvements
- Three optimized models

### 1.0 (Initial Release)
- Standard transformer models
- Basic embedding and re-ranking

---

**Last Updated:** November 15, 2025
**Version:** 2.1
**Status:** Production Ready ✅
**Port:** 8019
**Note:** OpenVINO quantization temporarily removed; using sentence-transformers
