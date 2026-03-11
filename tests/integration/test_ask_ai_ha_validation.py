"""
Ask AI full flow with HA validation (Epic 53.1).

Integration test that:
1. Runs Ask AI: POST query -> suggestions -> POST test (or approve)
2. Asserts on all response fields (schema from Epic 53.2)
3. When response includes automation_id, verifies it exists via deploy/HA API (Epic 53.3)

Requires: Docker stack with ai-automation-service (port 8024); for HA validation
set DEPLOY_SERVICE_URL (e.g. http://localhost:8036) and/or HA_URL + HA_TOKEN.

Run: pytest tests/integration/test_ask_ai_ha_validation.py -v
      pytest tests/integration/test_ask_ai_ha_validation.py -v -m integration
Exclude from default: pytest -m "not integration"
"""

from __future__ import annotations

import json
import logging
import os

import httpx
import pytest
import pytest_asyncio

from tests.integration.helpers.ha_automation_validation import automation_exists

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Base URL for Ask AI (ai-query-service exposes ask-ai API on Docker port 8035)
ASK_AI_BASE = os.environ.get("ASK_AI_API_URL", "http://localhost:8035/api/v1/ask-ai").rstrip("/")
TEST_QUERY = "Turn on the office lights"
TEST_USER_ID = "epic53_integration"


# --- Schema assertions (Epic 53.2) ---


def assert_query_response(data: dict) -> None:
    """Assert POST /query response shape."""
    assert "query_id" in data, "Missing query_id"
    assert "original_query" in data, "Missing original_query"
    assert "suggestions" in data, "Missing suggestions"
    assert isinstance(data["suggestions"], list), "suggestions must be a list"
    if data["suggestions"]:
        s = data["suggestions"][0]
        assert "suggestion_id" in s, "Suggestion missing suggestion_id"
        assert "description" in s, "Suggestion missing description"


def assert_test_response(data: dict) -> None:
    """Assert POST .../test response shape (required fields)."""
    assert "suggestion_id" in data, "Missing suggestion_id"
    assert "query_id" in data, "Missing query_id"
    assert "executed" in data, "Missing executed"
    assert "command" in data, "Missing command"
    assert "original_description" in data, "Missing original_description"
    # Optional but assert type when present
    if "response" in data:
        assert isinstance(data["response"], (str, type(None))), "response must be str or null"
    if "message" in data:
        assert isinstance(data["message"], (str, type(None))), "message must be str or null"
    if "validation_details" in data and data["validation_details"] is not None:
        assert isinstance(data["validation_details"], dict), "validation_details must be dict"
    if "quality_report" in data and data["quality_report"] is not None:
        assert isinstance(data["quality_report"], dict), "quality_report must be dict"


def assert_approve_response(data: dict) -> None:
    """Assert POST .../approve response shape (required/optional)."""
    assert "suggestion_id" in data, "Missing suggestion_id"
    if "automation_id" in data and data["automation_id"]:
        assert isinstance(data["automation_id"], str), "automation_id must be string"
    if "automation_yaml" in data and data["automation_yaml"]:
        assert isinstance(data["automation_yaml"], str), "automation_yaml must be string"


@pytest.mark.integration
@pytest.mark.asyncio
class TestAskAIHaValidation:
    """Full Ask AI flow with response assertions and HA validation."""

    @pytest_asyncio.fixture
    async def client(self):
        async with httpx.AsyncClient(timeout=120.0) as client:
            yield client

    async def test_full_flow_query_suggestions_test_and_validate_ha(self, client: httpx.AsyncClient):
        """
        Run: query -> suggestions -> test; assert full response; validate automation in HA when id present.
        """
        logger.info("Step 1: POST /query")
        query_resp = await client.post(
            f"{ASK_AI_BASE}/query",
            json={"query": TEST_QUERY, "user_id": TEST_USER_ID},
        )
        assert query_resp.status_code in (200, 201), f"Query failed: {query_resp.text}"
        query_data = query_resp.json()
        assert_query_response(query_data)

        query_id = query_data["query_id"]
        suggestions = query_data["suggestions"]
        assert len(suggestions) > 0, "No suggestions"
        suggestion_id = suggestions[0]["suggestion_id"]
        logger.info("Step 2: POST .../test")
        test_resp = await client.post(
            f"{ASK_AI_BASE}/query/{query_id}/suggestions/{suggestion_id}/test"
        )
        assert test_resp.status_code == 200, f"Test failed: {test_resp.text}"
        test_data = test_resp.json()
        assert_test_response(test_data)

        logger.info("Step 3: HA validation when automation_id present")
        automation_id = test_data.get("automation_id")
        if automation_id:
            exists = await automation_exists(automation_id)
            assert exists, (
                f"automation_id {automation_id} from Ask AI test response not found in deploy/HA. "
                "Set DEPLOY_SERVICE_URL and/or HA_URL, HA_TOKEN."
            )
            logger.info("Automation verified in HA/deploy: %s", automation_id)
        else:
            logger.info("No automation_id in test response (quick test may not create automation); skip HA check")

    async def test_full_flow_approve_and_validate_ha(self, client: httpx.AsyncClient):
        """
        Run: query -> suggestions -> approve; assert response; validate automation_id in HA.
        """
        logger.info("Step 1: POST /query")
        query_resp = await client.post(
            f"{ASK_AI_BASE}/query",
            json={"query": "Turn on the office lights at sunset", "user_id": TEST_USER_ID},
        )
        assert query_resp.status_code in (200, 201), f"Query failed: {query_resp.text}"
        query_data = query_resp.json()
        assert_query_response(query_data)

        query_id = query_data["query_id"]
        suggestions = query_data["suggestions"]
        assert len(suggestions) > 0, "No suggestions"
        suggestion_id = suggestions[0]["suggestion_id"]
        logger.info("Step 2: POST .../approve")
        approve_resp = await client.post(
            f"{ASK_AI_BASE}/query/{query_id}/suggestions/{suggestion_id}/approve"
        )
        assert approve_resp.status_code == 200, f"Approve failed: {approve_resp.text}"
        approve_data = approve_resp.json()
        assert_approve_response(approve_data)

        automation_id = approve_data.get("automation_id")
        if automation_id:
            exists = await automation_exists(automation_id)
            assert exists, (
                f"automation_id {automation_id} from Ask AI approve not found in deploy/HA."
            )
            logger.info("Automation verified in HA/deploy: %s", automation_id)
        else:
            logger.info("No automation_id in approve response; skip HA check")
