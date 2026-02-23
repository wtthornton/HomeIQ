"""
Manual test script for SyntheticDeviceGenerator.
Run this to verify the generator works correctly.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.training.synthetic_device_generator import SyntheticDeviceGenerator


def test_generator():
    """Test the synthetic device generator."""
    print("=" * 80)
    print("Testing SyntheticDeviceGenerator")
    print("=" * 80)
    
    # Test initialization
    print("\n1. Testing initialization...")
    generator = SyntheticDeviceGenerator(random_seed=42)
    print("   ✅ Generator initialized")
    
    # Test basic generation
    print("\n2. Testing basic generation...")
    data = generator.generate_training_data(count=10, days=30)
    assert len(data) == 10, f"Expected 10 samples, got {len(data)}"
    print(f"   ✅ Generated {len(data)} samples")
    
    # Test required fields
    print("\n3. Testing required fields...")
    required_fields = [
        'device_id', 'response_time', 'error_rate', 'battery_level',
        'signal_strength', 'usage_frequency', 'temperature', 'humidity',
        'uptime_hours', 'restart_count', 'connection_drops', 'data_transfer_rate'
    ]
    for sample in data:
        for field in required_fields:
            assert field in sample, f"Missing field: {field}"
    print(f"   ✅ All {len(required_fields)} required fields present")
    
    # Test value ranges
    print("\n4. Testing value ranges...")
    for sample in data:
        assert 10 <= sample['response_time'] <= 5000, f"response_time out of range: {sample['response_time']}"
        assert 0.0 <= sample['error_rate'] <= 1.0, f"error_rate out of range: {sample['error_rate']}"
        assert 0 <= sample['battery_level'] <= 100, f"battery_level out of range: {sample['battery_level']}"
        assert -100 <= sample['signal_strength'] <= -10, f"signal_strength out of range: {sample['signal_strength']}"
    print("   ✅ All value ranges valid")
    
    # Test failure scenarios
    print("\n5. Testing failure scenarios...")
    data_with_failures = generator.generate_training_data(count=20, days=30, failure_rate=0.5)
    assert len(data_with_failures) == 20
    print(f"   ✅ Generated {len(data_with_failures)} samples with failures")
    
    # Test reproducibility
    print("\n6. Testing reproducibility...")
    gen1 = SyntheticDeviceGenerator(random_seed=123)
    gen2 = SyntheticDeviceGenerator(random_seed=123)
    data1 = gen1.generate_training_data(count=5, days=30)
    data2 = gen2.generate_training_data(count=5, days=30)
    # Device IDs should match (they're deterministic)
    assert data1[0]['device_id'] == data2[0]['device_id']
    # Values should be similar (within reasonable range)
    assert abs(data1[0]['response_time'] - data2[0]['response_time']) < 1000
    print("   ✅ Generation is reproducible with same seed")
    
    # Test sample output
    print("\n7. Sample output:")
    print(f"   Device ID: {data[0]['device_id']}")
    print(f"   Response Time: {data[0]['response_time']} ms")
    print(f"   Error Rate: {data[0]['error_rate']:.4f}")
    print(f"   Battery Level: {data[0]['battery_level']:.1f}%")
    print(f"   Signal Strength: {data[0]['signal_strength']:.1f} dBm")
    
    print("\n" + "=" * 80)
    print("✅ All tests passed!")
    print("=" * 80)
    return True


if __name__ == "__main__":
    try:
        test_generator()
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

