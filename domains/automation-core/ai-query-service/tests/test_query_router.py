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
    async def test_query_endpoint_processes_query(self, client: AsyncClient, sample_query_request):
        """POST /query persists a record and returns a completed response.

        Data-api is unreachable in tests, so entity extraction degrades to
        zero entities and suggestions fall back to keyword matching -- the
        endpoint must still complete rather than 500.
        """
        response = await client.post("/api/v1/query", json=sample_query_request)
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "complete"
        assert "query_id" in data
        assert isinstance(data["suggestions"], list)
        assert isinstance(data["entities"], list)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_suggestions_returns_stored_query(
        self, client: AsyncClient, sample_query_request
    ):
        """GET /query/{id}/suggestions returns suggestions for a stored query."""
        created = await client.post("/api/v1/query", json=sample_query_request)
        query_id = created.json()["query_id"]

        response = await client.get(f"/api/v1/query/{query_id}/suggestions")
        assert response.status_code == 200
        data = response.json()
        assert data["query_id"] == query_id
        assert "suggestions" in data
        assert data["total_count"] == len(data["suggestions"])

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_suggestions_unknown_query_returns_404(self, client: AsyncClient):
        """GET /query/{id}/suggestions for an unknown id is a 404."""
        response = await client.get("/api/v1/query/no-such-query/suggestions")
        assert response.status_code == 404

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_refine_query_reprocesses_stored_query(
        self, client: AsyncClient, sample_query_request
    ):
        """POST /query/{id}/refine re-processes the stored query with feedback."""
        created = await client.post("/api/v1/query", json=sample_query_request)
        query_id = created.json()["query_id"]

        response = await client.post(
            f"/api/v1/query/{query_id}/refine",
            json={"feedback": "only the ceiling lights"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["query_id"] == query_id
        assert data["status"] == "complete"

    @pytest.mark.performance
    @pytest.mark.latency
    @pytest.mark.asyncio
    async def test_query_latency_target(self):
        """Test query endpoint meets <500ms P95 latency target."""
        pytest.skip(
            "P95 latency is not meaningful against the in-process ASGI test "
            "transport - needs a deployed environment (perf suite)"
        )
