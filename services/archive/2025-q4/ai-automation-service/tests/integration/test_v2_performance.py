"""
Performance benchmarks for v2 API

Tests:
- Response time benchmarks
- Throughput measurements
- Memory usage (basic)
"""

import statistics
import time

import httpx
import pytest


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.performance
class TestV2Performance:
    """Performance benchmarks for v2 API"""

    @pytest.fixture
    async def api_client(self):
        """Create HTTP client for API testing"""
        base_url = "http://localhost:8018"
        async with httpx.AsyncClient(base_url=base_url, timeout=60.0) as client:
            yield client

    @pytest.fixture
    def auth_headers(self) -> dict[str, str]:
        """Authentication headers"""
        api_key = "hs_P3rU9kQ2xZp6vL1fYc7bN4sTqD8mA0wR"
        return {
            "Authorization": f"Bearer {api_key}",
            "X-HomeIQ-API-Key": api_key,
            "Content-Type": "application/json",
        }

    async def test_start_conversation_latency(self, api_client, auth_headers):
        """Benchmark conversation start latency"""
        latencies = []

        for _ in range(5):
            start_time = time.time()
            response = await api_client.post(
                "/api/v2/conversations",
                headers=auth_headers,
                json={
                    "query": "turn on office lights",
                    "user_id": "perf_test_user",
                },
            )
            end_time = time.time()

            assert response.status_code == 201
            latencies.append((end_time - start_time) * 1000)  # Convert to ms

        avg_latency = statistics.mean(latencies)
        p95_latency = statistics.quantiles(latencies, n=20)[18]  # 95th percentile

        print("\nStart Conversation Latency:")
        print(f"  Average: {avg_latency:.2f}ms")
        print(f"  P95: {p95_latency:.2f}ms")
        print(f"  Min: {min(latencies):.2f}ms")
        print(f"  Max: {max(latencies):.2f}ms")

        # Assert reasonable performance (adjust thresholds as needed)
        assert avg_latency < 5000, f"Average latency {avg_latency}ms exceeds 5s threshold"

    async def test_send_message_latency(self, api_client, auth_headers):
        """Benchmark message send latency"""
        # Start conversation
        conv_response = await api_client.post(
            "/api/v2/conversations",
            headers=auth_headers,
            json={
                "query": "turn on office lights",
                "user_id": "perf_test_user",
            },
        )
        conversation_id = conv_response.json()["conversation_id"]

        latencies = []

        for i in range(3):
            start_time = time.time()
            response = await api_client.post(
                f"/api/v2/conversations/{conversation_id}/message",
                headers=auth_headers,
                json={
                    "message": f"test message {i}",
                },
            )
            end_time = time.time()

            assert response.status_code == 200
            latencies.append((end_time - start_time) * 1000)  # Convert to ms

        avg_latency = statistics.mean(latencies)
        p95_latency = statistics.quantiles(latencies, n=20)[18] if len(latencies) > 1 else latencies[0]

        print("\nSend Message Latency:")
        print(f"  Average: {avg_latency:.2f}ms")
        print(f"  P95: {p95_latency:.2f}ms")
        print(f"  Min: {min(latencies):.2f}ms")
        print(f"  Max: {max(latencies):.2f}ms")

        # Assert reasonable performance
        assert avg_latency < 10000, f"Average latency {avg_latency}ms exceeds 10s threshold"

    async def test_concurrent_requests(self, api_client, auth_headers):
        """Test concurrent request handling"""
        import asyncio

        async def start_conversation():
            response = await api_client.post(
                "/api/v2/conversations",
                headers=auth_headers,
                json={
                    "query": "turn on office lights",
                    "user_id": "concurrent_test_user",
                },
            )
            return response.status_code

        # Start 10 concurrent requests
        start_time = time.time()
        tasks = [start_conversation() for _ in range(10)]
        results = await asyncio.gather(*tasks)
        end_time = time.time()

        total_time = (end_time - start_time) * 1000  # Convert to ms
        success_count = sum(1 for code in results if code == 201)

        print("\nConcurrent Requests (10):")
        print(f"  Total time: {total_time:.2f}ms")
        print(f"  Successful: {success_count}/10")
        print(f"  Average per request: {total_time / 10:.2f}ms")

        # All requests should succeed
        assert success_count == 10, f"Only {success_count}/10 requests succeeded"

    async def test_get_conversation_latency(self, api_client, auth_headers):
        """Benchmark conversation retrieval latency"""
        # Start conversation and send a few messages
        conv_response = await api_client.post(
            "/api/v2/conversations",
            headers=auth_headers,
            json={
                "query": "turn on office lights",
                "user_id": "perf_test_user",
            },
        )
        conversation_id = conv_response.json()["conversation_id"]

        # Send a few messages
        for i in range(3):
            await api_client.post(
                f"/api/v2/conversations/{conversation_id}/message",
                headers=auth_headers,
                json={"message": f"test {i}"},
            )

        # Benchmark retrieval
        latencies = []
        for _ in range(10):
            start_time = time.time()
            response = await api_client.get(
                f"/api/v2/conversations/{conversation_id}",
                headers=auth_headers,
            )
            end_time = time.time()

            assert response.status_code == 200
            latencies.append((end_time - start_time) * 1000)

        avg_latency = statistics.mean(latencies)

        print("\nGet Conversation Latency:")
        print(f"  Average: {avg_latency:.2f}ms")
        print(f"  Min: {min(latencies):.2f}ms")
        print(f"  Max: {max(latencies):.2f}ms")

        # Retrieval should be fast
        assert avg_latency < 1000, f"Average latency {avg_latency}ms exceeds 1s threshold"

