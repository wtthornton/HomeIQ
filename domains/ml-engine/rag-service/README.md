# RAG Service

Semantic knowledge storage and retrieval service using Retrieval-Augmented Generation (RAG).

## Overview

The RAG Service provides semantic knowledge storage and retrieval capabilities using embeddings from the OpenVINO service. It enables similarity-based search and knowledge management for AI-powered features.

## Features

- **Semantic Knowledge Storage**: Store text with embeddings for semantic search
- **Similarity-Based Retrieval**: Find similar knowledge using cosine similarity
- **OpenVINO Integration**: Uses OpenVINO service for embedding generation
- **Metrics Tracking**: Comprehensive metrics for monitoring (calls, latency, cache hits)
- **Async/Await**: Fully async implementation following 2025 patterns
- **Type Safety**: Full type hints throughout

## Architecture

```
rag-service (Port 8027)
├── FastAPI application (async/await)
├── SQLAlchemy async database (SQLite)
├── OpenVINO client (embeddings, reranking)
├── RAG service (store, retrieve, search)
├── API routers (store, retrieve, search, metrics)
└── Metrics tracking (calls, latency, cache hits)
```

## API Endpoints

### Health

- `GET /health` - Health check
- `GET /health/ready` - Readiness probe

### RAG Operations

- `POST /api/v1/rag/store` - Store knowledge with embedding
- `POST /api/v1/rag/retrieve` - Retrieve similar knowledge
- `POST /api/v1/rag/search` - Search knowledge with filters
- `PUT /api/v1/rag/{id}/success` - Update success score

### Metrics

- `GET /api/v1/metrics` - RAG service metrics
- `GET /api/v1/metrics/stats` - Detailed statistics

## Configuration

Environment variables (prefixed with `RAG_`):

- `RAG_SERVICE_PORT` - Service port (default: 8027)
- `RAG_DATABASE_PATH` - Database file path (default: rag_service.db)
- `RAG_OPENVINO_SERVICE_URL` - OpenVINO service URL (default: http://openvino-service:8019)
- `RAG_EMBEDDING_CACHE_SIZE` - Embedding cache size (default: 100)
- `RAG_LOG_LEVEL` - Logging level (default: INFO)

## Database

- **Type**: SQLite (async)
- **Model**: `RAGKnowledge`
  - `id`: Primary key
  - `text`: Text content
  - `embedding`: 1024-dim embedding vector (JSON)
  - `knowledge_type`: Type identifier (e.g., 'query', 'pattern')
  - `metadata`: Flexible metadata (JSON)
  - `success_score`: Success score (0.0-1.0)
  - `created_at`, `updated_at`: Timestamps

## Usage Example

### Store Knowledge

```bash
curl -X POST http://localhost:8027/api/v1/rag/store \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Turn on the office light",
    "knowledge_type": "query",
    "metadata": {"device_id": "office_light"},
    "success_score": 0.8
  }'
```

### Retrieve Similar Knowledge

```bash
curl -X POST http://localhost:8027/api/v1/rag/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Switch on office light",
    "knowledge_type": "query",
    "top_k": 5,
    "min_similarity": 0.7
  }'
```

### Get Metrics

```bash
curl http://localhost:8027/api/v1/metrics
```

## Development

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run service
python -m uvicorn src.main:app --reload --port 8027
```

### Docker

```bash
# Build image
docker build -t rag-service .

# Run container
docker run -p 8027:8027 rag-service
```

### Testing

```bash
# Run tests
pytest tests/
```

## Dependencies

- **FastAPI**: Web framework
- **SQLAlchemy**: Async database ORM
- **httpx**: Async HTTP client
- **numpy**: Numerical operations (cosine similarity)
- **tenacity**: Retry logic
- **OpenVINO Service**: Embedding generation

## Integration

### OpenVINO Service

The RAG service depends on the OpenVINO service for embedding generation:

- Endpoint: `/embeddings`
- Model: BAAI/bge-m3-base (1024-dim embeddings)

### RAG Status Monitor

Metrics are exposed at `/api/v1/metrics` for integration with the RAG Status Monitor in the health dashboard.

## License

Part of the HomeIQ project.
