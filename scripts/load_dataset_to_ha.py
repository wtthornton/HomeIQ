#!/usr/bin/env python3
"""
Load synthetic home dataset into Home Assistant test container
Creates entities, areas, and relationships from dataset YAML
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

import httpx
import yaml

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "services" / "ai-automation-service"))

from src.testing.dataset_loader import HomeAssistantDatasetLoader


async def create_ha_entity(
    client: httpx.AsyncClient,
    entity_id: str,
    state: str,
    attributes: dict[str, Any],
    ha_url: str,
    ha_token: str,
) -> bool:
    """Create or update an entity in Home Assistant"""
    try:
        # Use Home Assistant API to set state
        # Note: This requires the entity to exist first (via configuration)
        # For testing, we'll use the states API
        response = await client.post(
            f"{ha_url}/api/states/{entity_id}",
            headers={
                "Authorization": f"Bearer {ha_token}",
                "Content-Type": "application/json",
            },
            json={
                "state": state,
                "attributes": attributes,
            },
            timeout=10.0,
        )
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"  ⚠️  Failed to create entity {entity_id}: {e}")
        return False


async def create_ha_area(
    client: httpx.AsyncClient,
    area_name: str,
    ha_url: str,
    ha_token: str,
) -> str | None:
    """Create an area in Home Assistant"""
    try:
        response = await client.post(
            f"{ha_url}/api/config/area_registry/create",
            headers={
                "Authorization": f"Bearer {ha_token}",
                "Content-Type": "application/json",
            },
            json={"name": area_name},
            timeout=10.0,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("area_id")
    except Exception as e:
        print(f"  ⚠️  Failed to create area {area_name}: {e}")
        return None


async def load_dataset_to_ha(
    dataset_name: str | None = None,
    home_json_path: Path | None = None,
    ha_url: str = "http://localhost:8124",
    ha_token: str | None = None,
    dataset_root: Path | None = None,
) -> bool:
    """
    Load a synthetic home dataset into Home Assistant.
    
    Supports both YAML (home-assistant-datasets format) and JSON (our generated format).
    
    Args:
        dataset_name: Dataset name for YAML format (e.g., 'assist-mini')
        home_json_path: Path to JSON file for our generated format
        ha_url: Home Assistant URL
        ha_token: Authentication token
        dataset_root: Root directory for YAML datasets
    
    Returns:
        True if successful, False otherwise
    """
    # Load token from environment or .env.test
    if not ha_token:
        import os
        ha_token = os.getenv("HA_TEST_TOKEN")
        if not ha_token:
            print("❌ HA_TEST_TOKEN not set. Please run setup_ha_test.sh first")
            return False
    
    # Determine format and load
    if home_json_path:
        # Load JSON format (our generated homes)
        from src.training.synthetic_home_ha_loader import SyntheticHomeHALoader
        
        loader = SyntheticHomeHALoader()
        
        print(f"Loading JSON home: {home_json_path}")
        try:
            results = await loader.load_json_home_to_ha(
                home_json_path=home_json_path,
                ha_url=ha_url,
                ha_token=ha_token
            )
            
            print(f"✅ Home loaded: {results['areas_created']} areas, {results['entities_created']} entities")
            
            if results['errors']:
                print(f"⚠️  {len(results['errors'])} errors encountered")
                return False
            
            return True
        except Exception as e:
            print(f"❌ Failed to load JSON home: {e}")
            return False
    
    elif dataset_name:
        # Load YAML format (home-assistant-datasets)
        if dataset_root is None:
            dataset_root = Path(__file__).parent.parent / "services" / "tests" / "datasets" / "home-assistant-datasets" / "datasets"
        
        loader = HomeAssistantDatasetLoader(dataset_root=str(dataset_root))
        
        print(f"Loading dataset '{dataset_name}'...")
        try:
            home_data = await loader.load_synthetic_home(dataset_name)
        except Exception as e:
            print(f"❌ Failed to load dataset: {e}")
            return False
        
        print(f"✅ Dataset loaded: {len(home_data.get('devices', []))} devices, {len(home_data.get('areas', []))} areas")
        
        # Connect to Home Assistant
        async with httpx.AsyncClient() as client:
            # Create areas
            areas = home_data.get("areas", [])
            area_map = {}
            
            print(f"\nCreating {len(areas)} areas...")
            for area in areas:
                area_name = area.get("name", area.get("area_name", "Unknown"))
                area_id = await create_ha_area(client, area_name, ha_url, ha_token)
                if area_id:
                    area_map[area_name] = area_id
                    print(f"  ✅ Created area: {area_name}")
            
            # Create entities from devices
            devices = home_data.get("devices", [])
            print(f"\nCreating {len(devices)} entities...")
            
            created = 0
            for device in devices:
                entity_id = device.get("entity_id")
                if not entity_id:
                    continue
                
                # Extract state and attributes
                state = device.get("state", "unknown")
                attributes = device.get("attributes", {})
                
                # Add area if available
                area_name = device.get("area_name")
                if area_name and area_name in area_map:
                    attributes["area_id"] = area_map[area_name]
                
                success = await create_ha_entity(
                    client, entity_id, state, attributes, ha_url, ha_token
                )
                if success:
                    created += 1
                    if created % 10 == 0:
                        print(f"  Created {created}/{len(devices)} entities...")
            
            print(f"\n✅ Created {created} entities in Home Assistant")
        
        return True


async def main():
    parser = argparse.ArgumentParser(
        description="Load synthetic home dataset into Home Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Load YAML dataset (home-assistant-datasets format)
  python scripts/load_dataset_to_ha.py --dataset assist-mini
  
  # Load JSON home (our generated format)
  python scripts/load_dataset_to_ha.py --home tests/datasets/synthetic_homes/home_001.json
        """
    )
    parser.add_argument(
        "--dataset",
        help="Dataset name to load (YAML format, e.g., 'assist-mini')",
    )
    parser.add_argument(
        "--home",
        type=Path,
        help="Path to JSON home file (our generated format)",
    )
    parser.add_argument(
        "--ha-url",
        default="http://localhost:8124",
        help="Home Assistant URL (default: http://localhost:8124)",
    )
    parser.add_argument(
        "--ha-token",
        help="Home Assistant token (or set HA_TEST_TOKEN env var)",
    )
    parser.add_argument(
        "--dataset-root",
        type=Path,
        help="Path to dataset root directory (for YAML datasets)",
    )
    
    args = parser.parse_args()
    
    # Validate that one format is specified
    if not args.dataset and not args.home:
        parser.error("Must specify either --dataset (YAML) or --home (JSON)")
    
    if args.dataset and args.home:
        parser.error("Cannot specify both --dataset and --home")
    
    success = await load_dataset_to_ha(
        dataset_name=args.dataset,
        home_json_path=args.home,
        ha_url=args.ha_url,
        ha_token=args.ha_token,
        dataset_root=args.dataset_root,
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())

