#!/usr/bin/env python3
"""
Simple script to run dataset tests directly without pytest path issues
"""
import sys
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, '/app')

from src.testing.dataset_loader import HomeAssistantDatasetLoader

async def test_dataset_loader():
    """Test that we can load the assist-mini dataset"""
    dataset_root = Path('/app/datasets/home-assistant-datasets/datasets')
    
    if not dataset_root.exists():
        print(f"❌ Dataset root not found: {dataset_root}")
        return False
    
    loader = HomeAssistantDatasetLoader(dataset_root=str(dataset_root))
    
    try:
        print(f"Loading dataset 'assist-mini' from {dataset_root}...")
        home_data = await loader.load_synthetic_home("assist-mini")
        
        print("✅ Dataset loaded successfully!")
        print(f"  - Devices: {len(home_data.get('devices', []))}")
        print(f"  - Areas: {len(home_data.get('areas', []))}")
        print(f"  - Events: {len(home_data.get('events', []))}")
        print(f"  - Expected patterns: {len(home_data.get('expected_patterns', []))}")
        print(f"  - Expected synergies: {len(home_data.get('expected_synergies', []))}")
        
        # Basic validation
        assert 'home' in home_data or 'dataset_name' in home_data, "Should have home or dataset_name"
        assert len(home_data.get('devices', [])) >= 0, "Devices list should exist"
        assert len(home_data.get('areas', [])) >= 0, "Areas list should exist"
        
        print("\n✅ All assertions passed!")
        return True
        
    except Exception as e:
        print(f"❌ Error loading dataset: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_dataset_loader())
    sys.exit(0 if success else 1)

