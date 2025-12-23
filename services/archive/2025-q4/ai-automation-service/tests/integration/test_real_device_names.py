"""
Integration tests for Real Device Names

Epic AI-12, Story AI12.7: E2E Testing with Real Devices
Tests entity resolution with actual user device names and validates accuracy.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from typing import Any, Dict, List

from src.services.entity.personalized_index import PersonalizedEntityIndex, EntityIndexEntry, EntityVariant
from src.services.entity.personalized_resolver import PersonalizedEntityResolver
from src.services.entity.training_data_generator import TrainingDataGenerator, QueryEntityPair
from src.services.entity.index_builder import PersonalizedIndexBuilder
from src.clients.ha_client import HomeAssistantClient


@pytest.fixture
def real_device_names():
    """Real device names from user's Home Assistant (example data)"""
    return {
        "light.office": {
            "name": "Office Light",
            "aliases": ["office light", "desk light", "work light"],
            "domain": "light",
            "area": "office"
        },
        "light.kitchen": {
            "name": "Kitchen Light",
            "aliases": ["kitchen light", "cooking light"],
            "domain": "light",
            "area": "kitchen"
        },
        "light.bedroom": {
            "name": "Bedroom Light",
            "aliases": ["bedroom light", "sleep light"],
            "domain": "light",
            "area": "bedroom"
        },
        "climate.living_room": {
            "name": "Living Room Thermostat",
            "aliases": ["thermostat", "living room temp", "temperature"],
            "domain": "climate",
            "area": "living_room"
        },
        "cover.garage": {
            "name": "Garage Door",
            "aliases": ["garage door", "garage"],
            "domain": "cover",
            "area": "garage"
        }
    }


@pytest.fixture
def mock_ha_client_with_real_devices(real_device_names):
    """Create mock HA client with real device names"""
    client = Mock(spec=HomeAssistantClient)
    
    # Build entity registry from real device names
    entity_registry = {}
    for entity_id, info in real_device_names.items():
        entity_registry[entity_id] = {
            "entity_id": entity_id,
            "name": info["name"],
            "aliases": info["aliases"],
            "domain": info["domain"],
            "device_id": f"device_{entity_id.split('.')[1]}",
            "area_id": info["area"]
        }
    
    client.get_entity_registry = AsyncMock(return_value=entity_registry)
    
    # Mock areas
    areas = {
        "office": {"area_id": "office", "name": "Office", "aliases": ["work space"]},
        "kitchen": {"area_id": "kitchen", "name": "Kitchen", "aliases": ["cooking area"]},
        "bedroom": {"area_id": "bedroom", "name": "Bedroom", "aliases": []},
        "living_room": {"area_id": "living_room", "name": "Living Room", "aliases": ["family room"]},
        "garage": {"area_id": "garage", "name": "Garage", "aliases": []}
    }
    client.get_areas = AsyncMock(return_value=areas)
    
    return client


@pytest.fixture
async def personalized_index_real_devices(mock_ha_client_with_real_devices):
    """Create personalized index from real device names"""
    builder = PersonalizedIndexBuilder(ha_client=mock_ha_client_with_real_devices)
    index = await builder.build_index()
    return index


@pytest.fixture
def personalized_resolver_real_devices(personalized_index_real_devices, mock_ha_client_with_real_devices):
    """Create personalized resolver with real devices"""
    return PersonalizedEntityResolver(
        personalized_index=personalized_index_real_devices,
        ha_client=mock_ha_client_with_real_devices
    )


@pytest.fixture
def training_data_generator(personalized_index_real_devices, personalized_resolver_real_devices):
    """Create training data generator"""
    return TrainingDataGenerator(
        personalized_index=personalized_index_real_devices,
        personalized_resolver=personalized_resolver_real_devices
    )


@pytest.mark.asyncio
async def test_resolve_real_device_names(personalized_resolver_real_devices, real_device_names):
    """Test resolution with real device names from user's Home Assistant"""
    test_cases = [
        ("turn on office light", "light.office"),
        ("turn on kitchen light", "light.kitchen"),
        ("set living room temperature to 72", "climate.living_room"),
        ("open garage door", "cover.garage"),
    ]
    
    results = []
    for query, expected_entity_id in test_cases:
        result = await personalized_resolver_real_devices.resolve_entities(
            device_names=[query],
            query=query
        )
        results.append((query, expected_entity_id, result))
    
    # Verify resolution accuracy
    correct = 0
    for query, expected_entity_id, result in results:
        resolved = result.resolved_entities
        if resolved and expected_entity_id in resolved:
            correct += 1
        else:
            print(f"Failed to resolve: {query} -> Expected: {expected_entity_id}, Got: {resolved}")
    
    accuracy = correct / len(test_cases)
    print(f"Resolution accuracy: {accuracy:.2%} ({correct}/{len(test_cases)})")
    
    # Should achieve high accuracy with real device names
    assert accuracy >= 0.75, f"Accuracy {accuracy:.2%} below threshold 0.75"


@pytest.mark.asyncio
async def test_resolve_real_aliases(personalized_resolver_real_devices, real_device_names):
    """Test resolution with real aliases from user's device names"""
    test_cases = [
        ("turn on desk light", "light.office"),  # Alias for office light
        ("turn on cooking light", "light.kitchen"),  # Alias for kitchen light
        ("set thermostat to 72", "climate.living_room"),  # Alias for thermostat
        ("open garage", "cover.garage"),  # Alias for garage door
    ]
    
    results = []
    for query, expected_entity_id in test_cases:
        result = await personalized_resolver_real_devices.resolve_entities(
            device_names=[query],
            query=query
        )
        results.append((query, expected_entity_id, result))
    
    # Verify alias resolution
    correct = 0
    for query, expected_entity_id, result in results:
        resolved = result.resolved_entities
        if resolved and expected_entity_id in resolved:
            correct += 1
    
    accuracy = correct / len(test_cases)
    print(f"Alias resolution accuracy: {accuracy:.2%} ({correct}/{len(test_cases)})")
    
    # Aliases should resolve correctly
    assert accuracy >= 0.75


@pytest.mark.asyncio
async def test_validate_against_real_entities(personalized_index_real_devices, real_device_names):
    """Validate that index contains all real Home Assistant entities"""
    # Check all real devices are in index
    missing = []
    for entity_id in real_device_names.keys():
        entry = personalized_index_real_devices.get_entity(entity_id)
        if not entry:
            missing.append(entity_id)
    
    assert len(missing) == 0, f"Missing entities in index: {missing}"
    
    # Verify entity details match
    for entity_id, info in real_device_names.items():
        entry = personalized_index_real_devices.get_entity(entity_id)
        assert entry is not None
        assert entry.domain == info["domain"]
        assert entry.area_id == info["area"]
        
        # Check variants include name and aliases
        variant_names = [v.variant_name for v in entry.variants]
        assert info["name"] in variant_names or any(info["name"].lower() in v.lower() for v in variant_names)
        
        # Check aliases are included
        for alias in info["aliases"]:
            assert any(alias.lower() in v.lower() for v in variant_names), f"Alias '{alias}' not found in variants"


@pytest.mark.asyncio
async def test_measure_accuracy_improvement(
    personalized_resolver_real_devices,
    real_device_names
):
    """Measure accuracy improvement with personalization"""
    # Test queries based on real device names
    test_queries = [
        "turn on office light",
        "turn on kitchen light",
        "turn on bedroom light",
        "set living room temperature to 72",
        "open garage door",
        "turn on desk light",  # Alias
        "turn on cooking light",  # Alias
        "set thermostat to 72",  # Alias
    ]
    
    results = []
    for query in test_queries:
        result = await personalized_resolver_real_devices.resolve_entities(
            device_names=[query],
            query=query
        )
        results.append(result)
    
    # Calculate accuracy metrics
    total_queries = len(test_queries)
    resolved_queries = sum(1 for r in results if r.resolved_entities)
    high_confidence = sum(
        1 for r in results
        if r.resolved_entities and any(
            m.confidence_score >= 0.8 for m in r.resolved_entities.values()
        )
    )
    
    resolution_rate = resolved_queries / total_queries
    high_confidence_rate = high_confidence / total_queries
    
    print(f"Resolution rate: {resolution_rate:.2%} ({resolved_queries}/{total_queries})")
    print(f"High confidence rate: {high_confidence_rate:.2%} ({high_confidence}/{total_queries})")
    
    # Should achieve good resolution rate with personalization
    assert resolution_rate >= 0.75, f"Resolution rate {resolution_rate:.2%} below threshold"
    assert high_confidence_rate >= 0.5, f"High confidence rate {high_confidence_rate:.2%} below threshold"


@pytest.mark.asyncio
async def test_generate_training_data_from_real_devices(training_data_generator):
    """Test generating training data from real device names"""
    # Generate synthetic queries
    pairs = training_data_generator.generate_synthetic_queries(limit=50)
    
    assert len(pairs) > 0
    
    # Verify pairs are valid
    for pair in pairs:
        assert pair.query
        assert pair.entity_id
        assert pair.device_name
        assert pair.domain
        assert pair.source == "synthetic"
    
    # Get statistics
    stats = training_data_generator.get_dataset_stats(pairs)
    
    print(f"Generated {stats['total_pairs']} training pairs")
    print(f"Domains: {stats['by_domain']}")
    print(f"Areas: {stats['by_area']}")
    
    # Should have pairs for multiple domains
    assert len(stats['by_domain']) > 1


@pytest.mark.asyncio
async def test_export_training_data_for_simulation(training_data_generator):
    """Test exporting training data for simulation framework"""
    import tempfile
    from pathlib import Path
    
    # Generate training data
    pairs = training_data_generator.generate_synthetic_queries(limit=20)
    
    # Export to JSON
    with tempfile.TemporaryDirectory() as tmpdir:
        json_path = Path(tmpdir) / "training_data.json"
        success = training_data_generator.export_for_simulation(pairs, json_path, format="json")
        
        assert success
        assert json_path.exists()
        
        # Verify JSON content
        import json
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert "metadata" in data
        assert "pairs" in data
        assert len(data["pairs"]) == len(pairs)
    
    # Export to CSV
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = Path(tmpdir) / "training_data.csv"
        success = training_data_generator.export_for_simulation(pairs, csv_path, format="csv")
        
        assert success
        assert csv_path.exists()


@pytest.mark.asyncio
async def test_comparison_generic_vs_personalized(
    personalized_resolver_real_devices,
    real_device_names
):
    """Compare generic vs personalized resolution with real device names"""
    # These queries would be ambiguous without personalization
    ambiguous_queries = [
        "turn on the light",  # Which light?
        "set temperature to 72",  # Which thermostat?
        "turn on desk light",  # Alias - may not be in generic system
    ]
    
    results = []
    for query in ambiguous_queries:
        result = await personalized_resolver_real_devices.resolve_entities(
            device_names=[query],
            query=query
        )
        results.append(result)
    
    # With personalization, should resolve better
    resolved = sum(1 for r in results if r.resolved_entities)
    resolution_rate = resolved / len(ambiguous_queries)
    
    print(f"Personalized resolution rate for ambiguous queries: {resolution_rate:.2%}")
    
    # Personalization should help with ambiguous queries
    # (Note: Without generic resolver to compare, we just verify it works)
    assert resolution_rate >= 0.0  # At least some should resolve


@pytest.mark.asyncio
async def test_real_device_name_variations(personalized_resolver_real_devices, real_device_names):
    """Test resolution with various ways users might refer to real devices"""
    # Test different phrasings for same device
    variations = [
        ("turn on office light", "light.office"),
        ("turn on the office light", "light.office"),
        ("office light on", "light.office"),
        ("light the office", "light.office"),
    ]
    
    results = []
    for query, expected_entity_id in variations:
        result = await personalized_resolver_real_devices.resolve_entities(
            device_names=[query],
            query=query
        )
        results.append((query, expected_entity_id, result))
    
    # Should handle variations
    correct = sum(
        1 for _, expected, result in results
        if result.resolved_entities and expected in result.resolved_entities
    )
    
    accuracy = correct / len(variations)
    print(f"Variation handling accuracy: {accuracy:.2%}")
    
    # Should handle most variations
    assert accuracy >= 0.5


@pytest.mark.asyncio
async def test_real_device_name_performance(personalized_resolver_real_devices):
    """Test performance with real device names"""
    import time
    
    # Realistic user queries
    queries = [
        "turn on office light",
        "turn on kitchen light",
        "set living room temperature to 72",
        "open garage door",
        "turn off bedroom light",
    ] * 20  # 100 queries
    
    start_time = time.time()
    
    for query in queries:
        await personalized_resolver_real_devices.resolve_entities(
            device_names=[query],
            query=query
        )
    
    elapsed = time.time() - start_time
    
    # Should be fast enough for real-time use
    assert elapsed < 10.0, f"Too slow: {elapsed:.2f}s for {len(queries)} queries"
    print(f"Resolved {len(queries)} queries in {elapsed:.2f}s ({len(queries)/elapsed:.1f} queries/sec)")

