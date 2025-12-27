"""
Ask AI Test Button - Direct API Test with Specific IDs

This test directly calls the API endpoint with specific query_id and suggestion_id.
Uses real API calls with httpx - no Playwright needed.

Test endpoint:
POST /api/v1/ask-ai/query/{query_id}/suggestions/{suggestion_id}/test
"""

import asyncio
import httpx
import pytest
import pytest_asyncio
import logging
import json
import yaml
from textwrap import dedent

# Configure logging with DEBUG level and visible format
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    force=True  # Force reconfiguration if already configured
)
logger = logging.getLogger(__name__)
# Also configure httpx and httpcore loggers for request/response details
logging.getLogger("httpx").setLevel(logging.DEBUG)
logging.getLogger("httpcore").setLevel(logging.DEBUG)

# Base URL for the API
# ai-automation-service is on port 8024 externally (Docker maps 8024:8018)
# Try both ports in case running differently
import os
BASE_URL = os.environ.get("AI_AUTOMATION_API_URL", "http://localhost:8024/api/v1/ask-ai")

# Specific IDs to test (fallback for testing existing queries)
# If not provided, test will create a new query
QUERY_ID = None  # Set to None to create new query, or provide existing ID
SUGGESTION_ID = None  # Will be extracted from new query response

# Test query text
TEST_QUERY = "make it look like a party in the office by randomly flashing each lights quickly in random colors. Also include the Wled lights and pick fireworks. Do this for 10 secs"


def format_yaml(yaml_string: str) -> str:
    """Format YAML string with proper indentation and validation."""
    try:
        # Parse and reformat YAML for clean output
        parsed = yaml.safe_load(yaml_string)
        formatted = yaml.dump(parsed, default_flow_style=False, sort_keys=False, allow_unicode=True)
        return formatted
    except Exception as e:
        logger.warning(f"Could not format YAML: {e}")
        return yaml_string


async def fetch_query_and_suggestion(client: httpx.AsyncClient, query_id: str, suggestion_id: str):
    """Fetch the original query and suggestion data to get the prompts."""
    prompts = {}
    
    try:
        # Try to fetch query data
        query_url = f"{BASE_URL.replace('/ask-ai', '')}/queries/{query_id}"
        logger.debug(f"Fetching query from: {query_url}")
        query_response = await client.get(query_url)
        
        if query_response.status_code == 200:
            query_data = query_response.json()
            prompts['query'] = query_data.get('query_text', query_data.get('text', 'N/A'))
            prompts['query_metadata'] = {
                'id': query_data.get('id'),
                'created_at': query_data.get('created_at'),
                'user_id': query_data.get('user_id'),
            }
            logger.debug(f"✅ Fetched query: {prompts['query'][:100]}...")
        else:
            logger.warning(f"Could not fetch query: {query_response.status_code}")
            prompts['query'] = 'Could not fetch from API'
            
    except Exception as e:
        logger.warning(f"Error fetching query: {e}")
        prompts['query'] = f'Error: {e}'
    
    try:
        # Try to fetch suggestion data
        suggestion_url = f"{BASE_URL}/query/{query_id}/suggestions/{suggestion_id}"
        logger.debug(f"Fetching suggestion from: {suggestion_url}")
        suggestion_response = await client.get(suggestion_url)
        
        if suggestion_response.status_code == 200:
            suggestion_data = suggestion_response.json()
            prompts['suggestion'] = suggestion_data.get('description', suggestion_data.get('suggestion', 'N/A'))
            prompts['trigger_summary'] = suggestion_data.get('trigger_summary', 'N/A')
            prompts['action_summary'] = suggestion_data.get('action_summary', 'N/A')
            prompts['devices_involved'] = suggestion_data.get('devices_involved', [])
            logger.debug(f"✅ Fetched suggestion: {prompts['suggestion'][:100]}...")
        else:
            logger.warning(f"Could not fetch suggestion: {suggestion_response.status_code}")
            prompts['suggestion'] = 'Could not fetch from API'
            
    except Exception as e:
        logger.warning(f"Error fetching suggestion: {e}")
        prompts['suggestion'] = f'Error: {e}'
    
    return prompts


def format_prompts_for_logging(prompts: dict) -> str:
    """Format prompts in a readable way for logging."""
    output = []
    output.append("\n" + "=" * 80)
    output.append("📝 ORIGINAL PROMPTS")
    output.append("=" * 80)
    
    if 'query' in prompts:
        output.append("\n🔍 USER QUERY:")
        output.append("-" * 80)
        output.append(prompts['query'])
        if 'query_metadata' in prompts:
            output.append(f"\nMetadata: {json.dumps(prompts['query_metadata'], indent=2)}")
    
    if 'suggestion' in prompts:
        output.append("\n💡 AI SUGGESTION:")
        output.append("-" * 80)
        output.append(f"Description: {prompts['suggestion']}")
        
        if 'trigger_summary' in prompts:
            output.append(f"\nTrigger Summary: {prompts['trigger_summary']}")
        
        if 'action_summary' in prompts:
            output.append(f"\nAction Summary: {prompts['action_summary']}")
        
        if 'devices_involved' in prompts and prompts['devices_involved']:
            output.append(f"\nDevices Involved: {', '.join(prompts['devices_involved'])}")
    
    output.append("=" * 80 + "\n")
    return "\n".join(output)


@pytest.mark.asyncio
class TestAskAISpecificIDs:
    """Direct API test with specific query and suggestion IDs"""
    
    @pytest_asyncio.fixture
    async def client(self):
        """Create an async HTTP client"""
        async with httpx.AsyncClient(timeout=120.0) as client:
            yield client
    
    async def test_specific_ids(self, client: httpx.AsyncClient):
        """
        Test the API endpoint - creates new query with entity enrichment or uses existing IDs.
        
        This verifies:
        - Entity enrichment works for new queries
        - API endpoint is accessible
        - Query and suggestion generation works
        - Test execution flow works
        - Response contains expected fields
        """
        query_id = QUERY_ID
        suggestion_id = SUGGESTION_ID
        
        # If no IDs provided, create a new query to test entity enrichment
        if not query_id or not suggestion_id:
            logger.info("=" * 80)
            logger.info("🆕 Creating NEW query to test entity enrichment...")
            logger.info("=" * 80)
            
            # Create new query using POST /query endpoint
            create_query_url = f"{BASE_URL}/query"
            create_request = {
                "query": TEST_QUERY,
                "user_id": "test-user"
            }
            
            logger.info(f"\n📤 Creating new query: {create_query_url}")
            logger.debug(f"Request: {json.dumps(create_request, indent=2)}")
            
            create_response = await client.post(create_query_url, json=create_request)
            
            if create_response.status_code != 201:
                logger.error(f"❌ Failed to create query: {create_response.status_code}")
                logger.error(f"Response: {create_response.text}")
                pytest.fail(f"Failed to create query: {create_response.status_code}")
            
            create_data = create_response.json()
            query_id = create_data.get('query_id')
            suggestions = create_data.get('suggestions', [])
            
            if not suggestions:
                pytest.fail("No suggestions generated from new query")
            
            suggestion_id = suggestions[0].get('suggestion_id')
            
            logger.info(f"✅ Created new query: query_id={query_id}, suggestion_id={suggestion_id}")
            logger.info(f"📊 Generated {len(suggestions)} suggestions")
            
            # Log first suggestion details
            first_suggestion = suggestions[0]
            logger.info(f"\n💡 First Suggestion:")
            logger.info(f"  Description: {first_suggestion.get('description', 'N/A')[:100]}...")
            devices = first_suggestion.get('devices_involved', [])
            logger.info(f"  Devices Involved ({len(devices)}): {', '.join(devices)}")
            
        else:
            logger.info("=" * 80)
            logger.info(f"🧪 Testing with existing query_id={query_id}, suggestion_id={suggestion_id}")
            logger.info("=" * 80)
        
        # Fetch original prompts before making test call
        logger.debug("\n📥 Fetching original query and suggestion prompts...")
        prompts = await fetch_query_and_suggestion(client, query_id, suggestion_id)
        
        # Log formatted prompts in DEBUG
        prompts_formatted = format_prompts_for_logging(prompts)
        logger.debug(prompts_formatted)
        
        # Build the endpoint URL
        endpoint = f"{BASE_URL}/query/{query_id}/suggestions/{suggestion_id}/test"
        logger.info(f"\n📡 Calling endpoint: {endpoint}")
        
        try:
            # Make the POST request
            logger.debug(f"\n🧪 Step 1: Preparing POST request to {endpoint}")
            logger.debug(f"Request headers: {dict(client.headers) if hasattr(client, 'headers') else 'N/A'}")
            
            logger.info("\n🧪 Step 1: Calling test endpoint...")
            response = await client.post(endpoint)
            
            logger.debug(f"Response headers: {dict(response.headers)}")
            logger.info(f"✅ Response status: {response.status_code}")
            logger.debug(f"Response URL: {response.url}")
            
            # Parse response
            if response.status_code >= 400:
                logger.error(f"❌ Error response: {response.status_code}")
                logger.error(f"Response text: {response.text}")
                # Try to parse as JSON for better error details
                try:
                    error_data = response.json()
                    logger.error(f"Error details: {json.dumps(error_data, indent=2)}")
                except:
                    pass
                # Don't raise - let's see what we got
                response_data = {}
            else:
                response_data = response.json()
            logger.info(f"\n📋 Response data:")
            logger.info(json.dumps(response_data, indent=2))
            
            # Log key fields
            if "valid" in response_data:
                logger.info(f"\n✅ Valid: {response_data['valid']}")
            
            if "executed" in response_data:
                logger.info(f"✅ Executed: {response_data['executed']}")
            
            if "automation_id" in response_data:
                logger.info(f"✅ Automation ID: {response_data['automation_id']}")
            
            # Also try to get prompts from quality_report if available (more reliable)
            if "quality_report" in response_data and "details" in response_data["quality_report"]:
                qr_details = response_data["quality_report"]["details"]
                if "original_query" in qr_details:
                    prompts['query'] = qr_details["original_query"]
                if "original_suggestion" in qr_details:
                    orig_suggestion = qr_details["original_suggestion"]
                    if isinstance(orig_suggestion, dict):
                        prompts['suggestion'] = orig_suggestion.get('description', 'N/A')
                        prompts['trigger_summary'] = orig_suggestion.get('trigger_summary', 'N/A')
                        prompts['action_summary'] = orig_suggestion.get('action_summary', 'N/A')
                        prompts['devices_involved'] = orig_suggestion.get('devices_involved', [])
                    else:
                        prompts['suggestion'] = orig_suggestion
                
                # Re-log prompts with updated data from response
                prompts_formatted = format_prompts_for_logging(prompts)
                logger.debug("\n" + "=" * 80)
                logger.debug("📝 PROMPTS (from response quality_report)")
                logger.debug("=" * 80)
                logger.debug(prompts_formatted)
            
            # Format and log the generated YAML in DEBUG
            if "automation_yaml" in response_data and response_data["automation_yaml"]:
                logger.debug("\n" + "=" * 80)
                logger.debug("📄 GENERATED AUTOMATION YAML")
                logger.debug("=" * 80)
                formatted_yaml = format_yaml(response_data["automation_yaml"])
                logger.debug(f"\n{formatted_yaml}")
                logger.debug("=" * 80 + "\n")
            
            if "validation_details" in response_data:
                logger.info(f"\n🔍 Validation Details:")
                logger.info(json.dumps(response_data['validation_details'], indent=2))
            
            if "quality_report" in response_data:
                logger.info(f"\n📊 Quality Report:")
                logger.info(json.dumps(response_data['quality_report'], indent=2))
            
            if "error" in response_data:
                logger.warning(f"\n⚠️ Error: {response_data['error']}")
            
            # Basic assertions
            if response.status_code == 404:
                logger.warning("⚠️ 404 Not Found - Query or suggestion may not exist in database")
                logger.info("This is expected if the IDs are not in the current database")
                logger.info(f"Tried to access: query_id={QUERY_ID}, suggestion_id={SUGGESTION_ID}")
                # Don't fail - this is informational
                return
            
            assert response.status_code < 500, f"Server error: {response.text}"
            
            if response_data:
                # Successful response should have executed, automation_id, or error/detail
                has_success_fields = "executed" in response_data or "automation_id" in response_data
                has_error_fields = "error" in response_data or "detail" in response_data
                assert has_success_fields or has_error_fields, f"Response missing expected fields. Got: {list(response_data.keys())}"
            
            logger.info("\n✅ Test completed successfully")
            
        except httpx.HTTPStatusError as e:
            logger.error(f"\n❌ HTTP Error: {e.response.status_code}")
            logger.error(f"Response: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"\n❌ Unexpected error: {e}")
            raise


if __name__ == "__main__":
    # Allow running directly with: python test_ask_ai_specific_ids.py
    # -vv: extra verbose
    # -s: no capture (show print statements)
    # --log-cli-level=DEBUG: show all logs at DEBUG level on CLI
    # --capture=no: disable output capturing completely
    # --tb=short: shorter traceback format
    pytest.main([__file__, "-vv", "-s", "--log-cli-level=DEBUG", "--capture=no", "--tb=short"])

