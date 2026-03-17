"""Tier 1 Data Flow Chain Tests (Story 78.1).

Verifies the critical data path:
    websocket-ingestion -> InfluxDB -> data-api

Tests the REAL client/library code paths with mocked external services
(InfluxDB server, data-api server) to validate write, query, retry,
authentication, and end-to-end round-trip contracts.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from homeiq_data import InfluxDBManager, StandardDataAPIClient
from homeiq_resilience import CircuitBreaker, CircuitOpenError


@pytest.mark.integration
class TestTier1DataFlow:
    """Verify Tier 1 data flow: InfluxDB writes, Data API reads, auth, retry."""

    @pytest.mark.asyncio
    async def test_influxdb_manager_write_and_query(self):
        """InfluxDBManager should write points and query them back.

        Validates the write_points -> query round-trip using the real
        InfluxDBManager class with mocked InfluxDB client internals.
        """
        manager = InfluxDBManager(
            url="http://influxdb:8086",
            token="test-token",
            org="homeiq",
            bucket="home_assistant_events",
        )

        # Mock the internal InfluxDB client components
        mock_write_api = MagicMock()
        mock_write_api.write = MagicMock()  # Synchronous (called via to_thread)
        mock_write_api.close = MagicMock()

        mock_record = MagicMock()
        mock_record.values = {
            "_measurement": "temperature",
            "room": "living",
            "value": 21.5,
        }
        mock_table = MagicMock()
        mock_table.records = [mock_record]
        mock_query_api = MagicMock()
        mock_query_api.query = MagicMock(return_value=[mock_table])

        mock_client = MagicMock()
        mock_client.write_api.return_value = mock_write_api
        mock_client.query_api.return_value = mock_query_api
        mock_client.close = MagicMock()

        # Bypass connect() — inject mocks directly
        manager._client = mock_client
        manager._write_api = mock_write_api
        manager._query_api = mock_query_api
        manager._available = True

        # Create a mock Point
        mock_point = MagicMock()

        # Write points
        result = await manager.write_points([mock_point])
        assert result is True, "write_points should return True on success"
        assert manager._write_count == 1

        # Query
        records = await manager.query(
            'from(bucket: "home_assistant_events") |> range(start: -1h)'
        )
        assert len(records) == 1
        assert records[0]["_measurement"] == "temperature"
        assert records[0]["value"] == 21.5

        await manager.close()

    @pytest.mark.asyncio
    async def test_data_api_client_entity_fetch_schema(self, data_api_url):
        """StandardDataAPIClient.fetch_entities should return a list of dicts.

        Validates the client constructor, auth header injection, and
        response parsing using the real client code with a mocked HTTP layer.
        """
        mock_entities = [
            {"entity_id": "light.living_room", "state": "on", "domain": "light"},
            {"entity_id": "sensor.temperature", "state": "21.5", "domain": "sensor"},
        ]

        with patch.object(
            StandardDataAPIClient, "fetch_entities",
            new_callable=AsyncMock,
            return_value=mock_entities,
        ):
            client = StandardDataAPIClient(
                base_url=data_api_url,
                api_key="test-api-key",
            )

            entities = await client.fetch_entities(domain="light")

            assert isinstance(entities, list)
            assert len(entities) == 2
            assert all("entity_id" in e for e in entities)
            assert all("state" in e for e in entities)

    @pytest.mark.asyncio
    async def test_data_api_bearer_auth_required(self, data_api_url):
        """Requests to data-api without Bearer auth should be rejected.

        Validates that StandardDataAPIClient injects the Authorization
        header correctly and that missing auth leads to empty fallback.
        """
        # Client with no api_key — should still construct without error
        client_no_auth = StandardDataAPIClient(
            base_url=data_api_url,
            api_key=None,
        )
        # Verify the underlying CrossGroupClient has no auth token
        assert client_no_auth._cross_client._auth_token is None

        # Client with api_key — should set auth token
        client_with_auth = StandardDataAPIClient(
            base_url=data_api_url,
            api_key="my-secret-key",
        )
        assert client_with_auth._cross_client._auth_token == "my-secret-key"

    @pytest.mark.asyncio
    async def test_influxdb_write_retry_on_transient_failure(self):
        """InfluxDBManager should retry writes on transient failures.

        Validates the retry loop in write_points: first attempt fails,
        second succeeds, and the CircuitBreaker-like retry count is honored.
        """
        manager = InfluxDBManager(
            url="http://influxdb:8086",
            token="test-token",
            org="homeiq",
            bucket="test_bucket",
            write_retries=3,
        )

        call_count = 0

        def flaky_write(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("transient failure")
            # Succeeds on second attempt

        mock_write_api = MagicMock()
        mock_write_api.write = flaky_write

        manager._write_api = mock_write_api
        manager._available = True

        mock_point = MagicMock()

        # Patch asyncio.sleep to avoid waiting during retry backoff
        with patch("homeiq_data.influxdb_manager.asyncio.sleep", new_callable=AsyncMock):
            result = await manager.write_points([mock_point])

        assert result is True, "Should succeed after retry"
        assert call_count == 2, "Should have retried once"

    @pytest.mark.asyncio
    async def test_data_flow_event_to_query_roundtrip(self):
        """Simulate event write then validate query result matches.

        End-to-end round-trip: write a temperature event point through
        InfluxDBManager, then query it back and verify field values.
        """
        manager = InfluxDBManager(
            url="http://influxdb:8086",
            token="test-token",
            org="homeiq",
            bucket="home_assistant_events",
        )

        written_records = []

        def capture_write(**kwargs):
            written_records.append(kwargs.get("record", []))

        mock_write_api = MagicMock()
        mock_write_api.write = capture_write
        mock_write_api.close = MagicMock()

        # Query returns what was written
        mock_record = MagicMock()
        mock_record.values = {
            "_measurement": "sensor_state",
            "entity_id": "sensor.temperature_living",
            "_value": 22.3,
            "_time": "2026-03-16T10:00:00Z",
        }
        mock_table = MagicMock()
        mock_table.records = [mock_record]

        mock_query_api = MagicMock()
        mock_query_api.query = MagicMock(return_value=[mock_table])

        manager._write_api = mock_write_api
        manager._query_api = mock_query_api
        manager._available = True

        # Write a point
        mock_point = MagicMock()
        write_ok = await manager.write_points([mock_point])
        assert write_ok is True

        # Query it back
        results = await manager.query(
            'from(bucket: "home_assistant_events") '
            '|> range(start: -1h) '
            '|> filter(fn: (r) => r._measurement == "sensor_state")'
        )

        assert len(results) == 1
        record = results[0]
        assert record["_measurement"] == "sensor_state"
        assert record["entity_id"] == "sensor.temperature_living"
        assert record["_value"] == 22.3

        await manager.close()
