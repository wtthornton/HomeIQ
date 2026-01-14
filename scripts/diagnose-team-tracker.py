#!/usr/bin/env python3
"""
Team Tracker Diagnostic Script

Verifies Team Tracker integration status:
- Checks if entities are in DeviceEntity table
- Verifies platform values
- Tests detection endpoint
- Shows sync status
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Any

import aiohttp
from dotenv import load_dotenv

# Fix Windows console encoding
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        # Python < 3.7 - use environment variable only
        pass

# Add shared directory to path
shared_path = Path(__file__).parent.parent / "shared"
if shared_path.exists():
    sys.path.insert(0, str(shared_path))

load_dotenv()

# API Configuration
DATA_API_URL = "http://localhost:8006"  # Fixed: data-api base URL
DEVICE_INTELLIGENCE_URL = "http://localhost:3001/api/device-intelligence"
API_KEY = "hs_P3rU9kQ2xZp6vL1fYc7bN4sTqD8mA0wR"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "X-HomeIQ-API-Key": API_KEY,
    "Content-Type": "application/json",
}


async def check_data_api_entities(session: aiohttp.ClientSession) -> list[dict[str, Any]]:
    """Check for Team Tracker entities in data-api"""
    print("\n" + "=" * 80)
    print("[DATA API] Checking Data API for Team Tracker Entities")
    print("=" * 80)
    
    try:
        # Fetch all sensor entities
        url = f"{DATA_API_URL}/api/entities?domain=sensor&limit=1000"
        async with session.get(url, headers=HEADERS) as response:
            if response.status != 200:
                print(f"[ERROR] Failed to fetch entities: {response.status}")
                error_text = await response.text()
                print(f"Error: {error_text[:200]}")
                return []
            
            data = await response.json()
            
            # Handle response format (can be dict with "entities" key or list)
            if isinstance(data, dict) and "entities" in data:
                entities = data["entities"]
            elif isinstance(data, list):
                entities = data
            else:
                print(f"[ERROR] Unexpected response format: {type(data)}")
                return []
            
            # Filter for Team Tracker entities
            team_tracker_entities = []
            for entity in entities:
                entity_id = entity.get("entity_id", "").lower()
                platform = entity.get("platform", "").lower() if entity.get("platform") else ""
                
                # Check platform
                platform_match = (
                    platform in ["teamtracker", "team_tracker", "team-tracker"] or
                    ("team" in platform and "tracker" in platform)
                )
                
                # Check entity_id
                entity_id_match = (
                    "team_tracker" in entity_id or
                    "teamtracker" in entity_id or
                    entity_id.endswith("_team_tracker") or
                    entity_id.startswith("sensor.team_tracker") or
                    entity_id.startswith("sensor.teamtracker")
                )
                
                if platform_match or entity_id_match:
                    team_tracker_entities.append(entity)
            
            print(f"[OK] Found {len(team_tracker_entities)} Team Tracker entities in data-api")
            
            if team_tracker_entities:
                print("\nDetected Entities:")
                for entity in team_tracker_entities:
                    print(f"  - {entity.get('entity_id')}")
                    print(f"    Platform: {entity.get('platform', 'N/A')}")
                    print(f"    Name: {entity.get('name', entity.get('friendly_name', 'N/A'))}")
                    print()
            else:
                print("[WARN] No Team Tracker entities found in data-api")
                print("\nPossible reasons:")
                print("  1. Entities not synced from Home Assistant")
                print("  2. Platform value differs from expected")
                print("  3. Entity ID pattern not matching")
                print("  4. Team Tracker not installed in Home Assistant")
            
            return team_tracker_entities
            
    except Exception as e:
        print(f"[ERROR] Error checking data-api: {e}")
        return []


async def check_detection_status(session: aiohttp.ClientSession) -> dict[str, Any]:
    """Check Team Tracker detection status"""
    print("\n" + "=" * 80)
    print("[STATUS] Checking Team Tracker Detection Status")
    print("=" * 80)
    
    try:
        url = f"{DEVICE_INTELLIGENCE_URL}/team-tracker/status"
        async with session.get(url, headers=HEADERS) as response:
            if response.status != 200:
                print(f"[ERROR] Failed to fetch status: {response.status}")
                return {}
            
            status = await response.json()
            
            print(f"Installation Status: {status.get('installation_status', 'unknown')}")
            print(f"Is Installed: {status.get('is_installed', False)}")
            print(f"Configured Teams: {status.get('configured_teams_count', 0)}")
            print(f"Active Teams: {status.get('active_teams_count', 0)}")
            print(f"Last Checked: {status.get('last_checked', 'N/A')}")
            
            return status
            
    except Exception as e:
        print(f"[ERROR] Error checking status: {e}")
        return {}


async def test_detection(session: aiohttp.ClientSession) -> dict[str, Any]:
    """Test Team Tracker detection"""
    print("\n" + "=" * 80)
    print("[DETECT] Testing Team Tracker Detection")
    print("=" * 80)
    
    try:
        url = f"{DEVICE_INTELLIGENCE_URL}/team-tracker/detect"
        async with session.post(url, headers=HEADERS) as response:
            if response.status != 200:
                error_text = await response.text()
                print(f"[ERROR] Detection failed: {response.status}")
                print(f"Error: {error_text}")
                return {}
            
            result = await response.json()
            
            detected_count = result.get("detected_count", 0)
            print(f"[OK] Detection completed: {detected_count} entities found")
            
            if detected_count > 0:
                print("\nDetected Teams:")
                for team in result.get("detected_teams", []):
                    print(f"  - {team.get('entity_id')}")
                    print(f"    Name: {team.get('name', 'N/A')}")
                    print(f"    Platform: {team.get('platform', 'N/A')}")
                    print()
            else:
                print("[WARN] No Team Tracker entities detected")
                if "warning" in result:
                    print(f"Warning: {result['warning']}")
            
            return result
            
    except Exception as e:
        print(f"[ERROR] Error testing detection: {e}")
        import traceback
        traceback.print_exc()
        return {}


async def check_debug_platforms(session: aiohttp.ClientSession) -> dict[str, Any]:
    """Check debug platform information"""
    print("\n" + "=" * 80)
    print("[DEBUG] Checking Debug Platform Information")
    print("=" * 80)
    
    try:
        url = f"{DEVICE_INTELLIGENCE_URL}/team-tracker/debug/platforms"
        async with session.get(url, headers=HEADERS) as response:
            if response.status != 200:
                print(f"[ERROR] Failed to fetch debug info: {response.status}")
                return {}
            
            debug_info = await response.json()
            
            print(f"Source: {debug_info.get('source', 'unknown')}")
            print(f"Total Sensor Entities: {debug_info.get('total_sensor_entities', 0)}")
            print(f"Team Tracker Candidates: {debug_info.get('total_team_tracker_candidates', 0)}")
            
            # Show platform distribution
            platforms = debug_info.get("sensor_platforms", {})
            if platforms:
                print("\nSensor Platform Distribution (top 10):")
                sorted_platforms = sorted(platforms.items(), key=lambda x: x[1], reverse=True)[:10]
                for platform, count in sorted_platforms:
                    print(f"  {platform}: {count}")
            
            # Show Team Tracker candidates by platform
            by_platform = debug_info.get("team_tracker_like_by_platform", [])
            if by_platform:
                print("\nTeam Tracker Candidates (by platform):")
                for entity in by_platform:
                    print(f"  - {entity.get('entity_id')}")
                    print(f"    Platform: {entity.get('platform', 'N/A')}")
                    print(f"    Name: {entity.get('name', 'N/A')}")
            
            # Show Team Tracker candidates by entity_id
            by_entity_id = debug_info.get("team_tracker_like_by_entity_id", [])
            if by_entity_id:
                print("\nTeam Tracker Candidates (by entity_id):")
                for entity in by_entity_id:
                    print(f"  - {entity.get('entity_id')}")
                    print(f"    Platform: {entity.get('platform', 'N/A')}")
                    print(f"    Name: {entity.get('name', 'N/A')}")
            
            if "error" in debug_info:
                print(f"\n[WARN] Debug Error: {debug_info['error']}")
            
            return debug_info
            
    except Exception as e:
        print(f"[ERROR] Error checking debug info: {e}")
        import traceback
        traceback.print_exc()
        return {}


async def main():
    """Run all diagnostic checks"""
    print("=" * 80)
    print("[TEAM TRACKER] Team Tracker Diagnostic Script")
    print("=" * 80)
    print("\nThis script will check:")
    print("  1. Entities in data-api DeviceEntity table")
    print("  2. Team Tracker detection status")
    print("  3. Test detection endpoint")
    print("  4. Debug platform information")
    print()
    
    async with aiohttp.ClientSession() as session:
        # Check 1: Data API entities
        entities = await check_data_api_entities(session)
        
        # Check 2: Detection status
        status = await check_detection_status(session)
        
        # Check 3: Test detection
        detection_result = await test_detection(session)
        
        # Check 4: Debug platforms
        debug_info = await check_debug_platforms(session)
        
        # Summary
        print("\n" + "=" * 80)
        print("[SUMMARY] Summary")
        print("=" * 80)
        print(f"Entities in data-api: {len(entities)}")
        print(f"Detection status: {status.get('installation_status', 'unknown')}")
        print(f"Detected count: {detection_result.get('detected_count', 0)}")
        print(f"Debug candidates: {debug_info.get('total_team_tracker_candidates', 0)}")
        
        if len(entities) == 0 and detection_result.get('detected_count', 0) == 0:
            print("\n[ISSUE] No Team Tracker entities found!")
            print("\nRecommended actions:")
            print("  1. Verify Team Tracker is installed in Home Assistant")
            print("  2. Check websocket-ingestion is syncing entities")
            print("  3. Verify entities have platform='teamtracker' in entity registry")
            print("  4. Check entity_id patterns match expected patterns")
        elif len(entities) > 0 and detection_result.get('detected_count', 0) == 0:
            print("\n[ISSUE] Entities exist but detection failed!")
            print("\nRecommended actions:")
            print("  1. Check detection logic in team_tracker_router.py")
            print("  2. Verify platform matching patterns")
            print("  3. Check entity_id matching patterns")
        elif len(entities) > 0 and detection_result.get('detected_count', 0) > 0:
            print("\n[SUCCESS] Team Tracker integration working correctly!")
        
        print()


if __name__ == "__main__":
    asyncio.run(main())
