"""Batch processing for ML Service — concurrent operation execution."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException

from .models import (
    AnomalyRequest,
    BatchAnomalyOperation,
    BatchClusterOperation,
    BatchOperationResult,
    ClusteringRequest,
)
from .validation import _validate_contamination, _validate_data_matrix

logger = logging.getLogger(__name__)


async def process_cluster_op(
    req: ClusteringRequest,
    clustering_manager: Any,
    run_cpu_bound: Any,
    max_clusters: int,
) -> BatchOperationResult:
    """Execute a single clustering operation within a batch."""
    if not clustering_manager:
        return BatchOperationResult(type="cluster", status="error", error="Clustering service not ready")
    num_points, _ = _validate_data_matrix(req.data)
    algorithm = req.algorithm.lower()
    if algorithm == "kmeans":
        if req.n_clusters is not None and (
            req.n_clusters < 2 or req.n_clusters > max_clusters or req.n_clusters > num_points
        ):
            return BatchOperationResult(
                type="cluster", status="error",
                error="Invalid n_clusters value supplied in batch operation.",
            )
        labels, n_clusters = await run_cpu_bound(
            clustering_manager.kmeans_cluster, req.data,
            n_clusters=req.n_clusters, max_clusters=max_clusters,
        )
    elif algorithm == "dbscan":
        if req.eps is not None and req.eps <= 0:
            return BatchOperationResult(type="cluster", status="error", error="eps must be > 0.")
        labels, n_clusters = await run_cpu_bound(
            clustering_manager.dbscan_cluster, req.data, eps=req.eps,
        )
    else:
        return BatchOperationResult(type="cluster", status="error", error=f"Unknown clustering algorithm: {algorithm}")
    return BatchOperationResult(type="cluster", status="success", algorithm=algorithm, labels=labels, n_clusters=n_clusters)


async def process_anomaly_op(
    req: AnomalyRequest,
    anomaly_manager: Any,
    run_cpu_bound: Any,
) -> BatchOperationResult:
    """Execute a single anomaly detection operation within a batch."""
    if not anomaly_manager:
        return BatchOperationResult(type="anomaly", status="error", error="Anomaly detection service not ready")
    _validate_data_matrix(req.data)
    _validate_contamination(req.contamination)
    labels, scores = await run_cpu_bound(
        anomaly_manager.detect_anomalies, req.data, contamination=req.contamination,
    )
    return BatchOperationResult(
        type="anomaly", status="success",
        labels=labels, scores=scores,
        n_anomalies=sum(1 for label in labels if label == -1),
    )


async def process_single_operation(
    operation: BatchClusterOperation | BatchAnomalyOperation,
    clustering_manager: Any,
    anomaly_manager: Any,
    run_cpu_bound: Any,
    max_clusters: int,
) -> BatchOperationResult:
    """Process a single batch operation, catching errors per-operation."""
    try:
        if operation.type == "cluster":
            return await process_cluster_op(operation.data, clustering_manager, run_cpu_bound, max_clusters)
        if operation.type == "anomaly":
            return await process_anomaly_op(operation.data, anomaly_manager, run_cpu_bound)  # type: ignore[arg-type]
        return BatchOperationResult(
            type=str(getattr(operation, "type", "unknown")),
            status="error", error="Unknown operation type",
        )
    except HTTPException as exc:
        return BatchOperationResult(
            type=operation.type, status="error",
            error=exc.detail if isinstance(exc.detail, str) else str(exc.detail),
        )
    except ValueError as exc:
        return BatchOperationResult(type=operation.type, status="error", error=str(exc))
    except Exception:
        logger.exception("Unexpected error processing batch operation")
        return BatchOperationResult(type=operation.type, status="error", error="Operation failed due to an internal error.")
