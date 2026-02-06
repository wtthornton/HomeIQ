"""
Clustering Algorithms Manager
Provides KMeans and DBSCAN clustering for pattern detection
"""

import logging

import numpy as np
from sklearn.cluster import DBSCAN, KMeans

from .utils import scale_features

logger = logging.getLogger(__name__)


class ClusteringManager:
    """
    Manages clustering algorithms for pattern detection.

    Heavy numerical operations remain synchronous and should be executed in a
    thread or process pool by the caller to avoid blocking the event loop.
    """

    def __init__(self):
        logger.info("ClusteringManager initialized")

    def kmeans_cluster(
        self,
        data: list[list[float]],
        n_clusters: int | None = None,
        max_clusters: int = 100,
        n_init: int | None = None,
    ) -> tuple[list[int], int]:
        """
        Perform KMeans clustering.

        Args:
            data: List of data points to cluster
            n_clusters: Number of clusters (auto-detect if None)
            max_clusters: Upper bound for allowed clusters (safety cap)
            n_init: Number of KMeans initializations (adaptive if None)
        """
        if not data:
            return [], 0

        X_scaled = scale_features(data)

        if n_clusters is None:
            # sqrt heuristic capped at 20 for a sensible default
            n_clusters = max(2, min(int(len(data) ** 0.5), 20))

        n_clusters = max(2, min(max_clusters, n_clusters, len(data)))

        # Adaptive n_init: reduce for larger datasets to keep runtime bounded
        if n_init is None:
            n_init = 10 if len(data) <= 10_000 else 3

        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=n_init)
        labels = kmeans.fit_predict(X_scaled)

        logger.info(
            "KMeans clustering completed",
            extra={"clusters": n_clusters, "points": len(data)},
        )
        return labels.tolist(), n_clusters

    def dbscan_cluster(
        self,
        data: list[list[float]],
        eps: float | None = None,
    ) -> tuple[list[int], int]:
        """
        Perform DBSCAN clustering.

        Args:
            data: List of data points to cluster
            eps: Epsilon parameter (auto-detect if None)
        """
        if not data:
            return [], 0

        X_scaled = scale_features(data)

        min_samples = 2

        if eps is None:
            if len(X_scaled) < 2:
                eps = 0.5
            else:
                from sklearn.neighbors import NearestNeighbors

                k = min_samples + 1  # 3 neighbors for elbow heuristic
                nbrs = NearestNeighbors(n_neighbors=k).fit(X_scaled)
                distances, _ = nbrs.kneighbors(X_scaled)
                # Use the 90th percentile of k-th neighbor distances (elbow heuristic)
                eps = max(1e-3, float(np.percentile(distances[:, k - 1], 90)))

        dbscan = DBSCAN(eps=eps, min_samples=min_samples)
        labels = dbscan.fit_predict(X_scaled)

        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)

        logger.info(
            "DBSCAN clustering completed",
            extra={"clusters": n_clusters, "points": len(data), "eps": float(eps)},
        )
        return labels.tolist(), n_clusters
