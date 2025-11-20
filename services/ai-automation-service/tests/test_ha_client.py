"""
Tests for Home Assistant Client

Story AI4.1: HA Client Foundation
"""

import asyncio

import pytest
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase
from src.clients.ha_client import HomeAssistantClient


class TestHomeAssistantClient(AioHTTPTestCase):
    """
    Test suite for HomeAssistantClient
    
    Story AI4.1: Tests authentication, retry logic, error handling, and health checks
    """

    async def get_application(self):
        """
        Create mock HA API server for testing
        """
        async def health_endpoint(request):
            """Mock /api/ endpoint"""
            return web.json_response({"message": "API running."})

        async def config_endpoint(request):
            """Mock /api/config endpoint"""
            return web.json_response({
                "version": "2024.1.0",
                "location_name": "Home",
                "latitude": 36.1699,
                "longitude": -115.1398,
                "time_zone": "America/Los_Angeles"
            })

        async def states_endpoint(request):
            """Mock /api/states endpoint"""
            return web.json_response([
                {
                    "entity_id": "automation.morning_lights",
                    "state": "on",
                    "attributes": {"friendly_name": "Morning Lights"}
                },
                {
                    "entity_id": "automation.night_mode",
                    "state": "on",
                    "attributes": {"friendly_name": "Night Mode"}
                },
                {
                    "entity_id": "light.living_room",
                    "state": "off",
                    "attributes": {"friendly_name": "Living Room Light"}
                }
            ])

        async def automation_config_endpoint(request):
            """Mock /api/config/automation/config endpoint"""
            return web.json_response([
                {
                    "id": "morning_lights",
                    "alias": "Morning Lights",
                    "trigger": [
                        {
                            "platform": "sun",
                            "event": "sunrise"
                        }
                    ],
                    "action": [
                        {
                            "service": "light.turn_on",
                            "target": {"entity_id": "light.living_room"}
                        }
                    ]
                }
            ])

        async def server_error_endpoint(request):
            """Mock endpoint that returns 500 error"""
            return web.json_response({"error": "Internal Server Error"}, status=500)

        async def timeout_endpoint(request):
            """Mock endpoint that times out"""
            await asyncio.sleep(15)  # Longer than client timeout
            return web.json_response({"message": "OK"})

        app = web.Application()
        app.router.add_get('/api/', health_endpoint)
        app.router.add_get('/api/config', config_endpoint)
        app.router.add_get('/api/states', states_endpoint)
        app.router.add_get('/api/config/automation/config', automation_config_endpoint)
        app.router.add_get('/api/error', server_error_endpoint)
        app.router.add_get('/api/timeout', timeout_endpoint)
        return app

    async def test_initialization(self):
        """
        Test AC1: Client initialization with authentication
        """
        client = HomeAssistantClient(
            ha_url="http://test.local:8123",
            access_token="test_token_12345",
            max_retries=3,
            retry_delay=0.1,
            timeout=5
        )

        assert client.ha_url == "http://test.local:8123"
        assert client.access_token == "test_token_12345"
        assert client.headers["Authorization"] == "Bearer test_token_12345"
        assert client.max_retries == 3
        assert client.retry_delay == 0.1
        assert client.timeout == 5

    async def test_connection_success(self):
        """
        Test AC2: Successful connection and health check
        """
        server_url = f"http://127.0.0.1:{self.server.port}"
        client = HomeAssistantClient(
            ha_url=server_url,
            access_token="test_token",
            timeout=5
        )

        # Test connection
        result = await client.test_connection()
        assert result is True

        # Verify last health check was updated
        assert client._last_health_check is not None

        await client.close()

    async def test_get_version(self):
        """
        Test AC2: Version detection
        """
        server_url = f"http://127.0.0.1:{self.server.port}"
        client = HomeAssistantClient(
            ha_url=server_url,
            access_token="test_token",
            timeout=5
        )

        version_info = await client.get_version()

        assert version_info is not None
        assert version_info["version"] == "2024.1.0"
        assert version_info["location_name"] == "Home"
        assert "latitude" in version_info
        assert "longitude" in version_info

        await client.close()

    async def test_health_check(self):
        """
        Test AC2: Comprehensive health check
        """
        server_url = f"http://127.0.0.1:{self.server.port}"
        client = HomeAssistantClient(
            ha_url=server_url,
            access_token="test_token",
            timeout=5
        )

        is_healthy, status_info = await client.health_check()

        assert is_healthy is True
        assert status_info["connected"] is True
        assert status_info["url"] == server_url
        assert status_info["last_check"] is not None
        assert status_info["version_info"] is not None
        assert status_info["version_info"]["version"] == "2024.1.0"

        await client.close()

    async def test_list_automations(self):
        """
        Test automation listing
        """
        server_url = f"http://127.0.0.1:{self.server.port}"
        client = HomeAssistantClient(
            ha_url=server_url,
            access_token="test_token",
            timeout=5
        )

        automations = await client.list_automations()

        assert len(automations) == 2
        assert automations[0]["entity_id"] == "automation.morning_lights"
        assert automations[1]["entity_id"] == "automation.night_mode"

        await client.close()

    async def test_get_automations(self):
        """
        Test automation configuration retrieval
        """
        server_url = f"http://127.0.0.1:{self.server.port}"
        client = HomeAssistantClient(
            ha_url=server_url,
            access_token="test_token",
            timeout=5
        )

        configs = await client.get_automations()

        assert len(configs) == 1
        assert configs[0]["id"] == "morning_lights"
        assert configs[0]["alias"] == "Morning Lights"
        assert "trigger" in configs[0]
        assert "action" in configs[0]

        await client.close()

    async def test_connection_pooling(self):
        """
        Test AC2: Connection pooling and session reuse
        """
        server_url = f"http://127.0.0.1:{self.server.port}"
        client = HomeAssistantClient(
            ha_url=server_url,
            access_token="test_token",
            timeout=5
        )

        # Get session
        session1 = await client._get_session()
        assert session1 is not None
        assert not session1.closed

        # Get session again - should reuse same session
        session2 = await client._get_session()
        assert session2 is session1

        await client.close()
        assert session1.closed

    async def test_retry_on_server_error(self):
        """
        Test AC3: Retry logic on server errors with exponential backoff
        """
        server_url = f"http://127.0.0.1:{self.server.port}"
        client = HomeAssistantClient(
            ha_url=server_url,
            access_token="test_token",
            max_retries=3,
            retry_delay=0.1,  # Fast retry for testing
            timeout=5
        )

        # This should retry and eventually return the error response
        result = await client._retry_request('GET', '/api/error')

        assert result is not None
        assert result['status'] == 500

        await client.close()

    async def test_graceful_connection_failure(self):
        """
        Test AC3: Graceful handling of connection failures
        """
        # Use invalid URL
        client = HomeAssistantClient(
            ha_url="http://invalid.local:9999",
            access_token="test_token",
            max_retries=2,
            retry_delay=0.1,
            timeout=2
        )

        # Should handle connection failure gracefully
        result = await client.test_connection()
        assert result is False

        # Health check should also handle failure
        is_healthy, status_info = await client.health_check()
        assert is_healthy is False
        assert status_info["connected"] is False

        await client.close()

    async def test_session_cleanup(self):
        """
        Test AC3: Proper resource cleanup
        """
        server_url = f"http://127.0.0.1:{self.server.port}"
        client = HomeAssistantClient(
            ha_url=server_url,
            access_token="test_token",
            timeout=5
        )

        # Create session
        await client.test_connection()
        assert client._session is not None
        assert not client._session.closed

        # Close client
        await client.close()
        assert client._session.closed

    async def test_authentication_header(self):
        """
        Test AC1: Authentication header is properly set
        """
        client = HomeAssistantClient(
            ha_url="http://test.local:8123",
            access_token="my_secret_token"
        )

        assert client.headers["Authorization"] == "Bearer my_secret_token"
        assert client.headers["Content-Type"] == "application/json"


@pytest.mark.asyncio
async def test_invalid_url_handling():
    """
    Test AC3: Error handling for malformed URLs
    """
    client = HomeAssistantClient(
        ha_url="not_a_valid_url",
        access_token="test_token",
        max_retries=1,
        retry_delay=0.1,
        timeout=2
    )

    result = await client.test_connection()
    assert result is False

    await client.close()


@pytest.mark.asyncio
async def test_configuration_validation():
    """
    Test AC4: Configuration parameter validation
    """
    # Test with minimal config
    client1 = HomeAssistantClient(
        ha_url="http://test.local:8123",
        access_token="token"
    )
    assert client1.max_retries == 3  # Default
    assert client1.retry_delay == 1.0  # Default
    assert client1.timeout == 10  # Default

    # Test with custom config
    client2 = HomeAssistantClient(
        ha_url="http://test.local:8123",
        access_token="token",
        max_retries=5,
        retry_delay=2.0,
        timeout=30
    )
    assert client2.max_retries == 5
    assert client2.retry_delay == 2.0
    assert client2.timeout == 30

    await client1.close()
    await client2.close()


@pytest.mark.asyncio
async def test_url_normalization():
    """
    Test that URLs with trailing slashes are normalized
    """
    client = HomeAssistantClient(
        ha_url="http://test.local:8123/",  # With trailing slash
        access_token="token"
    )

    assert client.ha_url == "http://test.local:8123"  # Should be stripped

    await client.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

