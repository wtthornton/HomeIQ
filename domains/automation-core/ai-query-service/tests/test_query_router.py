"""
Unit tests for Query Service Router

Epic 39, Story 39.12: Query & Automation Service Testing
"""

import pytest
from httpx import AsyncClient
from pydantic import SecretStr
from src.api.query_router import _build_processor
from src.config import Settings, settings


class TestBuildProcessorOpenAIKey:
    """Regression: the OpenAI key must be both declared and unwrapped.

    ``openai_api_key`` was never declared on ``Settings`` -- BaseServiceSettings
    only carries ``data_api_key`` and ``influxdb_token`` -- and its model_config
    sets ``extra="ignore"``, so the environment variable was silently dropped
    and ``settings.openai_api_key`` raised AttributeError inside
    ``_build_processor``. The broad ``except Exception`` in ``process_query``
    swallowed it into a 500, so every query request failed with no usable signal.
    """

    @pytest.mark.unit
    def test_openai_api_key_is_a_declared_field(self):
        """extra="ignore" hides a missing declaration until attribute access."""
        assert "openai_api_key" in Settings.model_fields

    @pytest.mark.unit
    def test_build_processor_unwraps_secret_for_openai(self, monkeypatch):
        """The SDK must receive the real key, not the SecretStr wrapper."""
        captured = {}

        class FakeAsyncOpenAI:
            def __init__(self, api_key, timeout):
                captured["api_key"] = api_key
                captured["timeout"] = timeout

        monkeypatch.setattr("openai.AsyncOpenAI", FakeAsyncOpenAI)
        monkeypatch.setattr(settings, "openai_api_key", SecretStr("sk-real-value"))

        _build_processor()

        # str(SecretStr) is "**********", so passing the wrapper straight through
        # authenticates with the mask and silently degrades to keyword matching.
        assert captured["api_key"] == "sk-real-value"


class TestBuildProcessorDataApiKey:
    """Regression: the data-api key must reach the EntityExtractor.

    ``_build_processor()`` constructed ``EntityExtractor()`` bare, so
    ``CrossGroupClient`` carried ``auth_token=None``, sent no Authorization
    header, and every entity lookup against data-api silently degraded to
    zero extracted entities whenever data-api requires auth.
    """

    @pytest.mark.unit
    def test_build_processor_wires_data_api_key(self, monkeypatch):
        """The unwrapped key must land on the extractor's CrossGroupClient."""
        monkeypatch.setattr(settings, "data_api_key", SecretStr("data-key-123"))

        processor = _build_processor()

        assert processor.entity_extractor._cross_client._auth_token == "data-key-123"

    @pytest.mark.unit
    def test_build_processor_without_key_leaves_token_unset(self, monkeypatch):
        """No configured key stays None rather than becoming a masked string."""
        monkeypatch.setattr(settings, "data_api_key", None)

        processor = _build_processor()

        assert processor.entity_extractor._cross_client._auth_token is None


class TestQueryRouter:
    """Test suite for query router endpoints."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_query_endpoint_not_implemented(self, client: AsyncClient, sample_query_request):
        """Test query endpoint returns placeholder response (not fully implemented yet)."""
        response = await client.post("/api/v1/query", json=sample_query_request)
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "pending"
        assert "query_id" in data

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_suggestions_not_implemented(self, client: AsyncClient):
        """Test get suggestions endpoint returns placeholder response."""
        query_id = "test-query-123"
        response = await client.get(f"/api/v1/query/{query_id}/suggestions")
        assert response.status_code == 200
        data = response.json()
        assert data["query_id"] == query_id
        assert "suggestions" in data

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_refine_query_not_implemented(self, client: AsyncClient):
        """Test refine query endpoint returns placeholder response."""
        query_id = "test-query-123"
        response = await client.post(
            f"/api/v1/query/{query_id}/refine",
            json={"refinement": "add more details"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["query_id"] == query_id
        assert "status" in data

    @pytest.mark.performance
    @pytest.mark.latency
    @pytest.mark.asyncio
    async def test_query_latency_target(self, _client: AsyncClient, _sample_query_request):
        """Test query endpoint meets <500ms P95 latency target (when implemented)."""

        # Skip for now since endpoint is not fully implemented
        pytest.skip("Endpoint not yet fully implemented - latency test will be added after implementation")

        # TODO: When endpoint is implemented, test latency
        # start_time = time.time()
        # response = await client.post("/api/v1/query", json=sample_query_request)
        # latency_ms = (time.time() - start_time) * 1000
        # assert latency_ms < 500, f"Query latency {latency_ms}ms exceeds 500ms target"
        # assert response.status_code in [200, 201]

