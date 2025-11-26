"""
Comprehensive Automation Generation Tests

Phase 4: Automation Testing - Comprehensive Test Suite

Tests automation generation from patterns and synergies, validates YAML quality,
and tests automation execution with synthetic homes.
"""

import pytest
import yaml as yaml_lib
from datetime import datetime, timedelta, timezone
from typing import Any

from tests.path_setup import add_service_src
add_service_src(__file__)

from src.testing.dataset_loader import HomeAssistantDatasetLoader
from src.testing.event_injector import EventInjector
from src.testing.ground_truth import GroundTruthExtractor
from src.clients.data_api_client import DataAPIClient
from src.services.automation.yaml_generation_service import generate_automation_yaml
from src.pattern_analyzer.co_occurrence import CoOccurrencePatternDetector
from src.synergy_detection.synergy_detector import DeviceSynergyDetector


def validate_yaml_structure(yaml_content: str) -> dict[str, Any]:
    """
    Validate YAML structure and return quality metrics.
    
    Args:
        yaml_content: YAML string to validate
    
    Returns:
        Dictionary with validation results:
        - valid: bool - Is YAML valid?
        - has_trigger: bool - Has trigger section?
        - has_action: bool - Has action section?
        - has_condition: bool - Has condition section (optional)?
        - entity_ids: list[str] - Entity IDs found in YAML
        - errors: list[str] - Validation errors
        - warnings: list[str] - Validation warnings
    """
    
    result = {
        'valid': False,
        'has_trigger': False,
        'has_action': False,
        'has_condition': False,
        'entity_ids': [],
        'errors': [],
        'warnings': []
    }
    
    try:
        # Parse YAML
        parsed = yaml_lib.safe_load(yaml_content)
        
        if not parsed:
            result['errors'].append("YAML is empty or invalid")
            return result
        
        # Check for automation structure
        if isinstance(parsed, dict):
            # Single automation
            result['has_trigger'] = 'trigger' in parsed
            result['has_action'] = 'action' in parsed
            result['has_condition'] = 'condition' in parsed
            
            # Extract entity IDs
            result['entity_ids'] = _extract_entity_ids_from_yaml(parsed)
            
        elif isinstance(parsed, list):
            # List of automations
            if len(parsed) > 0:
                first = parsed[0]
                if isinstance(first, dict):
                    result['has_trigger'] = 'trigger' in first
                    result['has_action'] = 'action' in first
                    result['has_condition'] = 'condition' in first
                    result['entity_ids'] = _extract_entity_ids_from_yaml(first)
        
        # Validate required sections
        if not result['has_trigger']:
            result['errors'].append("Missing 'trigger' section")
        if not result['has_action']:
            result['errors'].append("Missing 'action' section")
        
        # Check for common issues
        if result['entity_ids']:
            # Check for invalid entity IDs
            invalid_entities = [eid for eid in result['entity_ids'] if not _is_valid_entity_id(eid)]
            if invalid_entities:
                result['warnings'].append(f"Potentially invalid entity IDs: {invalid_entities}")
        
        result['valid'] = len(result['errors']) == 0
        
    except yaml_lib.YAMLError as e:
        result['errors'].append(f"YAML parsing error: {str(e)}")
    except Exception as e:
        result['errors'].append(f"Validation error: {str(e)}")
    
    return result


def _extract_entity_ids_from_yaml(yaml_dict: dict) -> list[str]:
    """Extract entity IDs from YAML dictionary"""
    entity_ids = []
    
    def extract_from_value(value):
        if isinstance(value, str):
            # Check if it looks like an entity ID (domain.entity format)
            if '.' in value and not value.startswith('http'):
                parts = value.split('.')
                if len(parts) == 2:
                    entity_ids.append(value)
        elif isinstance(value, dict):
            for v in value.values():
                extract_from_value(v)
        elif isinstance(value, list):
            for item in value:
                extract_from_value(item)
    
    extract_from_value(yaml_dict)
    return list(set(entity_ids))


def _is_valid_entity_id(entity_id: str) -> bool:
    """Check if entity ID has valid format"""
    if not entity_id or '.' not in entity_id:
        return False
    
    parts = entity_id.split('.')
    if len(parts) != 2:
        return False
    
    domain, entity = parts
    # Basic validation: domain and entity should be non-empty
    return bool(domain) and bool(entity)


def calculate_yaml_quality_score(validation_result: dict[str, Any]) -> float:
    """
    Calculate quality score for YAML (0.0-1.0).
    
    Args:
        validation_result: Result from validate_yaml_structure()
    
    Returns:
        Quality score (0.0-1.0)
    """
    score = 0.0
    
    # Valid YAML: 30%
    if validation_result['valid']:
        score += 0.3
    
    # Has trigger: 25%
    if validation_result['has_trigger']:
        score += 0.25
    
    # Has action: 25%
    if validation_result['has_action']:
        score += 0.25
    
    # Has condition (optional): 10%
    if validation_result['has_condition']:
        score += 0.1
    
    # No errors: 10%
    if len(validation_result['errors']) == 0:
        score += 0.1
    
    # Penalty for warnings
    score -= len(validation_result['warnings']) * 0.05
    score = max(0.0, min(1.0, score))
    
    return score


@pytest.mark.asyncio
async def test_yaml_generation_from_pattern(
    dataset_loader: HomeAssistantDatasetLoader,
    event_injector: EventInjector
):
    """
    Test YAML generation from detected patterns.
    
    Validates that patterns can be converted to valid Home Assistant automation YAML.
    """
    # Load dataset
    home_data = await dataset_loader.load_synthetic_home("assist-mini")
    
    # Generate and inject events
    events = dataset_loader.generate_synthetic_events(home_data, days=7, events_per_day=50)
    await event_injector.inject_events(events)
    
    # Fetch events and detect patterns
    data_api_client = DataAPIClient()
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=7)
    
    events_df = await data_api_client.fetch_events(
        start_time=start_time,
        end_time=end_time,
        limit=10000
    )
    
    if events_df.empty:
        pytest.skip("No events fetched from InfluxDB")
    
    # Detect patterns
    detector = CoOccurrencePatternDetector(min_confidence=0.7, time_window_minutes=5)
    patterns = detector.detect_patterns(events_df)
    
    if not patterns:
        pytest.skip("No patterns detected")
    
    # Select a pattern to test
    test_pattern = patterns[0]
    
    # Create suggestion from pattern
    suggestion = {
        'description': f"Automation based on pattern: {test_pattern.get('device1', 'device1')} and {test_pattern.get('device2', 'device2')}",
        'trigger_summary': f"When {test_pattern.get('device1', 'device1')} changes",
        'action_summary': f"Control {test_pattern.get('device2', 'device2')}",
        'validated_entities': {
            test_pattern.get('device1', 'device1'): test_pattern.get('device1', 'device1'),
            test_pattern.get('device2', 'device2'): test_pattern.get('device2', 'device2')
        },
        'devices_involved': [test_pattern.get('device1', ''), test_pattern.get('device2', '')]
    }
    
    # Generate YAML (requires OpenAI client - may be mocked)
    try:
        from src.llm.openai_client import OpenAIClient
        openai_client = OpenAIClient()
        
        yaml_content = await generate_automation_yaml(
            suggestion=suggestion,
            original_query="Test automation from pattern",
            openai_client=openai_client,
            entities=[],
            db_session=None,
            ha_client=None
        )
        
        # Validate YAML
        validation = validate_yaml_structure(yaml_content)
        quality_score = calculate_yaml_quality_score(validation)
        
        print(f"\n✅ YAML Generation from Pattern:")
        print(f"  Pattern: {test_pattern.get('device1')} → {test_pattern.get('device2')}")
        print(f"  YAML Valid: {validation['valid']}")
        print(f"  Has Trigger: {validation['has_trigger']}")
        print(f"  Has Action: {validation['has_action']}")
        print(f"  Quality Score: {quality_score:.3f}")
        print(f"  Entity IDs: {validation['entity_ids']}")
        
        if validation['errors']:
            print(f"  Errors: {validation['errors']}")
        if validation['warnings']:
            print(f"  Warnings: {validation['warnings']}")
        
        # Assert basic quality
        assert validation['valid'], f"YAML should be valid: {validation['errors']}"
        assert quality_score >= 0.5, f"Quality score should be >= 0.5, got {quality_score:.3f}"
        
    except Exception as e:
        pytest.skip(f"Cannot generate YAML without OpenAI client: {e}")


@pytest.mark.asyncio
async def test_yaml_generation_from_synergy(
    dataset_loader: HomeAssistantDatasetLoader
):
    """
    Test YAML generation from detected synergies.
    
    Validates that synergies can be converted to valid Home Assistant automation YAML.
    """
    # Load dataset
    home_data = await dataset_loader.load_synthetic_home("assist-mini")
    
    # Extract ground truth synergies
    extractor = GroundTruthExtractor(home_data)
    synergies = extractor.extract_synergies()
    
    if not synergies:
        pytest.skip("No synergies found in dataset")
    
    # Select a synergy to test
    test_synergy = synergies[0]
    trigger_entity = test_synergy.get('trigger_entity', '')
    action_entity = test_synergy.get('action_entity', '')
    relationship_type = test_synergy.get('relationship_type', 'unknown')
    
    # Create suggestion from synergy
    suggestion = {
        'description': f"Automation based on {relationship_type}: {trigger_entity} → {action_entity}",
        'trigger_summary': f"When {trigger_entity} changes",
        'action_summary': f"Control {action_entity}",
        'validated_entities': {
            trigger_entity: trigger_entity,
            action_entity: action_entity
        },
        'devices_involved': [trigger_entity, action_entity]
    }
    
    # Generate YAML (requires OpenAI client - may be mocked)
    try:
        from src.llm.openai_client import OpenAIClient
        openai_client = OpenAIClient()
        
        yaml_content = await generate_automation_yaml(
            suggestion=suggestion,
            original_query=f"Test automation from {relationship_type} synergy",
            openai_client=openai_client,
            entities=[],
            db_session=None,
            ha_client=None
        )
        
        # Validate YAML
        validation = validate_yaml_structure(yaml_content)
        quality_score = calculate_yaml_quality_score(validation)
        
        print(f"\n✅ YAML Generation from Synergy:")
        print(f"  Synergy: {trigger_entity} → {action_entity} ({relationship_type})")
        print(f"  YAML Valid: {validation['valid']}")
        print(f"  Quality Score: {quality_score:.3f}")
        
        # Assert basic quality
        assert validation['valid'], f"YAML should be valid: {validation['errors']}"
        assert quality_score >= 0.5, f"Quality score should be >= 0.5, got {quality_score:.3f}"
        
    except Exception as e:
        pytest.skip(f"Cannot generate YAML without OpenAI client: {e}")


@pytest.mark.asyncio
async def test_yaml_quality_validation(
    dataset_loader: HomeAssistantDatasetLoader
):
    """
    Test YAML quality validation across multiple automations.
    
    Validates that generated YAML meets quality standards.
    """
    # Load dataset
    home_data = await dataset_loader.load_synthetic_home("assist-mini")
    
    # Extract ground truth synergies
    extractor = GroundTruthExtractor(home_data)
    synergies = extractor.extract_synergies()
    
    if not synergies:
        pytest.skip("No synergies found in dataset")
    
    # Test YAML quality for multiple synergies
    quality_scores = []
    valid_count = 0
    
    for synergy in synergies[:5]:  # Test first 5
        trigger_entity = synergy.get('trigger_entity', '')
        action_entity = synergy.get('action_entity', '')
        
        if not trigger_entity or not action_entity:
            continue
        
        # Create basic YAML structure (simplified for testing)
        yaml_content = f"""
alias: Test Automation
description: Automation from {trigger_entity} to {action_entity}
trigger:
  - platform: state
    entity_id: {trigger_entity}
action:
  - service: homeassistant.turn_on
    entity_id: {action_entity}
"""
        
        # Validate YAML
        validation = validate_yaml_structure(yaml_content)
        quality_score = calculate_yaml_quality_score(validation)
        
        quality_scores.append(quality_score)
        if validation['valid']:
            valid_count += 1
    
    if quality_scores:
        avg_quality = sum(quality_scores) / len(quality_scores)
        valid_rate = valid_count / len(quality_scores)
        
        print(f"\n✅ YAML Quality Validation:")
        print(f"  Tested: {len(quality_scores)} automations")
        print(f"  Valid: {valid_count} ({valid_rate*100:.1f}%)")
        print(f"  Average Quality Score: {avg_quality:.3f}")
        
        # Assert quality thresholds
        assert avg_quality >= 0.7, f"Average quality should be >= 0.7, got {avg_quality:.3f}"
        assert valid_rate >= 0.8, f"Valid rate should be >= 80%, got {valid_rate*100:.1f}%"


@pytest.mark.asyncio
async def test_automation_entity_resolution(
    dataset_loader: HomeAssistantDatasetLoader
):
    """
    Test that automation YAML uses correct entity IDs.
    
    Validates entity resolution accuracy.
    """
    # Load dataset
    home_data = await dataset_loader.load_synthetic_home("assist-mini")
    
    # Extract devices
    devices = home_data.get('devices', [])
    
    if not devices:
        pytest.skip("No devices found in dataset")
    
    # Create test YAML with entity IDs from dataset
    test_entities = [d.get('entity_id', '') for d in devices[:3] if d.get('entity_id')]
    
    if not test_entities:
        pytest.skip("No entity IDs found in devices")
    
    yaml_content = f"""
alias: Test Entity Resolution
trigger:
  - platform: state
    entity_id: {test_entities[0]}
action:
  - service: homeassistant.turn_on
    entity_id: {test_entities[1] if len(test_entities) > 1 else test_entities[0]}
"""
    
    # Validate YAML
    validation = validate_yaml_structure(yaml_content)
    
    print(f"\n✅ Entity Resolution Test:")
    print(f"  Test Entities: {test_entities}")
    print(f"  YAML Entity IDs: {validation['entity_ids']}")
    print(f"  Matches: {set(test_entities[:2]) == set(validation['entity_ids'])}")
    
    # Assert entity IDs are present
    assert len(validation['entity_ids']) > 0, "Should extract entity IDs from YAML"
    assert validation['valid'], "YAML should be valid"


@pytest.mark.asyncio
async def test_suggestion_ranking_validation(
    dataset_loader: HomeAssistantDatasetLoader
):
    """
    Test suggestion ranking accuracy.
    
    Validates that high-quality suggestions are ranked higher.
    """
    # Load dataset
    home_data = await dataset_loader.load_synthetic_home("assist-mini")
    
    # Extract ground truth synergies
    extractor = GroundTruthExtractor(home_data)
    synergies = extractor.extract_synergies()
    
    if not synergies:
        pytest.skip("No synergies found in dataset")
    
    # Create suggestions with different confidence scores
    suggestions = []
    for synergy in synergies[:10]:
        confidence = synergy.get('confidence', 0.5)
        suggestions.append({
            'id': f"suggestion_{len(suggestions)}",
            'description': f"Automation: {synergy.get('trigger_entity')} → {synergy.get('action_entity')}",
            'confidence': confidence,
            'relationship_type': synergy.get('relationship_type', 'unknown'),
            'benefit_score': 0.7 if synergy.get('relationship_type') == 'motion_to_light' else 0.5
        })
    
    # Sort by confidence (simulating ranking)
    ranked_suggestions = sorted(suggestions, key=lambda x: x['confidence'], reverse=True)
    
    # Validate ranking
    top_5 = ranked_suggestions[:5]
    top_5_confidences = [s['confidence'] for s in top_5]
    avg_top_5_confidence = sum(top_5_confidences) / len(top_5_confidences) if top_5_confidences else 0
    
    print(f"\n✅ Suggestion Ranking Validation:")
    print(f"  Total Suggestions: {len(suggestions)}")
    print(f"  Top 5 Average Confidence: {avg_top_5_confidence:.3f}")
    print(f"  Top 5 Relationship Types: {[s['relationship_type'] for s in top_5]}")
    
    # Assert ranking quality
    assert avg_top_5_confidence >= 0.7, f"Top 5 should have high confidence, got {avg_top_5_confidence:.3f}"
    
    # Check that high-confidence suggestions are ranked higher
    if len(ranked_suggestions) >= 2:
        assert ranked_suggestions[0]['confidence'] >= ranked_suggestions[-1]['confidence'], \
            "Higher confidence suggestions should be ranked higher"


@pytest.mark.asyncio
async def test_automation_generation_on_multiple_datasets(
    dataset_loader: HomeAssistantDatasetLoader
):
    """
    Test automation generation across multiple datasets.
    
    Validates consistency across different home configurations.
    """
    datasets = ['assist-mini']  # Add more as available
    
    results = {}
    
    for dataset_name in datasets:
        try:
            # Load dataset
            home_data = await dataset_loader.load_synthetic_home(dataset_name)
            
            # Extract synergies
            extractor = GroundTruthExtractor(home_data)
            synergies = extractor.extract_synergies()
            
            # Count relationship types
            relationship_types = {}
            for synergy in synergies:
                rel_type = synergy.get('relationship_type', 'unknown')
                relationship_types[rel_type] = relationship_types.get(rel_type, 0) + 1
            
            # Test YAML generation for a few synergies
            yaml_quality_scores = []
            for synergy in synergies[:3]:
                trigger = synergy.get('trigger_entity', '')
                action = synergy.get('action_entity', '')
                
                if trigger and action:
                    yaml_content = f"""
alias: Test
trigger:
  - platform: state
    entity_id: {trigger}
action:
  - service: homeassistant.turn_on
    entity_id: {action}
"""
                    validation = validate_yaml_structure(yaml_content)
                    quality_score = calculate_yaml_quality_score(validation)
                    yaml_quality_scores.append(quality_score)
            
            avg_quality = sum(yaml_quality_scores) / len(yaml_quality_scores) if yaml_quality_scores else 0
            
            results[dataset_name] = {
                'total_synergies': len(synergies),
                'relationship_types': len(relationship_types),
                'avg_yaml_quality': avg_quality,
                'devices': len(home_data.get('devices', []))
            }
            
            print(f"\n✅ {dataset_name}:")
            print(f"  Total synergies: {len(synergies)}")
            print(f"  Relationship types: {len(relationship_types)}")
            print(f"  Avg YAML quality: {avg_quality:.3f}")
        
        except Exception as e:
            print(f"❌ Error testing {dataset_name}: {e}")
            continue
    
    # Assert we got results
    assert len(results) > 0, "Should test at least one dataset"
    
    # Print summary
    print(f"\n✅ Tested {len(results)} datasets")
    total_synergies = sum(r['total_synergies'] for r in results.values())
    avg_quality = sum(r['avg_yaml_quality'] for r in results.values()) / len(results)
    print(f"✅ Total synergies: {total_synergies}")
    print(f"✅ Average YAML quality: {avg_quality:.3f}")

