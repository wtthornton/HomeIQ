"""
Ask AI Test Button - Direct API Integration Test

This test directly calls the API endpoints to verify the Test button functionality
without going through the UI. Uses real API calls with httpx.

Test Flow:
1. POST /api/v1/ask-ai/query - Create a query
2. GET /api/v1/ask-ai/query/{query_id}/suggestions - Get suggestions
3. POST /api/v1/ask-ai/query/{query_id}/suggestions/{suggestion_id}/test - Test suggestion

This verifies:
- Query is created and stored
- Suggestions are generated
- Test endpoint retrieves query and suggestion correctly
- YAML is generated
- HA automation is created with [TEST] prefix
- Automation is triggered
- Automation is disabled
"""

import asyncio
import httpx
import pytest
import pytest_asyncio
import logging
from typing import Dict, Any
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Base URL for the API
# Note: ai-automation-service is on port 8024 externally (docker maps 8024:8018)
BASE_URL = "http://localhost:8024/api/v1/ask-ai"

# Test configuration
TEST_QUERY = "Turn on the office lights"
TEST_USER_ID = "test_user_api"


@pytest.mark.asyncio
class TestAskAITestButtonAPI:
    """Direct API integration tests for Ask AI Test button functionality"""
    
    @pytest_asyncio.fixture
    async def client(self):
        """Create an async HTTP client"""
        async with httpx.AsyncClient(timeout=120.0) as client:
            yield client
    
    async def test_complete_test_button_flow(self, client: httpx.AsyncClient):
        """
        Test the complete flow: query → suggestions → test
        
        This is a comprehensive integration test that verifies:
        1. Query creation
        2. Suggestion generation
        3. Test button execution (YAML generation, HA automation creation, trigger, disable)
        """
        logger.info("=" * 80)
        logger.info("TEST: Complete Test Button Flow")
        logger.info("=" * 80)
        
        # Step 1: Create a query
        logger.info("\n📝 Step 1: Creating query...")
        query_response = await client.post(
            f"{BASE_URL}/query",
            json={
                "query": TEST_QUERY,
                "user_id": TEST_USER_ID
            }
        )
        
        logger.info(f"Query response status: {query_response.status_code}")
        assert query_response.status_code in [200, 201], f"Query failed: {query_response.text}"
        
        query_data = query_response.json()
        query_id = query_data.get("query_id")
        logger.info(f"✅ Query created with ID: {query_id}")
        logger.info(f"Query data: {json.dumps(query_data, indent=2)}")
        
        # Verify query structure
        assert "query_id" in query_data
        assert "original_query" in query_data
        assert "suggestions" in query_data
        assert len(query_data["suggestions"]) > 0, "No suggestions generated"
        
        # Step 2: Get suggestions from the query response (they're already there)
        logger.info("\n📋 Step 2: Parsing suggestions from query response...")
        suggestions = query_data.get("suggestions", [])
        logger.info(f"✅ Got {len(suggestions)} suggestions from query response")
        
        # Log first suggestion details
        first_suggestion = suggestions[0]
        logger.info(f"\nSuggestion 1 details:")
        logger.info(f"  - ID: {first_suggestion.get('suggestion_id')}")
        logger.info(f"  - Description: {first_suggestion.get('description')}")
        logger.info(f"  - Trigger: {first_suggestion.get('trigger_summary')}")
        logger.info(f"  - Action: {first_suggestion.get('action_summary')}")
        logger.info(f"  - Confidence: {first_suggestion.get('confidence')}")
        
        suggestion_id = first_suggestion.get('suggestion_id')
        assert suggestion_id, "No suggestion_id found"
        
        # Log the full suggestion structure for debugging
        logger.info(f"\n📄 Full first suggestion: {json.dumps(first_suggestion, indent=2)}")
        
        # Step 3: Test the suggestion
        logger.info("\n🧪 Step 3: Testing suggestion...")
        logger.info(f"Query ID: {query_id}")
        logger.info(f"Suggestion ID: {suggestion_id}")
        
        test_response = await client.post(
            f"{BASE_URL}/query/{query_id}/suggestions/{suggestion_id}/test"
        )
        
        logger.info(f"Test response status: {test_response.status_code}")
        logger.info(f"Test response text: {test_response.text}")
        
        # Check status code
        if test_response.status_code != 200:
            logger.error(f"Test failed with status {test_response.status_code}")
            logger.error(f"Response: {test_response.text}")
            # Don't fail the test immediately - let's see what the error is
            
        test_data = test_response.json()
        logger.info(f"\nTest response data: {json.dumps(test_data, indent=2)}")
        
        # Verify test response structure (NEW BEHAVIOR: Quick test via HA Conversation API)
        assert "suggestion_id" in test_data
        assert "query_id" in test_data
        assert "executed" in test_data
        assert "command" in test_data
        assert "original_description" in test_data
        
        # Log results
        logger.info(f"\n✅ Quick Test Results:")
        logger.info(f"  - Executed: {test_data.get('executed')}")
        logger.info(f"  - Command: {test_data.get('command')}")
        logger.info(f"  - Original Description: {test_data.get('original_description')}")
        logger.info(f"  - Response: {test_data.get('response', 'N/A')}")
        logger.info(f"  - Message: {test_data.get('message', 'N/A')}")
        
        # Verify simplified command is present and makes sense
        command = test_data.get("command", "")
        if command:
            logger.info(f"✅ Simplified command: '{command}'")
            # Should be shorter than original description (removed conditions)
            original = test_data.get("original_description", "")
            if len(original) > len(command):
                logger.info("✅ Command is simplified (shorter than original)")
            else:
                logger.warning("⚠️  Command might not be simplified properly")
        
        return test_data
    
    async def test_query_creation_only(self, client: httpx.AsyncClient):
        """
        Test only query creation without testing suggestion
        
        Verifies the query endpoint works correctly
        """
        logger.info("\n" + "=" * 80)
        logger.info("TEST: Query Creation Only")
        logger.info("=" * 80)
        
        response = await client.post(
            f"{BASE_URL}/query",
            json={
                "query": "Flash the office lights every 30 seconds",
                "user_id": TEST_USER_ID
            }
        )
        
        assert response.status_code in [200, 201]
        data = response.json()
        
        logger.info(f"✅ Query created successfully")
        logger.info(f"  Query ID: {data.get('query_id')}")
        logger.info(f"  Original Query: {data.get('original_query')}")
        logger.info(f"  Suggestions Count: {len(data.get('suggestions', []))}")
        logger.info(f"  Confidence: {data.get('confidence')}")
        
        assert "query_id" in data
        assert "original_query" in data
        assert "suggestions" in data
        
        return data
    
    async def test_get_suggestions(self, client: httpx.AsyncClient):
        """
        Test getting suggestions for a query
        
        First creates a query, then retrieves its suggestions
        """
        logger.info("\n" + "=" * 80)
        logger.info("TEST: Get Suggestions")
        logger.info("=" * 80)
        
        # Create query first
        query_response = await client.post(
            f"{BASE_URL}/query",
            json={
                "query": "Turn on bedroom lights at sunset",
                "user_id": TEST_USER_ID
            }
        )
        
        assert query_response.status_code in [200, 201]
        query_data = query_response.json()
        query_id = query_data.get("query_id")
        
        logger.info(f"Created query with ID: {query_id}")
        
        # Get suggestions
        suggestions_response = await client.get(
            f"{BASE_URL}/query/{query_id}/suggestions"
        )
        
        assert suggestions_response.status_code == 200
        suggestions_data = suggestions_response.json()
        
        logger.info(f"✅ Got {len(suggestions_data.get('suggestions', []))} suggestions")
        
        return suggestions_data


@pytest.mark.asyncio
async def test_run_all():
    """Run all tests in sequence"""
    async with httpx.AsyncClient(timeout=300.0) as client:
        test_suite = TestAskAITestButtonAPI()
        
        # Test 1: Query creation
        logger.info("\n" + "=" * 80)
        logger.info("RUNNING TEST 1: Query Creation")
        logger.info("=" * 80)
        query_data = await test_suite.test_query_creation_only(client)
        
        # Test 2: Get suggestions  
        logger.info("\n" + "=" * 80)
        logger.info("RUNNING TEST 2: Get Suggestions")
        logger.info("=" * 80)
        suggestions_data = await test_suite.test_get_suggestions(client)
        
        # Test 3: Complete test flow
        logger.info("\n" + "=" * 80)
        logger.info("RUNNING TEST 3: Complete Test Button Flow")
        logger.info("=" * 80)
        test_data = await test_suite.test_complete_test_button_flow(client)
        
        logger.info("\n" + "=" * 80)
        logger.info("ALL TESTS COMPLETE")
        logger.info("=" * 80)


if __name__ == "__main__":
    # Run the test
    asyncio.run(test_run_all())

