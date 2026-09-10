"""
ML Service Tests
Tests for the classical machine learning service
"""

import numpy as np
import pytest
from httpx import ASGITransport, AsyncClient

import src.main as main_module
from src.main import _startup_ml, app


class TestMLService:
    """Test suite for ML Service"""

    @pytest.fixture
    async def client(self):
        """In-process ASGI client.

        These used to point at http://localhost:8020, so the whole class
        failed whenever no ml-service container happened to be running —
        which is always, in CI. The managers are plain sklearn objects, so
        the app runs end to end in-process; _startup_ml() is what the app
        lifespan calls.

        The merged app's /health now also reports the shared OpenVINO
        model's readiness (TAP-7276); this suite only exercises the ml
        algorithms, so the OpenVINO check is stubbed ready rather than
        pulled in via a real (slow, network-dependent) model load.
        """
        await _startup_ml()
        old_manager = main_module.openvino_manager
        main_module.openvino_manager = type("_ReadyStub", (), {"is_ready": lambda self: True})()
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                yield client
        finally:
            main_module.openvino_manager = old_manager

    @pytest.fixture
    def sample_data(self):
        """Generate sample data for testing"""
        # Generate 2D data with 3 clusters
        np.random.seed(42)
        cluster1 = np.random.normal([0, 0], 0.5, (20, 2))
        cluster2 = np.random.normal([3, 3], 0.5, (20, 2))
        cluster3 = np.random.normal([-3, 3], 0.5, (20, 2))

        data = np.vstack([cluster1, cluster2, cluster3]).tolist()
        return data

    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Test health check endpoint"""
        response = await client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        # TAP-7276: unified StandardHealthCheck reports the merged service
        # identity, not the former ml-service; algorithm availability moved
        # to its own /algorithms/status endpoint (see test_algorithm_status).
        assert data["service"] == "model-server"

    @pytest.mark.asyncio
    async def test_algorithm_status(self, client):
        """Test algorithm status endpoint"""
        response = await client.get("/algorithms/status")
        assert response.status_code == 200

        data = response.json()
        assert "clustering" in data
        assert "anomaly_detection" in data
        assert "kmeans" in data["clustering"]
        assert "dbscan" in data["clustering"]
        assert "isolation_forest" in data["anomaly_detection"]

    @pytest.mark.asyncio
    async def test_kmeans_clustering(self, client, sample_data):
        """Test KMeans clustering"""
        response = await client.post(
            "/cluster",
            json={"data": sample_data, "algorithm": "kmeans", "n_clusters": 3},
        )

        assert response.status_code == 200
        data = response.json()

        assert "labels" in data
        assert "n_clusters" in data
        assert "algorithm" in data
        assert "processing_time" in data
        assert data["algorithm"] == "kmeans"
        assert data["n_clusters"] == 3
        assert len(data["labels"]) == len(sample_data)
        assert data["processing_time"] > 0

    @pytest.mark.asyncio
    async def test_dbscan_clustering(self, client, sample_data):
        """Test DBSCAN clustering"""
        response = await client.post(
            "/cluster",
            json={"data": sample_data, "algorithm": "dbscan", "eps": 0.5},
        )

        assert response.status_code == 200
        data = response.json()

        assert "labels" in data
        assert "n_clusters" in data
        assert "algorithm" in data
        assert "processing_time" in data
        assert data["algorithm"] == "dbscan"
        assert len(data["labels"]) == len(sample_data)
        assert data["processing_time"] > 0

    @pytest.mark.asyncio
    async def test_anomaly_detection(self, client, sample_data):
        """Test anomaly detection"""
        response = await client.post("/anomaly", json={"data": sample_data, "contamination": 0.1})

        assert response.status_code == 200
        data = response.json()

        assert "labels" in data
        assert "scores" in data
        assert "n_anomalies" in data
        assert "processing_time" in data
        assert len(data["labels"]) == len(sample_data)
        assert len(data["scores"]) == len(sample_data)
        assert data["n_anomalies"] >= 0
        assert data["processing_time"] > 0

    @pytest.mark.asyncio
    async def test_batch_processing(self, client, sample_data):
        """Test batch processing"""
        operations = [
            {
                "type": "cluster",
                "data": {"data": sample_data, "algorithm": "kmeans", "n_clusters": 3},
            },
            {"type": "anomaly", "data": {"data": sample_data, "contamination": 0.1}},
        ]

        response = await client.post("/batch/process", json={"operations": operations})

        assert response.status_code == 200
        data = response.json()

        assert "results" in data
        assert "processing_time" in data
        assert len(data["results"]) == 2
        assert data["processing_time"] > 0

        # Check clustering result
        cluster_result = data["results"][0]
        assert cluster_result["type"] == "cluster"
        assert "labels" in cluster_result
        assert "n_clusters" in cluster_result

        # Check anomaly result
        anomaly_result = data["results"][1]
        assert anomaly_result["type"] == "anomaly"
        assert "labels" in anomaly_result
        assert "n_anomalies" in anomaly_result

    @pytest.mark.asyncio
    async def test_error_handling(self, client):
        """Test error handling for invalid requests"""
        # Test with empty data
        response = await client.post("/cluster", json={"data": [], "algorithm": "kmeans", "n_clusters": 3})

        # Should handle empty input gracefully
        assert response.status_code in [200, 400]

    @pytest.mark.asyncio
    async def test_performance(self, client):
        """Test performance with larger datasets"""
        # Generate larger test data
        np.random.seed(42)
        large_data = np.random.normal(0, 1, (100, 2)).tolist()

        response = await client.post(
            "/cluster",
            json={"data": large_data, "algorithm": "kmeans", "n_clusters": 5},
        )

        assert response.status_code == 200
        data = response.json()

        # Should complete within reasonable time
        assert data["processing_time"] < 5.0  # Less than 5 seconds
        assert len(data["labels"]) == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
