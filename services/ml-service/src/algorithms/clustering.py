"""
Clustering Algorithms Manager
Provides KMeans and DBSCAN clustering for pattern detection
"""

import logging
import numpy as np
from typing import List, Tuple, Optional
from sklearn.cluster import KMeans, DBSCAN
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

class ClusteringManager:
    """
    Manages clustering algorithms for pattern detection
    """
    
    def __init__(self):
        self.scaler = StandardScaler()
        logger.info("ClusteringManager initialized")
    
    async def kmeans_cluster(self, data: List[List[float]], n_clusters: Optional[int] = None) -> Tuple[List[int], int]:
        """
        Perform KMeans clustering
        
        Args:
            data: List of data points to cluster
            n_clusters: Number of clusters (auto-detect if None)
        
        Returns:
            Tuple of (labels, n_clusters_found)
        """
        if not data:
            return [], 0
        
        # Convert to numpy array
        X = np.array(data)
        
        # Standardize features
        X_scaled = self.scaler.fit_transform(X)
        
        # Auto-detect number of clusters if not specified
        if n_clusters is None:
            n_clusters = min(8, max(2, len(data) // 10))
        
        # Perform KMeans clustering
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = kmeans.fit_predict(X_scaled)
        
        logger.info(f"KMeans clustering completed: {n_clusters} clusters, {len(data)} points")
        
        return labels.tolist(), n_clusters
    
    async def dbscan_cluster(self, data: List[List[float]], eps: Optional[float] = None) -> Tuple[List[int], int]:
        """
        Perform DBSCAN clustering
        
        Args:
            data: List of data points to cluster
            eps: Epsilon parameter (auto-detect if None)
        
        Returns:
            Tuple of (labels, n_clusters_found)
        """
        if not data:
            return [], 0
        
        # Convert to numpy array
        X = np.array(data)
        
        # Standardize features
        X_scaled = self.scaler.fit_transform(X)
        
        # Auto-detect epsilon if not specified
        if eps is None:
            # Use a simple heuristic: 0.5 * mean distance to nearest neighbor
            from sklearn.neighbors import NearestNeighbors
            nbrs = NearestNeighbors(n_neighbors=2).fit(X_scaled)
            distances, _ = nbrs.kneighbors(X_scaled)
            eps = 0.5 * np.mean(distances[:, 1])
        
        # Perform DBSCAN clustering
        dbscan = DBSCAN(eps=eps, min_samples=2)
        labels = dbscan.fit_predict(X_scaled)
        
        # Count clusters (excluding noise points labeled as -1)
        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        
        logger.info(f"DBSCAN clustering completed: {n_clusters} clusters, {len(data)} points, eps={eps:.3f}")
        
        return labels.tolist(), n_clusters
