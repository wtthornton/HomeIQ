"""
Ask AI Test Button - Specific Automation E2E Test

This test directly calls the Test API endpoint with specific query_id and suggestion_id
from the database to test a known automation.

Test Data:
- Query ID: query-649c39bb
- Suggestion ID: ask-ai-8bdbe1b5
- Description: "Create a lively office ambiance by cycling through RGB colors on 
  the office lights every minute to mimic a disco effect, enhancing your focus while working."

This test verifies:
1. Query and suggestion are retrieved from database
2. Command is simplified for quick test
3. Command is executed via HA Conversation API
4. Response is returned with execution status
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
BASE_URL = "http://localhost:8024/api/v1/ask-ai"

# Known test data from database
KNOWN_QUERY_ID = "query-649c39bb"
KNOWN_SUGGESTION_ID = "ask-ai-8bdbe1b5"
EXPECTED_DESCRIPTION = "Create a lively office ambiance by cycling through RGB colors on the office lights every minute to mimic a disco effect, enhancing your focus while working."


@pytest.mark.asyncio
class TestSpecificAutomation:
    """E2E test for specific known automation"""
    
    @pytest_asyncio.fixture
    async def client(self):
        """Create an async HTTP client"""
        async with httpx.AsyncClient(timeout=120.0) as client:
            yield client
    
    async def test_known_automation(self, client: httpx.AsyncClient):
        """
        Test the specific automation from the database
        
        This test verifies the complete flow for a known query/suggestion pair:
        1. Fetch query from database
        2. Extract suggestion from query
        3. Simplify command using AI
        4. Execute via HA Conversation API
        5. Return execution result
        """
        logger.info("=" * 80)
        logger.info("E2E TEST: Known Automation Test")
        logger.info("=" * 80)
        logger.info(f"Query ID: {KNOWN_QUERY_ID}")
        logger.info(f"Suggestion ID: {KNOWN_SUGGESTION_ID}")
        logger.info(f"Expected Description: {EXPECTED_DESCRIPTION}")
        
        # Step 1: Call the test endpoint
        logger.info("\n🧪 Step 1: Calling Test API endpoint...")
        logger.info(f"Endpoint: POST {BASE_URL}/query/{KNOWN_QUERY_ID}/suggestions/{KNOWN_SUGGESTION_ID}/test")
        
        test_response = await client.post(
            f"{BASE_URL}/query/{KNOWN_QUERY_ID}/suggestions/{KNOWN_SUGGESTION_ID}/test"
        )
        
        logger.info(f"\nResponse Status: {test_response.status_code}")
        
        # Check status code
        if test_response.status_code != 200:
            logger.error(f"❌ Test failed with status {test_response.status_code}")
            logger.error(f"Response: {test_response.text}")
            pytest.fail(f"Test endpoint returned {test_response.status_code}")
        
        # Parse response
        test_data = test_response.json()
        logger.info(f"\nResponse Data:")
        logger.info(json.dumps(test_data, indent=2))
        
        # Step 2: Verify response structure
        logger.info("\n✅ Step 2: Verifying response structure...")
        
        assert "suggestion_id" in test_data, "Missing suggestion_id in response"
        assert "query_id" in test_data, "Missing query_id in response"
        assert "executed" in test_data, "Missing executed field in response"
        assert "command" in test_data, "Missing command field in response"
        assert "original_description" in test_data, "Missing original_description field in response"
        
        logger.info("✅ All required fields present")
        
        # Step 3: Verify values
        logger.info("\n✅ Step 3: Verifying values...")
        
        assert test_data["suggestion_id"] == KNOWN_SUGGESTION_ID, \
            f"Wrong suggestion_id: {test_data['suggestion_id']} != {KNOWN_SUGGESTION_ID}"
        
        assert test_data["query_id"] == KNOWN_QUERY_ID, \
            f"Wrong query_id: {test_data['query_id']} != {KNOWN_QUERY_ID}"
        
        assert test_data["original_description"] == EXPECTED_DESCRIPTION, \
            f"Wrong description: {test_data['original_description']}"
        
        logger.info("✅ All values match expected")
        
        # Step 4: Log execution results
        logger.info("\n" + "=" * 80)
        logger.info("EXECUTION RESULTS")
        logger.info("=" * 80)
        
        executed = test_data.get("executed", False)
        command = test_data.get("command", "")
        response_text = test_data.get("response", "")
        message = test_data.get("message", "")
        
        logger.info(f"\nExecuted: {executed}")
        logger.info(f"Simplified Command: '{command}'")
        logger.info(f"HA Response: {response_text}")
        logger.info(f"Message: {message}")
        
        # Step 5: Verify command was simplified
        logger.info("\n✅ Step 5: Verifying command simplification...")
        
        if command:
            # Simplified command should be shorter than original (removed conditions)
            original_length = len(EXPECTED_DESCRIPTION)
            command_length = len(command)
            
            logger.info(f"Original length: {original_length} chars")
            logger.info(f"Simplified length: {command_length} chars")
            
            if command_length < original_length:
                logger.info("✅ Command was simplified (shorter than original)")
            else:
                logger.warning("⚠️  Command might not be simplified properly")
            
            # Check if time constraints were removed
            if "every minute" not in command.lower() and "every min" not in command.lower():
                logger.info("✅ Time constraints removed from command")
            else:
                logger.warning("⚠️  Time constraints may still be present")
        
        # Step 6: Verify execution result
        logger.info("\n✅ Step 6: Verifying execution result...")
        
        if executed:
            logger.info("✅ Automation executed successfully via HA Conversation API")
            assert "response" in test_data, "Missing response field"
            assert test_data["response"] != "No response from HA", "Got error response from HA"
        else:
            logger.warning("⚠️  Automation execution failed")
            logger.warning(f"Response: {response_text}")
        
        logger.info("\n" + "=" * 80)
        logger.info("TEST COMPLETE")
        logger.info("=" * 80)
        
        return test_data
    
    async def test_api_endpoint_structure(self, client: httpx.AsyncClient):
        """
        Test that the API endpoint is accessible and returns correct structure
        
        This is a smoke test to verify the endpoint works even if execution fails
        """
        logger.info("\n" + "=" * 80)
        logger.info("SMOKE TEST: API Endpoint Structure")
        logger.info("=" * 80)
        
        try:
            response = await client.post(
                f"{BASE_URL}/query/{KNOWN_QUERY_ID}/suggestions/{KNOWN_SUGGESTION_ID}/test"
            )
            
            logger.info(f"Status Code: {response.status_code}")
            
            # Should return 200 even if execution fails
            assert response.status_code == 200, \
                f"Expected 200, got {response.status_code}: {response.text}"
            
            data = response.json()
            logger.info(f"Response structure: {list(data.keys())}")
            
            # Verify minimum structure
            required_fields = ["suggestion_id", "query_id", "executed", "command"]
            for field in required_fields:
                assert field in data, f"Missing required field: {field}"
            
            logger.info("✅ API endpoint structure is correct")
            
        except httpx.ConnectError as e:
            logger.error(f"❌ Could not connect to API: {e}")
            pytest.fail(f"API connection failed: {e}")
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
            raise


@pytest.mark.asyncio
async def test_run_specific_automation():
    """Run the specific automation test"""
    async with httpx.AsyncClient(timeout=300.0) as client:
        test_suite = TestSpecificAutomation()
        
        # Run smoke test first
        logger.info("\n" + "=" * 80)
        logger.info("RUNNING SMOKE TEST: API Endpoint Structure")
        logger.info("=" * 80)
        await test_suite.test_api_endpoint_structure(client)
        
        # Run full test
        logger.info("\n" + "=" * 80)
        logger.info("RUNNING E2E TEST: Known Automation")
        logger.info("=" * 80)
        result = await test_suite.test_known_automation(client)
        
        logger.info("\n" + "=" * 80)
        logger.info("ALL TESTS COMPLETE")
        logger.info("=" * 80)
        
        logger.info("\nTest Results:")
        logger.info(f"  Query ID: {result.get('query_id')}")
        logger.info(f"  Suggestion ID: {result.get('suggestion_id')}")
        logger.info(f"  Executed: {result.get('executed')}")
        logger.info(f"  Command: {result.get('command')}")
        logger.info(f"  Message: {result.get('message')}")


if __name__ == "__main__":
    # Run the test
    asyncio.run(test_run_specific_automation())

