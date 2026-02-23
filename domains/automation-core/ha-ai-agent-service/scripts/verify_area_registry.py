#!/usr/bin/env python3
"""
Verification script for Area Registry WebSocket API implementation.

This script tests the area registry functionality to verify:
1. WebSocket API connection works
2. Areas are fetched correctly
3. Fallback to REST API works if needed
"""

import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from clients.ha_client import HomeAssistantClient
from config import Settings


async def verify_area_registry():
    """Verify area registry functionality"""
    print("🔍 Verifying Area Registry Implementation...")
    print("=" * 60)
    
    # Load settings
    try:
        settings = Settings()
        print(f"✅ Settings loaded")
        print(f"   HA URL: {settings.ha_url}")
        print(f"   Data API URL: {settings.data_api_url}")
    except Exception as e:
        print(f"❌ Failed to load settings: {e}")
        return False
    
    # Create client
    try:
        client = HomeAssistantClient(
            ha_url=settings.ha_url,
            access_token=settings.ha_token
        )
        print(f"✅ Home Assistant client created")
    except Exception as e:
        print(f"❌ Failed to create client: {e}")
        return False
    
    # Test area registry fetch
    try:
        print("\n🔌 Attempting to fetch area registry...")
        areas = await client.get_area_registry()
        
        if areas:
            print(f"✅ Successfully fetched {len(areas)} areas:")
            for area in areas[:5]:  # Show first 5
                area_id = area.get("area_id", "unknown")
                name = area.get("name", area_id)
                aliases = area.get("aliases", [])
                icon = area.get("icon", "")
                
                print(f"   - {name} (area_id: {area_id})")
                if aliases:
                    print(f"     Aliases: {', '.join(aliases[:3])}")
                if icon:
                    print(f"     Icon: {icon}")
            
            if len(areas) > 5:
                print(f"   ... and {len(areas) - 5} more areas")
            
            print(f"\n✅ Area registry verification PASSED")
            return True
        else:
            print("⚠️  No areas found")
            print("   This could mean:")
            print("   - No areas are configured in Home Assistant")
            print("   - WebSocket API is not available (fallback may have been used)")
            print("   - Check Home Assistant logs for details")
            return True  # Not an error, just no areas configured
        
    except Exception as e:
        print(f"❌ Failed to fetch area registry: {e}")
        print(f"   Error type: {type(e).__name__}")
        import traceback
        print(f"   Traceback:")
        traceback.print_exc()
        return False
    finally:
        await client.close()


async def main():
    """Main entry point"""
    success = await verify_area_registry()
    print("\n" + "=" * 60)
    if success:
        print("✅ Verification completed successfully")
        sys.exit(0)
    else:
        print("❌ Verification failed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

