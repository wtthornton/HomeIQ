# ML Service

**Classical Machine Learning for Pattern Detection and Analysis**

**Port:** 8020 (internal), exposed as 8025 (external)
**Technology:** Python 3.11+, FastAPI 0.121, scikit-learn 1.4, pandas 2.3
**Container:** `homeiq-ml-service`
**Database:** None (stateless ML service)
**Scale:** Optimized for ~50-100 devices (single-home, not multi-home)

## Overview

The ML Service provides classical machine learning algorithms for clustering, anomaly detection, and feature analysis. It complements deep learning models with traditional ML algorithms that are faster, more interpretable, and don't require pre-training for certain tasks.

**Port Mapping Note:** The service runs on internal port 8020 but is exposed as port 8025 externally to avoid port conflicts with other services. All examples in this document use port 8025 (external) for production access. When developing locally without Docker, use port 8020.

### Key Features

- **Clustering Algorithms** - KMeans, DBSCAN for pattern grouping
- **Anomaly Detection** - Isolation Forest for outlier detection
- **Feature Importance** - Random Forest for feature ranking
- **Batch Processing** - Efficient multi-operation processing
- **Fast Inference** - <100ms for most operations
- **No Pre-training** - Classical algorithms ready to use
- **Interpretable Results** - Understandable decision processes

## Quick Start

### Prerequisites

- Python 3.11+
- scikit-learn 1.4+

### Running Locally

```bash
cd services/ml-service

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start service
uvicorn src.main:app --reload --port 8020
```

### Running with Docker

```bash
# Build and start
docker compose up -d ml-service

# View logs
docker compose logs -f ml-service

# Check health
curl http://localhost:8025/health
```

## API Endpoints

### Health & Status

#### `GET /health`
Service health check
```bash
curl http://localhost:8025/health
```

### Clustering

#### `POST /cluster`
Group data points into clusters

```bash
curl -X POST http://localhost:8025/cluster \
  -H "Content-Type: application/json" \
  -d '{
    "data": [[1.0, 2.0], [1.5, 1.8], [5.0, 8.0], [5.5, 8.5]],
    "algorithm": "kmeans",
    "n_clusters": 2
  }'
```

**Request:**
```json
{
  "data": [[1.0, 2.0], [1.5, 1.8], ...],
  "algorithm": "kmeans|dbscan",
  "n_clusters": 3,    // for KMeans
  "eps": 0.5          // for DBSCAN
}
```

**Response:**
```json
{
  "labels": [0, 0, 1, 1],
  "n_clusters": 2,
  "algorithm": "kmeans",
  "processing_time": 0.045
}
```

### Anomaly Detection

#### `POST /anomaly`
Identify outliers in data

```bash
curl -X POST http://localhost:8025/anomaly \
  -H "Content-Type: application/json" \
  -d '{
    "data": [[1.0, 1.0], [1.2, 1.1], [10.0, 10.0]],
    "contamination": 0.1
  }'
```

**Request:**
```json
{
  "data": [[1.0, 2.0], [1.5, 1.8], ...],
  "contamination": 0.1  // expected outlier proportion
}
```

**Response:**
```json
{
  "labels": [1, 1, -1, 1],      // 1=normal, -1=anomaly
  "scores": [0.3, 0.2, 0.9, ...],
  "n_anomalies": 1,
  "processing_time": 0.032
}
```

### Batch Processing

#### `POST /batch/process`
Process multiple operations efficiently

```bash
curl -X POST http://localhost:8025/batch/process \
  -H "Content-Type: application/json" \
  -d '{
    "operations": [
      {"type": "cluster", "data": [[1,2],[3,4]], "algorithm": "kmeans", "n_clusters": 2},
      {"type": "anomaly", "data": [[1,1],[10,10]], "contamination": 0.1}
    ]
  }'
```

**Response:**
```json
{
  "results": [
    {"labels": [0, 1], "n_clusters": 2},
    {"labels": [1, -1], "n_anomalies": 1}
  ],
  "processing_time": 0.087
}
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8020` | Service port |
| `LOG_LEVEL` | `INFO` | Logging level |
| `ML_ALLOWED_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001` | Comma-separated list of trusted frontends |
| `ML_MAX_BATCH_SIZE` | `100` | Maximum operations per batch request |
| `ML_MAX_PAYLOAD_BYTES` | `10MB` | Maximum data payload per operation |
| `ML_MAX_DIMENSIONS` | `1000` | Maximum features per row |
| `ML_MAX_CLUSTERS` | `100` | Safety cap for requested clusters |
| `ML_MAX_DATA_POINTS` | `50000` | Upper bound on rows per request |
| `ML_ALGORITHM_TIMEOUT_SECONDS` | `8` | Timeout for CPU-bound operations |

## Architecture

### Component Architecture

```
┌─────────────────────────────┐
│      ML Service             │
│      (Port 8020)            │
│                             │
│  ┌───────────────────────┐ │
│  │ Algorithm Manager     │ │
│  └───────────┬───────────┘ │
│              │             │
│  ┌───────────┼───────────┐ │
│  │           │           │ │
│  ▼           ▼           ▼ │
│ ┌────┐    ┌────┐    ┌────┐│
│ │KMea│    │DBSC│    │Iso ││
│ │ns  │    │AN  │    │For ││
│ └────┘    └────┘    └────┘│
└─────────────────────────────┘
```

### Supported Algorithms

**Clustering:**
- **KMeans** - Partition data into K clusters
  - Best for: Well-separated, spherical clusters
  - Parameters: `n_clusters` (number of clusters)
  - Time complexity: O(n × k × i)

- **DBSCAN** - Density-based clustering
  - Best for: Arbitrary shapes, noisy data
  - Parameters: `eps` (radius), `min_samples`
  - Time complexity: O(n log n)

**Anomaly Detection:**
- **Isolation Forest** - Outlier detection
  - Best for: High-dimensional data
  - Parameters: `contamination` (outlier proportion)
  - Time complexity: O(n log n)

- **Local Outlier Factor** - Density deviation detection
  - Best for: Local density anomalies
  - Parameters: `n_neighbors`, `contamination`

**Feature Analysis:**
- **Random Forest** - Feature importance ranking
- **PCA** - Dimensionality reduction

## Use Cases

### 1. Pattern Clustering
Group similar automation patterns together:
```python
# Group similar device usage patterns
patterns = [
  [0.8, 0.2, 0.9],  # Evening usage
  [0.7, 0.3, 0.8],  # Evening usage
  [0.1, 0.9, 0.2],  # Morning usage
]
# Result: [0, 0, 1] - Two clusters identified
```

### 2. Anomaly Detection
Identify unusual device behavior:
```python
# Detect abnormal energy consumption
energy_data = [
  [100, 105, 98],   # Normal
  [102, 99, 101],   # Normal
  [500, 520, 510],  # Anomaly (spike)
]
# Result: [1, 1, -1] - Third entry is anomaly
```

### 3. Feature Importance
Rank which features matter most:
```python
# Which factors affect device failures?
features = [
  [age, usage, temp, humidity],
  ...
]
# Result: {"importance": [0.4, 0.3, 0.2, 0.1]}
# Age and usage are most important
```

## Safety Guardrails (2025)

- **Per-request normalization** – new `StandardScaler` instances are created for every operation to prevent cross-request contamination.
- **Thread offloading** – CPU-heavy sklearn calls now run in a background executor so the FastAPI event loop remains responsive.
- **Strict validation** – the API enforces 10MB payload limits, ≤1000 dimensions, ≤100 clusters, and ≤100 operations per batch before any processing occurs.
- **Time-limited execution** – clustering and anomaly detection calls time out (default 8s) to avoid runaway workloads on the NUC.
- **Restricted CORS** – only explicitly allowed dashboard origins can issue browser calls; override via `ML_ALLOWED_ORIGINS` if needed.
- **Sanitized errors** – responses never leak stack traces or sklearn internals; see logs for details.

## Performance

### Performance Targets

| Operation | Target | Acceptable | Investigation |
|-----------|--------|------------|---------------|
| KMeans (1000 pts) | <40ms | <100ms | >200ms |
| DBSCAN (1000 pts) | <60ms | <150ms | >300ms |
| Isolation Forest | <35ms | <100ms | >200ms |
| Batch (10 ops) | <150ms | <300ms | >500ms |

### Throughput

| Algorithm | Points/Second |
|-----------|---------------|
| KMeans | ~25,000 |
| DBSCAN | ~16,000 |
| Isolation Forest | ~30,000 |

## Development

### Testing

```bash
# Health check
curl http://localhost:8025/health

# Test clustering
curl -X POST http://localhost:8025/cluster \
  -H "Content-Type: application/json" \
  -d '{
    "data": [[1.0, 2.0], [1.5, 1.8], [5.0, 8.0], [5.5, 8.5]],
    "algorithm": "kmeans",
    "n_clusters": 2
  }'

# Test anomaly detection
curl -X POST http://localhost:8025/detect-anomalies \
  -H "Content-Type: application/json" \
  -d '{
    "data": [[1.0, 1.0], [1.2, 1.1], [10.0, 10.0]],
    "contamination": 0.1
  }'
```

## Monitoring

### Metrics Exposed

- Request latency per algorithm
- Algorithm usage distribution
- Batch processing efficiency
- Error rates
- Processing time histograms

## Dependencies

### Core

```
fastapi==0.121.2          # Web framework
uvicorn[standard]==0.38.0 # ASGI server
pydantic==2.12.4          # Data validation
pydantic-settings==2.12.0 # Settings management
```

### Machine Learning

```
scikit-learn==1.4.2       # ML algorithms
pandas==2.3.3             # Data analysis
numpy==2.3.4              # Numerical computing
scipy==1.16.3             # Scientific computing
```

### Utilities

```
httpx==0.27.2             # HTTP client
python-dotenv==1.2.1      # Environment variables
tenacity==8.2.3           # Retry logic
```

### Testing

```
pytest==8.3.3             # Testing framework
pytest-asyncio==0.23.0    # Async test support
```

## Troubleshooting

### Poor Clustering Results

**Symptoms:**
- Unexpected cluster assignments
- Too many/few clusters

**Solutions:**
- Normalize/scale input data
- Try different `n_clusters` values
- Switch algorithm (KMeans → DBSCAN)
- Visualize data to understand structure

### Too Many/Few Anomalies

**Symptoms:**
- Anomaly count doesn't match expectations

**Solutions:**
- Adjust `contamination` parameter
- Check data distribution
- Consider ensemble methods
- Verify data quality

### Slow Performance

**Symptoms:**
- Operations taking >200ms

**Solutions:**
- Reduce data dimensionality (PCA)
- Use batch processing
- Consider sampling for large datasets
- Check resource usage (CPU/memory)

## ML Service vs OpenVINO Service

| Use ML Service | Use OpenVINO Service |
|----------------|---------------------|
| Small datasets (<10k points) | Large datasets |
| Need interpretability | Need semantic understanding |
| Clustering/grouping tasks | Text/embedding tasks |
| Anomaly detection | Classification/ranking |
| Fast prototyping | Production inference |
| No training data available | Have pre-trained models |

## Related Documentation

- [AI Core Service](../ai-core-service/README.md) - Orchestrates ML operations
- [OpenVINO Service](../openvino-service/README.md) - Deep learning models
- [Automation Miner](../automation-miner/README.md) - Consumer of clustering
- [API Reference](../../docs/api/API_REFERENCE.md)
- [CLAUDE.md](../../CLAUDE.md)

## Support

- **Issues:** https://github.com/wtthornton/HomeIQ/issues
- **Documentation:** `/docs` directory
- **Health Check:** http://localhost:8025/health
- **API Docs:** http://localhost:8025/docs

## Version History

### 2.2.1 (December 09, 2025)
- Updated documentation to reflect port mapping (8020 internal, 8025 external)
- Clarified port usage for Docker vs local development
- Updated all API examples to use external port 8025

### 2.2 (November 15, 2025)
- Added strict payload validation (10MB cap, 1000 dimensions, 100 clusters) and enforced documented batch limits
- Routed CPU-bound sklearn workloads through thread executors with per-request scalers to eliminate memory leaks
- Restricted CORS origins, added operation timeouts, and sanitized error responses to prevent information disclosure
- Updated `/anomaly` and `/batch/process` documentation plus new environment variables for guardrails

### 2.1 (November 15, 2025)
- Updated documentation to 2025 standards
- Enhanced dependency documentation
- Added comprehensive troubleshooting
- Performance targets and metrics added
- Improved API endpoint documentation

### 2.0 (Initial Release)
- KMeans and DBSCAN clustering
- Isolation Forest anomaly detection
- Batch processing support
- FastAPI implementation

---

**Last Updated:** December 09, 2025
**Version:** 2.2.1
**Status:** Production Ready ✅
**Port:** 8020 (internal), 8025 (external)
