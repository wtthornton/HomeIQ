#!/usr/bin/env python3
"""
Load our generated synthetic home JSON files into Home Assistant test container.

Usage:
    python scripts/load_synthetic_home_to_ha.py \
        --home tests/datasets/synthetic_homes/home_001.json \
        --ha-url http://localhost:8124 \
        --ha-token <token>
"""

#!/usr/bin/env python3
"""
Load our generated synthetic home JSON files into Home Assistant test container.

Usage:
    python scripts/load_synthetic_home_to_ha.py \
        --home tests/datasets/synthetic_homes/home_001.json \
        --ha-url http://localhost:8124 \
        --ha-token <token>
"""

import argparse
import asyncio
import os
import sys
import traceback
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "services" / "ai-automation-service"))

from src.training.synthetic_home_ha_loader import SyntheticHomeHALoader


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Load synthetic home JSON into Home Assistant"
    )
    parser.add_argument(
        "--home",
        type=Path,
        required=True,
        help="Path to synthetic home JSON file",
    )
    parser.add_argument(
        "--ha-url",
        default=os.getenv("HA_TEST_URL", "http://localhost:8124"),
        help="Home Assistant URL (default: http://localhost:8124 or HA_TEST_URL env var)",
    )
    parser.add_argument(
        "--ha-token",
        default=os.getenv("HA_TEST_TOKEN"),
        help="Home Assistant token (or set HA_TEST_TOKEN env var)",
    )
    
    args = parser.parse_args()
    
    # Validate inputs
    if not args.home.exists():
        print(f"❌ Home file not found: {args.home}")
        sys.exit(1)
    
    if not args.ha_token:
        print("❌ HA_TEST_TOKEN not set. Please set environment variable or use --ha-token")
        sys.exit(1)
    
    # Load home into HA
    loader = SyntheticHomeHALoader()
    
    print(f"Loading home: {args.home}")
    print(f"HA URL: {args.ha_url}")
    
    try:
        results = await loader.load_json_home_to_ha(
            home_json_path=args.home,
            ha_url=args.ha_url,
            ha_token=args.ha_token
        )
        
        print(f"\n✅ Load complete:")
        print(f"   Areas created: {results['areas_created']}")
        print(f"   Entities created: {results['entities_created']}")
        
        if results['errors']:
            print(f"\n⚠️  Errors encountered ({len(results['errors'])}):")
            for error in results['errors'][:10]:  # Show first 10 errors
                print(f"   - {error}")
            if len(results['errors']) > 10:
                print(f"   ... and {len(results['errors']) - 10} more errors")
        
        sys.exit(0 if not results['errors'] else 1)
        
    except FileNotFoundError as e:
        print(f"❌ File not found: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"❌ Invalid input: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Failed to load home: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

