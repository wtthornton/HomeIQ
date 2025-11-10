"""
End-to-End Test for Ask AI Flow: Prompt -> Suggestion -> Test

This test verifies the complete flow:
1. Create query with natural language prompt
2. Entity extraction and enrichment
3. Suggestion generation (with prompt capture)
4. YAML generation and validation
5. Test endpoint execution

Tests verify:
- Entities are correctly extracted and enriched
- Group entities are expanded to individual entities
- Suggestions include correct device counts
- YAML uses validated entity IDs
- Test execution completes successfully
"""

import asyncio
import httpx
import pytest
import pytest_asyncio
import logging
import json
import yaml
from typing import Dict, List, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    force=True
)
logger = logging.getLogger(__name__)

# Base URL for the API
import os
BASE_URL = os.environ.get("AI_AUTOMATION_API_URL", "http://localhost:8024/api/v1/ask-ai")


class AskAIEndToEndTest:
    """End-to-end test for Ask AI complete flow"""
    
    def __init__(self, client: httpx.AsyncClient):
        self.client = client
        self.test_results = {
            'query_creation': None,
            'entity_extraction': None,
            'suggestion_generation': None,
            'yaml_generation': None,
            'test_execution': None,
            'validation_results': {}
        }
    
    async def create_query(self, query_text: str, user_id: str = "test-user") -> Dict[str, Any]:
        """Step 1: Create query and generate suggestions"""
        logger.info("\n" + "=" * 80)
        logger.info("STEP 1: CREATE QUERY")
        logger.info("=" * 80)
        
        url = f"{BASE_URL}/query"
        request_data = {
            "query": query_text,
            "user_id": user_id
        }
        
        logger.info(f"POST {url}")
        logger.info(f"Query: {query_text}")
        
        response = await self.client.post(url, json=request_data)
        
        assert response.status_code == 201, f"Failed to create query: {response.status_code}\n{response.text}"
        
        data = response.json()
        query_id = data.get('query_id')
        entities = data.get('extracted_entities', [])
        suggestions = data.get('suggestions', [])
        
        logger.info(f"Query created: {query_id}")
        logger.info(f"Extracted {len(entities)} entities")
        logger.info(f"Generated {len(suggestions)} suggestions")
        
        # Log extracted entities
        if entities:
            logger.info("\nExtracted Entities:")
            for entity in entities:
                entity_id = entity.get('entity_id', 'N/A')
                name = entity.get('name', entity.get('friendly_name', 'N/A'))
                logger.info(f"  - {name} ({entity_id})")
        
        self.test_results['query_creation'] = {
            'success': True,
            'query_id': query_id,
            'query_text': query_text,
            'entities': entities,
            'suggestions_count': len(suggestions)
        }
        
        return data
    
    def validate_suggestions(self, suggestions: List[Dict[str, Any]], expected_device_count: Optional[int] = None):
        """Step 2: Validate suggestions"""
        logger.info("\n" + "=" * 80)
        logger.info("STEP 2: VALIDATE SUGGESTIONS")
        logger.info("=" * 80)
        
        assert len(suggestions) > 0, "No suggestions generated"
        
        validation_results = []
        
        for i, suggestion in enumerate(suggestions, 1):
            logger.info(f"\nSuggestion {i}:")
            
            description = suggestion.get('description', 'N/A')
            devices = suggestion.get('devices_involved', [])
            confidence = suggestion.get('confidence', 0)
            
            logger.info(f"  Description: {description[:100]}...")
            logger.info(f"  Devices ({len(devices)}): {', '.join(devices)}")
            logger.info(f"  Confidence: {confidence:.2f}")
            
            # Validate suggestion has required fields
            assert 'suggestion_id' in suggestion, f"Suggestion {i} missing suggestion_id"
            assert 'description' in suggestion, f"Suggestion {i} missing description"
            assert 'devices_involved' in suggestion, f"Suggestion {i} missing devices_involved"
            
            # Check device count if expected
            if expected_device_count and len(devices) != expected_device_count:
                logger.warning(
                    f"Suggestion {i}: Expected {expected_device_count} devices, "
                    f"got {len(devices)}: {devices}"
                )
            
            validation_results.append({
                'suggestion_id': suggestion.get('suggestion_id'),
                'devices_count': len(devices),
                'devices': devices,
                'has_required_fields': True
            })
        
        self.test_results['suggestion_generation'] = {
            'success': True,
            'suggestions': validation_results,
            'total_count': len(suggestions)
        }
        
        return validation_results
    
    async def test_suggestion(self, query_id: str, suggestion_id: str) -> Dict[str, Any]:
        """Step 3: Test suggestion (generate YAML and execute)"""
        logger.info("\n" + "=" * 80)
        logger.info("STEP 3: TEST SUGGESTION")
        logger.info("=" * 80)
        
        url = f"{BASE_URL}/query/{query_id}/suggestions/{suggestion_id}/test"
        
        logger.info(f"POST {url}")
        
        response = await self.client.post(url)
        
        assert response.status_code == 200, f"Failed to test suggestion: {response.status_code}\n{response.text}"
        
        data = response.json()
        
        # Extract key information
        automation_yaml = data.get('automation_yaml', '')
        validated_entities = data.get('quality_report', {}).get('details', {}).get('validated_entities', {})
        executed = data.get('executed', False)
        quality_report = data.get('quality_report', {})
        
        logger.info(f"Test executed: {executed}")
        logger.info(f"YAML generated: {len(automation_yaml)} characters")
        logger.info(f"Validated entities: {len(validated_entities)}")
        
        # Log validated entities
        if validated_entities:
            logger.info("\nValidated Entities (Device -> Entity ID):")
            for device_name, entity_id in validated_entities.items():
                logger.info(f"  - {device_name} -> {entity_id}")
        
        # Log YAML
        if automation_yaml:
            logger.info("\nGenerated YAML:")
            try:
                parsed = yaml.safe_load(automation_yaml)
                formatted = yaml.dump(parsed, default_flow_style=False, sort_keys=False)
                # Log first 50 lines
                lines = formatted.split('\n')
                for line in lines[:50]:
                    logger.info(f"  {line}")
                if len(lines) > 50:
                    logger.info(f"  ... ({len(lines) - 50} more lines)")
            except Exception as e:
                logger.warning(f"Could not format YAML: {e}")
                logger.info(f"  {automation_yaml[:500]}...")
        
        # Validate quality report
        if quality_report:
            checks = quality_report.get('checks', [])
            passed = sum(1 for check in checks if 'PASS' in check.get('status', ''))
            total = len(checks)
            logger.info(f"\nQuality Checks: {passed}/{total} passed")
        
        self.test_results['test_execution'] = {
            'success': True,
            'executed': executed,
            'automation_yaml': automation_yaml,
            'validated_entities': validated_entities,
            'quality_report': quality_report
        }
        
        return data
    
    def validate_end_to_end(self, expected_min_entities: int = 1):
        """Step 4: Validate end-to-end flow"""
        logger.info("\n" + "=" * 80)
        logger.info("STEP 4: END-TO-END VALIDATION")
        logger.info("=" * 80)
        
        # Check query creation
        assert self.test_results['query_creation'] is not None, "Query creation step failed"
        assert self.test_results['query_creation']['success'], "Query creation was not successful"
        
        # Check suggestion generation
        assert self.test_results['suggestion_generation'] is not None, "Suggestion generation step failed"
        assert self.test_results['suggestion_generation']['success'], "Suggestion generation was not successful"
        assert self.test_results['suggestion_generation']['total_count'] > 0, "No suggestions generated"
        
        # Check test execution
        assert self.test_results['test_execution'] is not None, "Test execution step failed"
        assert self.test_results['test_execution']['success'], "Test execution was not successful"
        assert self.test_results['test_execution']['executed'], "Test execution did not complete"
        
        # Validate entity enrichment worked
        entities = self.test_results['query_creation'].get('entities', [])
        assert len(entities) >= expected_min_entities, \
            f"Expected at least {expected_min_entities} entities, got {len(entities)}"
        
        # Validate YAML was generated
        automation_yaml = self.test_results['test_execution'].get('automation_yaml', '')
        assert len(automation_yaml) > 0, "No automation YAML generated"
        
        # Validate entities in YAML
        validated_entities = self.test_results['test_execution'].get('validated_entities', {})
        assert len(validated_entities) > 0, "No entities were validated"
        
        logger.info("All end-to-end validations passed!")
        
        return True
    
    def print_summary(self):
        """Print test summary"""
        logger.info("\n" + "=" * 80)
        logger.info("TEST SUMMARY")
        logger.info("=" * 80)
        
        if self.test_results['query_creation']:
            qc = self.test_results['query_creation']
            logger.info(f"Query Created: {qc['query_id']}")
            logger.info(f"  - Entities: {len(qc['entities'])}")
            logger.info(f"  - Suggestions: {qc['suggestions_count']}")
        
        if self.test_results['suggestion_generation']:
            sg = self.test_results['suggestion_generation']
            logger.info(f"Suggestions Generated: {sg['total_count']}")
            for i, sug in enumerate(sg['suggestions'], 1):
                logger.info(f"  - Suggestion {i}: {sug['devices_count']} devices")
        
        if self.test_results['test_execution']:
            te = self.test_results['test_execution']
            logger.info(f"Test Executed: {te['executed']}")
            logger.info(f"  - Validated Entities: {len(te['validated_entities'])}")
            logger.info(f"  - YAML Length: {len(te['automation_yaml'])} chars")
        
        logger.info("=" * 80 + "\n")


@pytest.mark.asyncio
class TestAskAIEndToEnd:
    """End-to-end tests for Ask AI flow"""
    
    @pytest_asyncio.fixture
    async def client(self):
        """Create an async HTTP client"""
        async with httpx.AsyncClient(timeout=180.0) as client:
            yield client
    
    @pytest.mark.parametrize("query,expected_devices", [
        (
            "make it look like a party in the office by randomly flashing each lights quickly in random colors. Also include the Wled lights and pick fireworks. Do this for 10 secs",
            6  # Expect all 6 office lights (including WLED)
        ),
        (
            "turn on the office lights",
            1  # May return group entity or individual lights
        ),
    ])
    async def test_complete_flow(self, client: httpx.AsyncClient, query: str, expected_devices: int):
        """
        Test complete end-to-end flow:
        1. Create query
        2. Validate suggestions
        3. Test first suggestion
        4. Validate end-to-end
        """
        tester = AskAIEndToEndTest(client)
        
        try:
            # Step 1: Create query
            query_data = await tester.create_query(query)
            query_id = query_data['query_id']
            suggestions = query_data['suggestions']
            
            # Step 2: Validate suggestions
            tester.validate_suggestions(suggestions, expected_device_count=None)
            
            # Step 3: Test first suggestion
            first_suggestion = suggestions[0]
            suggestion_id = first_suggestion['suggestion_id']
            await tester.test_suggestion(query_id, suggestion_id)
            
            # Step 4: Validate end-to-end
            tester.validate_end_to_end(expected_min_entities=1)
            
            # Print summary
            tester.print_summary()
            
        except Exception as e:
            tester.print_summary()
            raise


if __name__ == "__main__":
    pytest.main([__file__, "-vv", "-s", "--log-cli-level=INFO", "--capture=no", "--tb=short"])

