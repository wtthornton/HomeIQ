# ML Service

**Port:** 8020
**Purpose:** Classical machine learning algorithms for pattern detection
**Status:** Production Ready

## Overview

The ML Service provides classical machine learning algorithms for clustering, anomaly detection, and feature analysis. It complements the deep learning models in the OpenVINO service by offering traditional ML algorithms that are faster and more interpretable for certain tasks.

## Key Features

- **Clustering Algorithms**: KMeans, DBSCAN for pattern grouping
- **Anomaly Detection**: Isolation Forest for outlier detection
- **Feature Importance**: Random Forest for feature ranking
- **Batch Processing**: Efficient processing of multiple operations
- **No Pre-training Required**: Classical algorithms don't need model downloads
- **Fast Inference**: <100ms for most operations
- **Interpretable Results**: Understandable decision processes

## Supported Algorithms

### Clustering
- **KMeans**: Partition data into K clusters
- **DBSCAN**: Density-based clustering for arbitrary shapes

### Anomaly Detection
- **Isolation Forest**: Identify outliers in high-dimensional data
- **Local Outlier Factor**: Detect local density deviations

### Feature Analysis
- **Random Forest**: Feature importance ranking
- **Principal Component Analysis**: Dimensionality reduction

## API Endpoints

### Health Check
```
GET /health
```

### Clustering
```
POST /cluster
Body: {
  "data": [[1.0, 2.0], [1.5, 1.8], ...],
  "algorithm": "kmeans|dbscan",
  "n_clusters": 3,  // for KMeans
  "eps": 0.5        // for DBSCAN
}
Response: {
  "labels": [0, 0, 1, 2, ...],
  "n_clusters": 3,
  "algorithm": "kmeans",
  "processing_time": 0.045
}
```

### Anomaly Detection
```
POST /detect-anomalies
Body: {
  "data": [[1.0, 2.0], [1.5, 1.8], ...],
  "contamination": 0.1  // expected outlier proportion
}
Response: {
  "labels": [1, 1, -1, 1, ...],  // 1=normal, -1=anomaly
  "scores": [0.3, 0.2, 0.9, ...],
  "n_anomalies": 5,
  "processing_time": 0.032
}
```

### Batch Processing
```
POST /batch
Body: {
  "operations": [
    {"type": "cluster", "data": [...], "algorithm": "kmeans", "n_clusters": 3},
    {"type": "anomaly", "data": [...], "contamination": 0.1}
  ]
}
Response: {
  "results": [
    {"labels": [...], "n_clusters": 3},
    {"labels": [...], "n_anomalies": 5}
  ],
  "processing_time": 0.087
}
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8020` | Service port |
| `LOG_LEVEL` | `INFO` | Logging level |
| `MAX_BATCH_SIZE` | `100` | Maximum operations per batch request |

## Architecture

```
┌─────────────────┐
│   ML Service    │
│   (Port 8020)   │
└────────┬────────┘
         │
    ┌────┴────┬──────────┬──────────┐
    │         │          │          │
    ▼         ▼          ▼          ▼
┌─────────┐ ┌────────┐ ┌─────────┐ ┌──────┐
│KMeans   │ │DBSCAN  │ │Isolation│ │Random│
│Clustering│ │Cluster │ │Forest   │ │Forest│
└─────────┘ └────────┘ └─────────┘ └──────┘
```

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

## Development

### Running Locally
```bash
cd services/ml-service
docker-compose up --build
```

### Testing
```bash
# Health check
curl http://localhost:8020/health

# Clustering
curl -X POST http://localhost:8020/cluster \
  -H "Content-Type: application/json" \
  -d '{
    "data": [[1.0, 2.0], [1.5, 1.8], [5.0, 8.0], [5.5, 8.5]],
    "algorithm": "kmeans",
    "n_clusters": 2
  }'

# Anomaly detection
curl -X POST http://localhost:8020/detect-anomalies \
  -H "Content-Type: application/json" \
  -d '{
    "data": [[1.0, 1.0], [1.2, 1.1], [10.0, 10.0]],
    "contamination": 0.1
  }'
```

## Dependencies

- FastAPI (web framework)
- scikit-learn (ML algorithms)
- numpy (numerical computing)
- pydantic (data validation)

## Performance

| Operation | Latency | Throughput |
|-----------|---------|------------|
| KMeans (1000 points) | 20-40ms | ~25,000 points/sec |
| DBSCAN (1000 points) | 30-60ms | ~16,000 points/sec |
| Isolation Forest | 15-35ms | ~30,000 points/sec |
| Batch (10 ops) | 50-150ms | Varies |

## Algorithm Details

### KMeans
- **Best for**: Well-separated, spherical clusters
- **Parameters**: `n_clusters` (number of clusters)
- **Time complexity**: O(n * k * i) where n=points, k=clusters, i=iterations
- **Output**: Cluster labels (0 to k-1)

### DBSCAN
- **Best for**: Arbitrary shapes, noisy data
- **Parameters**: `eps` (neighborhood radius), `min_samples` (min points per cluster)
- **Time complexity**: O(n log n) with spatial indexing
- **Output**: Cluster labels (-1 for noise)

### Isolation Forest
- **Best for**: High-dimensional anomaly detection
- **Parameters**: `contamination` (expected outlier proportion)
- **Time complexity**: O(n log n)
- **Output**: Binary labels (1=normal, -1=anomaly) + anomaly scores

## Monitoring

Metrics exposed for:
- Request latency per algorithm
- Algorithm usage distribution
- Batch processing efficiency
- Error rates

## Related Services

- [AI Core Service](../ai-core-service/README.md) - Orchestrates ML operations
- [OpenVINO Service](../openvino-service/README.md) - Deep learning models
- [Automation Miner](../automation-miner/README.md) - Consumer of clustering

## When to Use ML Service vs OpenVINO Service

| Use ML Service | Use OpenVINO Service |
|----------------|---------------------|
| Small datasets (<10k points) | Large datasets |
| Need interpretability | Need semantic understanding |
| Clustering/grouping tasks | Text/embedding tasks |
| Anomaly detection | Classification/ranking |
| Fast prototyping | Production inference |
| No training data available | Have pre-trained models |

## Troubleshooting

### Poor clustering results
- Normalize/scale input data
- Try different `n_clusters` values
- Switch algorithm (KMeans → DBSCAN)
- Visualize data to understand structure

### Too many/few anomalies
- Adjust `contamination` parameter
- Check data distribution
- Consider ensemble methods

### Slow performance
- Reduce data dimensionality (PCA)
- Use batch processing
- Consider sampling for large datasets
