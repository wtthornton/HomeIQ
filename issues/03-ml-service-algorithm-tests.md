# Issue #3: [P0] Add ML Service Algorithm Tests (Clustering & Anomaly Detection)

**Status:** 🟢 Open
**Priority:** 🔴 P0 - Critical
**Effort:** 6-8 hours
**Dependencies:** None

## Description

Implement comprehensive tests for ML Service (Port 8025→8020) covering clustering algorithms (DBSCAN, K-means), anomaly detection, and pattern recognition with known datasets.

**Current Status:** 1 test file (217 lines) vs 417 lines of source code (~52% coverage)

**Risk:** Machine learning algorithms lack validation, could produce incorrect results.

## Modern 2025 Patterns

✅ **Synthetic datasets** - Controlled test data with known properties
✅ **Property-based testing** - Validate algorithm properties
✅ **Benchmark datasets** - Standard ML evaluation sets
✅ **Statistical validation** - Chi-square, silhouette scores

## Acceptance Criteria

- [ ] Clustering algorithm correctness tests
- [ ] Anomaly detection accuracy tests
- [ ] Pattern recognition validation tests
- [ ] Algorithm property tests (convergence, consistency)
- [ ] Performance tests (<1s for 1000 points)
- [ ] Coverage >85%

## Code Templates

```python
# tests/test_clustering.py
import pytest
import numpy as np
from sklearn.datasets import make_blobs

@pytest.mark.asyncio
async def test_dbscan_identifies_clusters():
    """Test DBSCAN correctly identifies distinct clusters"""
    # Generate synthetic data with 3 clusters
    X, y_true = make_blobs(n_samples=300, centers=3, random_state=42)

    clusters = await ml_service.cluster_dbscan(X, eps=0.5, min_samples=5)

    # Should find 3 clusters (plus potential noise)
    unique_clusters = set(clusters) - {-1}  # Exclude noise
    assert len(unique_clusters) == 3

@pytest.mark.asyncio
async def test_kmeans_convergence():
    """Test K-means converges to stable clusters"""
    X, _ = make_blobs(n_samples=300, centers=4, random_state=42)

    # Run twice with same data
    clusters1 = await ml_service.cluster_kmeans(X, k=4, random_state=42)
    clusters2 = await ml_service.cluster_kmeans(X, k=4, random_state=42)

    # Should produce identical results with same random state
    assert np.array_equal(clusters1, clusters2)

@pytest.mark.asyncio
async def test_anomaly_detection_accuracy():
    """Test anomaly detection identifies outliers"""
    # Normal data
    normal = np.random.normal(0, 1, (100, 2))

    # Outliers
    outliers = np.array([[10, 10], [-10, -10], [10, -10]])

    X = np.vstack([normal, outliers])

    anomalies = await ml_service.detect_anomalies(X)

    # Should detect the 3 outliers
    assert len(anomalies) >= 3
    assert any(idx >= 100 for idx in anomalies)  # Outliers are at end
```
