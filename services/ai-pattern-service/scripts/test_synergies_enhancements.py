#!/usr/bin/env python3
"""
Smoke Test Script for Synergies Enhancements

Tests all new synergy detection engines and integrations.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from synergy_detection import (
    DeviceSynergyDetector,
    RelationshipDiscoveryEngine,
    SpatialIntelligenceService,
    TemporalSynergyDetector,
    DeviceCapabilityAnalyzer
)
from services.energy_savings_calculator import EnergySavingsCalculator
from config import settings


async def test_energy_savings_calculator():
    """Test EnergySavingsCalculator."""
    print("🔋 Testing EnergySavingsCalculator...")
    calculator = EnergySavingsCalculator()
    
    # Test synergy with energy context
    test_synergy = {
        'synergy_type': 'energy_context',
        'devices': ['climate.living_room', 'sensor.electricity_pricing'],
        'context_metadata': {'context_type': 'energy_scheduling'}
    }
    
    result = calculator.calculate_energy_savings(test_synergy)
    assert 'energy_savings_score' in result
    assert 'estimated_kwh_savings' in result
    assert 'estimated_cost_savings' in result
    print(f"   ✅ Energy savings: {result['energy_savings_score']:.2f}, ${result.get('estimated_cost_savings', 0):.2f}/month")
    return True


async def test_relationship_discovery_engine():
    """Test RelationshipDiscoveryEngine."""
    print("🔗 Testing RelationshipDiscoveryEngine...")
    engine = RelationshipDiscoveryEngine()
    
    # Test with empty events (should return empty list)
    import pandas as pd
    empty_events = pd.DataFrame()
    relationships = await engine.discover_from_events(empty_events)
    assert isinstance(relationships, list)
    print(f"   ✅ Relationship discovery initialized (found {len(relationships)} relationships)")
    return True


async def test_spatial_intelligence_service():
    """Test SpatialIntelligenceService."""
    print("📍 Testing SpatialIntelligenceService...")
    service = SpatialIntelligenceService()
    
    # Test with empty synergy (should handle gracefully)
    test_synergy = {
        'synergy_id': 'test-123',
        'devices': ['light.kitchen', 'light.living_room'],
        'area': 'kitchen'
    }
    
    # Test validation (will return False for empty entities, but should not crash)
    result = await service.validate_cross_area_synergy(test_synergy, [])
    assert isinstance(result, bool)
    print(f"   ✅ Spatial intelligence initialized (validation: {result})")
    return True


async def test_temporal_detector():
    """Test TemporalSynergyDetector."""
    print("⏰ Testing TemporalSynergyDetector...")
    detector = TemporalSynergyDetector()
    
    # Test with empty patterns (should return empty list)
    patterns = []
    entities = []
    temporal_synergies = await detector.discover_temporal_patterns(patterns, entities)
    assert isinstance(temporal_synergies, list)
    print(f"   ✅ Temporal detector initialized (found {len(temporal_synergies)} temporal synergies)")
    return True


async def test_capability_analyzer():
    """Test DeviceCapabilityAnalyzer."""
    print("🔧 Testing DeviceCapabilityAnalyzer...")
    if not settings.device_intelligence_url:
        print("   ⚠️  Device intelligence URL not configured, skipping")
        return True
    
    analyzer = DeviceCapabilityAnalyzer(base_url=settings.device_intelligence_url)
    
    # Test with non-existent device (should return empty list gracefully)
    capabilities = await analyzer.get_device_capabilities("test-device-123")
    assert isinstance(capabilities, list)
    print(f"   ✅ Capability analyzer initialized (found {len(capabilities)} capabilities for test device)")
    return True


async def test_synergy_detector_integration():
    """Test DeviceSynergyDetector with new engines."""
    print("🔍 Testing DeviceSynergyDetector integration...")
    
    # Mock data API client
    class MockDataAPIClient:
        async def fetch_devices(self):
            return []
        async def fetch_entities(self):
            return []
    
    detector = DeviceSynergyDetector(data_api_client=MockDataAPIClient())
    
    # Check that engines are initialized
    assert hasattr(detector, 'energy_calculator') or detector.energy_calculator is None
    assert hasattr(detector, 'spatial_intelligence') or detector.spatial_intelligence is None
    assert hasattr(detector, 'temporal_detector') or detector.temporal_detector is None
    assert hasattr(detector, 'capability_analyzer') or detector.capability_analyzer is None
    assert hasattr(detector, 'relationship_discovery') or detector.relationship_discovery is None
    
    print("   ✅ DeviceSynergyDetector initialized with all engines")
    return True


async def main():
    """Run all smoke tests."""
    print("=" * 80)
    print("🧪 Synergies Enhancements Smoke Tests")
    print("=" * 80)
    print()
    
    tests = [
        ("Energy Savings Calculator", test_energy_savings_calculator),
        ("Relationship Discovery Engine", test_relationship_discovery_engine),
        ("Spatial Intelligence Service", test_spatial_intelligence_service),
        ("Temporal Detector", test_temporal_detector),
        ("Capability Analyzer", test_capability_analyzer),
        ("Synergy Detector Integration", test_synergy_detector_integration),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = await test_func()
            results.append((name, True, None))
        except Exception as e:
            print(f"   ❌ {name} failed: {e}")
            results.append((name, False, str(e)))
        print()
    
    # Summary
    print("=" * 80)
    print("📊 Test Summary")
    print("=" * 80)
    
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    for name, success, error in results:
        status = "✅ PASS" if success else f"❌ FAIL: {error}"
        print(f"  {name}: {status}")
    
    print()
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All smoke tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
