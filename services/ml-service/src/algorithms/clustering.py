"""
Clustering Algorithms Manager
Provides KMeans and DBSCAN clustering for pattern detection
"""

import logging
from typing import List, Tuple, Optional

import numpy as np
from sklearn.cluster import DBSCAN, KMeans
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

class ClusteringManager:
    """
    Manages clustering algorithms for pattern detection.

    Heavy numerical operations remain synchronous and should be executed in a
    thread or process pool by the caller to avoid blocking the event loop.
    """

    def __init__(self):
        logger.info("ClusteringManager initialized")

    @staticmethod
    def _scale_features(data: List[List[float]]) -> np.ndarray:
        """
        Scale the provided data using a fresh StandardScaler per request.

        Using per-request scalers prevents data leakage between different calls
        and ensures garbage collection can reclaim memory when the call exits.
        """
        scaler = StandardScaler()
        return scaler.fit_transform(np.array(data, dtype=np.float64))

    def kmeans_cluster(
        self,
        data: List[List[float]],
        n_clusters: Optional[int] = None,
        max_clusters: int = 100,
    ) -> Tuple[List[int], int]:
        """
        Perform KMeans clustering.

        Args:
            data: List of data points to cluster
            n_clusters: Number of clusters (auto-detect if None)
            max_clusters: Upper bound for allowed clusters (safety cap)
        """
        if not data:
            return [], 0

        X_scaled = self._scale_features(data)

        if n_clusters is None:
            auto_clusters = max(2, len(data) // 10)
            n_clusters = auto_clusters or 2

        n_clusters = max(2, min(max_clusters, n_clusters, len(data)))

        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = kmeans.fit_predict(X_scaled)
        del kmeans

        logger.info(
            "KMeans clustering completed",
            extra={"clusters": n_clusters, "points": len(data)},
        )
        return labels.tolist(), n_clusters

    def dbscan_cluster(
        self,
        data: List[List[float]],
        eps: Optional[float] = None,
    ) -> Tuple[List[int], int]:
        """
        Perform DBSCAN clustering.

        Args:
            data: List of data points to cluster
            eps: Epsilon parameter (auto-detect if None)
        """
        if not data:
            return [], 0

        X_scaled = self._scale_features(data)

        if eps is None:
            if len(X_scaled) < 2:
                eps = 0.5
            else:
                from sklearn.neighbors import NearestNeighbors

                nbrs = NearestNeighbors(n_neighbors=2).fit(X_scaled)
                distances, _ = nbrs.kneighbors(X_scaled)
                eps = max(1e-3, 0.5 * float(np.mean(distances[:, 1])))

        dbscan = DBSCAN(eps=eps, min_samples=2)
        labels = dbscan.fit_predict(X_scaled)
        del dbscan

        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)

        logger.info(
            "DBSCAN clustering completed",
            extra={"clusters": n_clusters, "points": len(data), "eps": float(eps)},
        )
        return labels.tolist(), n_clusters
