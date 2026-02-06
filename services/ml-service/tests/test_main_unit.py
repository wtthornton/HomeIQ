"""
Unit tests for ML Service Main Application

Tests for main.py application initialization, validation functions, and API endpoints.
Covers: NaN/Inf validation, DBSCAN, batch processing, timeout paths, edge cases.
"""

import math

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport
from fastapi import HTTPException

from src.main import (
    app,
    _parse_allowed_origins,
    _estimate_payload_bytes,
    _validate_data_matrix,
    _validate_contamination,
    _run_cpu_bound,
    _check_rate_limit,
    _rate_limit_store,
    BatchClusterOperation,
    BatchAnomalyOperation,
    ClusteringRequest,
    AnomalyRequest,
)


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------

class TestHelperFunctions:
    """Test suite for helper functions."""

    def test_parse_allowed_origins_with_value(self):
        """Test parsing allowed origins with value."""
        result = _parse_allowed_origins("http://example.com,http://test.com")
        assert result == ["http://example.com", "http://test.com"]

    def test_parse_allowed_origins_with_whitespace(self):
        """Test parsing allowed origins with whitespace."""
        result = _parse_allowed_origins(" http://example.com , http://test.com ")
        assert result == ["http://example.com", "http://test.com"]

    def test_parse_allowed_origins_none(self):
        """Test parsing allowed origins with None."""
        result = _parse_allowed_origins(None)
        assert len(result) > 0  # Should return default

    def test_parse_allowed_origins_empty(self):
        """Test parsing allowed origins with empty string."""
        result = _parse_allowed_origins("")
        assert len(result) > 0  # Should return default

    def test_estimate_payload_bytes(self):
        """Test payload size estimation."""
        result = _estimate_payload_bytes(100, 10)
        assert result == 100 * 10 * 8  # 8000 bytes


# ---------------------------------------------------------------------------
# Data validation tests
# ---------------------------------------------------------------------------

class TestDataValidation:
    """Test suite for _validate_data_matrix."""

    def test_validate_data_matrix_valid(self):
        """Test validation of valid data matrix."""
        data = [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]]
        num_points, num_dimensions = _validate_data_matrix(data)
        assert num_points == 3
        assert num_dimensions == 2

    def test_validate_data_matrix_with_integers(self):
        """Test that integer values are accepted."""
        data = [[1, 2], [3, 4]]
        num_points, num_dimensions = _validate_data_matrix(data)
        assert num_points == 2
        assert num_dimensions == 2

    def test_validate_data_matrix_empty(self):
        """Test validation of empty data matrix."""
        with pytest.raises(ValueError, match="at least one row"):
            _validate_data_matrix([])

    def test_validate_data_matrix_none(self):
        """Test validation of None data."""
        with pytest.raises(ValueError, match="at least one row"):
            _validate_data_matrix(None)

    def test_validate_data_matrix_empty_row(self):
        """Test validation of data matrix with empty row."""
        with pytest.raises(ValueError, match="at least one feature"):
            _validate_data_matrix([[]])

    def test_validate_data_matrix_inconsistent_rows(self):
        """Test validation of data matrix with inconsistent row lengths."""
        data = [[1.0, 2.0], [3.0, 4.0, 5.0]]
        with pytest.raises(ValueError, match="same number of features"):
            _validate_data_matrix(data)

    def test_validate_data_matrix_non_numeric(self):
        """Test validation of data matrix with non-numeric values."""
        data = [[1.0, 2.0], ["invalid", 4.0]]
        with pytest.raises(ValueError, match="must be numbers"):
            _validate_data_matrix(data)

    def test_validate_data_matrix_nan(self):
        """CRITICAL-1: NaN values must be rejected."""
        data = [[1.0, float("nan")], [3.0, 4.0]]
        with pytest.raises(ValueError, match="NaN or Inf"):
            _validate_data_matrix(data)

    def test_validate_data_matrix_inf(self):
        """CRITICAL-1: Inf values must be rejected."""
        data = [[1.0, float("inf")], [3.0, 4.0]]
        with pytest.raises(ValueError, match="NaN or Inf"):
            _validate_data_matrix(data)

    def test_validate_data_matrix_negative_inf(self):
        """CRITICAL-1: Negative Inf values must be rejected."""
        data = [[1.0, float("-inf")], [3.0, 4.0]]
        with pytest.raises(ValueError, match="NaN or Inf"):
            _validate_data_matrix(data)

    def test_validate_data_matrix_single_point(self):
        """Edge case: single data point should be valid."""
        data = [[1.0, 2.0]]
        num_points, num_dimensions = _validate_data_matrix(data)
        assert num_points == 1
        assert num_dimensions == 2

    def test_validate_data_matrix_single_dimension(self):
        """Edge case: single dimension data should be valid."""
        data = [[1.0], [2.0], [3.0]]
        num_points, num_dimensions = _validate_data_matrix(data)
        assert num_points == 3
        assert num_dimensions == 1

    def test_validate_data_matrix_all_identical_points(self):
        """Edge case: all identical points should be valid."""
        data = [[1.0, 1.0]] * 10
        num_points, _ = _validate_data_matrix(data)
        assert num_points == 10

    def test_validate_contamination_valid(self):
        """Test validation of valid contamination value."""
        _validate_contamination(0.1)  # Should not raise

    def test_validate_contamination_too_low(self):
        """Test validation of contamination value too low."""
        with pytest.raises(ValueError, match="between 0 and 0.5"):
            _validate_contamination(0.0)

    def test_validate_contamination_too_high(self):
        """Test validation of contamination value too high."""
        with pytest.raises(ValueError, match="between 0 and 0.5"):
            _validate_contamination(0.5)

    def test_validate_contamination_negative(self):
        """Test validation of negative contamination value."""
        with pytest.raises(ValueError, match="between 0 and 0.5"):
            _validate_contamination(-0.1)

    @pytest.mark.asyncio
    async def test_run_cpu_bound(self):
        """Test running CPU-bound function."""
        def cpu_func(x, y):
            return x + y

        result = await _run_cpu_bound(cpu_func, 2, 3)
        assert result == 5

    @pytest.mark.asyncio
    async def test_run_cpu_bound_timeout(self):
        """Test that CPU-bound function times out correctly."""
        import time as time_mod

        def slow_func():
            time_mod.sleep(30)
            return "done"

        with patch("src.main.ALGORITHM_TIMEOUT_SECONDS", 0.1):
            with pytest.raises(HTTPException) as exc_info:
                await _run_cpu_bound(slow_func)
            assert exc_info.value.status_code == 504


# ---------------------------------------------------------------------------
# Rate limiting tests
# ---------------------------------------------------------------------------

class TestRateLimiting:
    """Test suite for rate limiting."""

    def setup_method(self):
        """Clear rate limit store before each test."""
        _rate_limit_store.clear()

    def test_rate_limit_allows_requests(self):
        """Normal requests should be allowed."""
        assert _check_rate_limit("127.0.0.1") is True

    def test_rate_limit_blocks_excess(self):
        """Excess requests should be blocked."""
        with patch("src.main.RATE_LIMIT_MAX_REQUESTS", 3):
            assert _check_rate_limit("10.0.0.1") is True
            assert _check_rate_limit("10.0.0.1") is True
            assert _check_rate_limit("10.0.0.1") is True
            assert _check_rate_limit("10.0.0.1") is False

    def test_rate_limit_per_ip(self):
        """Rate limits should be per-IP."""
        with patch("src.main.RATE_LIMIT_MAX_REQUESTS", 1):
            assert _check_rate_limit("10.0.0.1") is True
            assert _check_rate_limit("10.0.0.2") is True
            assert _check_rate_limit("10.0.0.1") is False


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------

class TestAPIEndpoints:
    """Test suite for API endpoints."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_health_endpoint(self):
        """Test health endpoint."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["service"] == "ml-service"
            assert "algorithms_available" in data

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_ready_endpoint_not_initialized(self):
        """Test readiness endpoint when managers are not initialized."""
        import src.main as main_module
        old_cm = main_module.clustering_manager
        old_am = main_module.anomaly_manager
        main_module.clustering_manager = None
        main_module.anomaly_manager = None
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/ready")
                assert response.status_code == 503
        finally:
            main_module.clustering_manager = old_cm
            main_module.anomaly_manager = old_am

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_ready_endpoint_initialized(self):
        """Test readiness endpoint when managers are initialized."""
        import src.main as main_module
        old_cm = main_module.clustering_manager
        old_am = main_module.anomaly_manager
        main_module.clustering_manager = MagicMock()
        main_module.anomaly_manager = MagicMock()
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/ready")
                assert response.status_code == 200
                assert response.json()["status"] == "ready"
        finally:
            main_module.clustering_manager = old_cm
            main_module.anomaly_manager = old_am

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_algorithms_status_endpoint(self):
        """Test algorithms status endpoint."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/algorithms/status")
            assert response.status_code == 200
            data = response.json()
            assert "clustering" in data
            assert "anomaly_detection" in data

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_kmeans_clustering_endpoint(self):
        """Test KMeans clustering endpoint."""
        mock_manager = MagicMock()
        mock_manager.kmeans_cluster = MagicMock(return_value=([0, 0, 1, 1], 2))
        import src.main as main_module
        old_cm = main_module.clustering_manager
        main_module.clustering_manager = mock_manager
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/cluster",
                    json={
                        "data": [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0], [7.0, 8.0]],
                        "algorithm": "kmeans",
                        "n_clusters": 2,
                    },
                )
                assert response.status_code == 200
                data = response.json()
                assert data["n_clusters"] == 2
                assert len(data["labels"]) == 4
        finally:
            main_module.clustering_manager = old_cm

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_dbscan_clustering_endpoint(self):
        """Test DBSCAN clustering endpoint."""
        mock_manager = MagicMock()
        mock_manager.dbscan_cluster = MagicMock(return_value=([0, 0, 1, -1], 2))
        import src.main as main_module
        old_cm = main_module.clustering_manager
        main_module.clustering_manager = mock_manager
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/cluster",
                    json={
                        "data": [[1.0, 2.0], [1.1, 2.1], [5.0, 5.0], [100.0, 100.0]],
                        "algorithm": "dbscan",
                        "eps": 0.5,
                    },
                )
                assert response.status_code == 200
                data = response.json()
                assert data["algorithm"] == "dbscan"
        finally:
            main_module.clustering_manager = old_cm

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_kmeans_clustering_invalid_data(self):
        """Test KMeans clustering with invalid data."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/cluster",
                json={
                    "data": [],
                    "algorithm": "kmeans",
                    "n_clusters": 2,
                },
            )
            # Empty data returns 400 (validation error) or 503 if manager not initialized
            assert response.status_code in [400, 422, 500, 503]

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_cluster_unknown_algorithm(self):
        """Test clustering with unknown algorithm returns 400."""
        import src.main as main_module
        old_cm = main_module.clustering_manager
        main_module.clustering_manager = MagicMock()
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/cluster",
                    json={
                        "data": [[1.0, 2.0], [3.0, 4.0]],
                        "algorithm": "invalid_algo",
                    },
                )
                assert response.status_code == 400
        finally:
            main_module.clustering_manager = old_cm

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_cluster_nan_data_rejected(self):
        """CRITICAL-1: NaN in clustering request must be rejected."""
        import src.main as main_module
        old_cm = main_module.clustering_manager
        main_module.clustering_manager = MagicMock()
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/cluster",
                    json={
                        "data": [[1.0, float("nan")], [3.0, 4.0]],
                        "algorithm": "kmeans",
                    },
                )
                # JSON spec doesn't have NaN, so httpx may send null or the
                # server may reject it at the Pydantic layer. Either 400 or 422
                # is acceptable.
                assert response.status_code in [400, 422]
        finally:
            main_module.clustering_manager = old_cm

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_anomaly_detection_endpoint(self):
        """Test anomaly detection endpoint."""
        mock_manager = MagicMock()
        mock_manager.detect_anomalies = MagicMock(
            return_value=([1, 1, -1, 1], [0.1, 0.2, -0.5, 0.15])
        )
        import src.main as main_module
        old_am = main_module.anomaly_manager
        main_module.anomaly_manager = mock_manager
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/anomaly",
                    json={
                        "data": [[1.0, 2.0], [3.0, 4.0], [100.0, 200.0], [5.0, 6.0]],
                        "contamination": 0.1,
                    },
                )
                assert response.status_code == 200
                data = response.json()
                assert "labels" in data
                assert "scores" in data
                assert "n_anomalies" in data
        finally:
            main_module.anomaly_manager = old_am

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_anomaly_detection_invalid_contamination(self):
        """Test anomaly detection with invalid contamination."""
        import src.main as main_module
        old_am = main_module.anomaly_manager
        main_module.anomaly_manager = MagicMock()
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/anomaly",
                    json={
                        "data": [[1.0, 2.0], [3.0, 4.0]],
                        "contamination": 0.6,  # Invalid: > 0.5
                    },
                )
                assert response.status_code == 400
        finally:
            main_module.anomaly_manager = old_am

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_batch_processing_endpoint(self):
        """Test batch processing with typed operations."""
        mock_cm = MagicMock()
        mock_cm.kmeans_cluster = MagicMock(return_value=([0, 1], 2))
        mock_am = MagicMock()
        mock_am.detect_anomalies = MagicMock(return_value=([1, -1], [0.1, -0.5]))

        import src.main as main_module
        old_cm = main_module.clustering_manager
        old_am = main_module.anomaly_manager
        main_module.clustering_manager = mock_cm
        main_module.anomaly_manager = mock_am
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/batch/process",
                    json={
                        "operations": [
                            {
                                "type": "cluster",
                                "data": {
                                    "data": [[1.0, 2.0], [3.0, 4.0]],
                                    "algorithm": "kmeans",
                                    "n_clusters": 2,
                                },
                            },
                            {
                                "type": "anomaly",
                                "data": {
                                    "data": [[1.0, 2.0], [100.0, 200.0]],
                                    "contamination": 0.1,
                                },
                            },
                        ]
                    },
                )
                assert response.status_code == 200
                data = response.json()
                assert len(data["results"]) == 2
                assert data["results"][0]["type"] == "cluster"
                assert data["results"][1]["type"] == "anomaly"
        finally:
            main_module.clustering_manager = old_cm
            main_module.anomaly_manager = old_am

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_batch_mixed_success_failure(self):
        """MED-6: Batch with a mix of successful and failing operations."""
        mock_cm = MagicMock()
        mock_cm.kmeans_cluster = MagicMock(return_value=([0, 1], 2))

        import src.main as main_module
        old_cm = main_module.clustering_manager
        old_am = main_module.anomaly_manager
        main_module.clustering_manager = mock_cm
        main_module.anomaly_manager = None  # Force anomaly to fail
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/batch/process",
                    json={
                        "operations": [
                            {
                                "type": "cluster",
                                "data": {
                                    "data": [[1.0, 2.0], [3.0, 4.0]],
                                    "algorithm": "kmeans",
                                    "n_clusters": 2,
                                },
                            },
                            {
                                "type": "anomaly",
                                "data": {
                                    "data": [[1.0, 2.0], [100.0, 200.0]],
                                    "contamination": 0.1,
                                },
                            },
                        ]
                    },
                )
                # Batch should still return 200 with per-op results
                assert response.status_code == 200
                data = response.json()
                assert len(data["results"]) == 2
                assert data["results"][0]["status"] == "success"
                assert data["results"][1]["status"] == "error"
        finally:
            main_module.clustering_manager = old_cm
            main_module.anomaly_manager = old_am

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_request_id_header(self):
        """MED-3: Response should include X-Request-ID header."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")
            assert "x-request-id" in response.headers

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_request_id_passthrough(self):
        """MED-3: Custom X-Request-ID should be echoed back."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/health",
                headers={"X-Request-ID": "test-trace-id-123"},
            )
            assert response.headers.get("x-request-id") == "test-trace-id-123"


# ---------------------------------------------------------------------------
# Algorithm manager unit tests
# ---------------------------------------------------------------------------

class TestClusteringManager:
    """Direct unit tests for ClusteringManager."""

    def test_kmeans_basic(self):
        """Test basic KMeans clustering."""
        from src.algorithms.clustering import ClusteringManager

        manager = ClusteringManager()
        data = [[0.0, 0.0], [0.1, 0.1], [10.0, 10.0], [10.1, 10.1]]
        labels, n_clusters = manager.kmeans_cluster(data, n_clusters=2)
        assert len(labels) == 4
        assert n_clusters == 2
        # Points in the same cluster should have the same label
        assert labels[0] == labels[1]
        assert labels[2] == labels[3]
        assert labels[0] != labels[2]

    def test_kmeans_auto_clusters(self):
        """Test KMeans with auto-detected clusters (sqrt heuristic)."""
        from src.algorithms.clustering import ClusteringManager

        manager = ClusteringManager()
        data = [[float(i), float(i)] for i in range(25)]
        labels, n_clusters = manager.kmeans_cluster(data)
        assert n_clusters >= 2
        assert n_clusters <= 20
        assert len(labels) == 25

    def test_kmeans_empty_data(self):
        """Test KMeans with empty data."""
        from src.algorithms.clustering import ClusteringManager

        manager = ClusteringManager()
        labels, n_clusters = manager.kmeans_cluster([])
        assert labels == []
        assert n_clusters == 0

    def test_dbscan_basic(self):
        """Test basic DBSCAN clustering."""
        from src.algorithms.clustering import ClusteringManager

        manager = ClusteringManager()
        data = [[0.0, 0.0], [0.1, 0.1], [0.2, 0.2], [10.0, 10.0], [10.1, 10.1], [10.2, 10.2]]
        labels, n_clusters = manager.dbscan_cluster(data, eps=1.0)
        assert len(labels) == 6
        assert n_clusters >= 1

    def test_dbscan_auto_eps(self):
        """HIGH-5: Test DBSCAN with automatic epsilon detection."""
        from src.algorithms.clustering import ClusteringManager

        manager = ClusteringManager()
        data = [[0.0, 0.0], [0.1, 0.1], [0.2, 0.2], [10.0, 10.0], [10.1, 10.1], [10.2, 10.2]]
        labels, n_clusters = manager.dbscan_cluster(data)
        assert len(labels) == 6
        assert n_clusters >= 1

    def test_dbscan_empty_data(self):
        """Test DBSCAN with empty data."""
        from src.algorithms.clustering import ClusteringManager

        manager = ClusteringManager()
        labels, n_clusters = manager.dbscan_cluster([])
        assert labels == []
        assert n_clusters == 0

    def test_dbscan_single_point(self):
        """Edge case: DBSCAN with a single data point."""
        from src.algorithms.clustering import ClusteringManager

        manager = ClusteringManager()
        labels, n_clusters = manager.dbscan_cluster([[1.0, 2.0]])
        assert len(labels) == 1


class TestAnomalyDetectionManager:
    """Direct unit tests for AnomalyDetectionManager."""

    def test_anomaly_detection_basic(self):
        """Test basic anomaly detection."""
        from src.algorithms.anomaly_detection import AnomalyDetectionManager

        manager = AnomalyDetectionManager()
        # Normal cluster with one obvious outlier
        data = [[1.0, 1.0], [1.1, 0.9], [0.9, 1.1], [1.0, 1.0], [100.0, 100.0]]
        labels, scores = manager.detect_anomalies(data, contamination=0.2)
        assert len(labels) == 5
        assert len(scores) == 5
        # The outlier should be labeled -1
        assert labels[-1] == -1

    def test_anomaly_detection_empty(self):
        """Test anomaly detection with empty data."""
        from src.algorithms.anomaly_detection import AnomalyDetectionManager

        manager = AnomalyDetectionManager()
        labels, scores = manager.detect_anomalies([])
        assert labels == []
        assert scores == []

    def test_anomaly_detection_all_identical(self):
        """Edge case: all identical points."""
        from src.algorithms.anomaly_detection import AnomalyDetectionManager

        manager = AnomalyDetectionManager()
        data = [[1.0, 1.0]] * 20
        labels, scores = manager.detect_anomalies(data, contamination=0.1)
        assert len(labels) == 20
        assert len(scores) == 20
