#!/usr/bin/env python3
"""
Evaluate Synergy Detection

Comprehensive analysis of why device_pair and device_chain synergies
are not being detected. Only event_context synergies are found.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

async def evaluate_synergy_detection():
    """Evaluate why device_pair/device_chain synergies aren't detected."""
    
    print("=" * 80)
    print("Synergy Detection Evaluation")
    print("=" * 80)
    
    try:
        # Import required modules - add services path
        services_path = project_root / "services" / "ai-pattern-service" / "src"
        sys.path.insert(0, str(services_path))
        
        try:
            from clients.data_api_client import DataAPIClient
            from synergy_detection.synergy_detector import DeviceSynergyDetector
        except ImportError as import_err:
            print(f"   [ERROR] Import failed: {import_err}")
            print(f"   Tried path: {services_path}")
            raise
        import pandas as pd
        from datetime import datetime, timedelta, timezone
        
        print("\n1. Testing Data API Connection...")
        data_client = DataAPIClient(base_url="http://localhost:8006")
        
        # Fetch devices and entities
        print("   Fetching devices...")
        devices = await data_client.fetch_devices(limit=1000)
        print(f"   [OK] Found {len(devices)} devices")
        
        print("   Fetching entities...")
        entities = await data_client.fetch_entities(limit=1000)
        print(f"   [OK] Found {len(entities)} entities")
        
        if not devices or not entities:
            print("   [ERROR] No devices or entities found - cannot detect synergies")
            return
        
        # Fetch recent events
        print("\n2. Fetching Recent Events...")
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=7)
        
        events_df = await data_client.fetch_events(
            start_time=start_time,
            end_time=end_time,
            limit=50000
        )
        print(f"   [OK] Found {len(events_df)} events")
        
        if events_df.empty:
            print("   [WARNING] No events found - synergy detection needs events")
            return
        
        # Initialize detector
        print("\n3. Initializing Synergy Detector...")
        detector = DeviceSynergyDetector()
        print("   [OK] Detector initialized")
        
        # Test device pair detection
        print("\n4. Testing Device Pair Detection...")
        print("   Running detect_synergies()...")
        
        synergies = await detector.detect_synergies(
            events_df=events_df,
            devices=devices,
            entities=entities
        )
        
        print(f"   [OK] Detected {len(synergies)} synergies")
        
        # Analyze results
        print("\n5. Analyzing Results...")
        by_type = {}
        by_depth = {}
        
        for synergy in synergies:
            synergy_type = synergy.get('synergy_type', 'unknown')
            depth = synergy.get('synergy_depth', 2)
            
            by_type[synergy_type] = by_type.get(synergy_type, 0) + 1
            by_depth[depth] = by_depth.get(depth, 0) + 1
        
        print("\n   Synergy Types Detected:")
        for synergy_type, count in sorted(by_type.items(), key=lambda x: x[1], reverse=True):
            print(f"     {synergy_type}: {count}")
        
        print("\n   Synergy Depths Detected:")
        for depth, count in sorted(by_depth.items()):
            print(f"     Depth {depth}: {count}")
        
        # Check for device_pair and device_chain
        device_pair_count = by_type.get('device_pair', 0)
        device_chain_count = by_type.get('device_chain', 0)
        
        print("\n6. Summary:")
        print(f"   Total synergies: {len(synergies)}")
        print(f"   device_pair: {device_pair_count}")
        print(f"   device_chain: {device_chain_count}")
        print(f"   event_context: {by_type.get('event_context', 0)}")
        
        if device_pair_count == 0 and device_chain_count == 0:
            print("\n   [ERROR] PROBLEM: No device_pair or device_chain synergies detected!")
            print("\n   Possible causes:")
            print("     1. No compatible device pairs found")
            print("     2. Filters too restrictive (same_area_required, min_confidence)")
            print("     3. All potential pairs already have automations")
            print("     4. Device data incomplete or incorrect")
            print("     5. Events don't contain device interactions")
        else:
            print("\n   [OK] device_pair/device_chain synergies are being detected!")
        
        # Sample synergies
        if synergies:
            print("\n7. Sample Synergies:")
            for i, synergy in enumerate(synergies[:5], 1):
                print(f"\n   {i}. Type: {synergy.get('synergy_type')}")
                print(f"      Devices: {synergy.get('devices', [])}")
                print(f"      Impact: {synergy.get('impact_score', 0):.2f}")
                print(f"      Confidence: {synergy.get('confidence', 0):.2f}")
                print(f"      Relationship: {synergy.get('relationship', 'N/A')}")
        
        await data_client.close()
        
    except ImportError as e:
        print(f"\n[ERROR] Import Error: {e}")
        print("   Make sure you're running from the project root and dependencies are installed")
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(evaluate_synergy_detection())
