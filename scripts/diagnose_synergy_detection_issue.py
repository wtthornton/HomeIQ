#!/usr/bin/env python3
"""
Diagnose Synergy Detection Issue

Analyzes why only event_context synergies are detected, not device_pair/device_chain.
Uses API calls instead of direct imports.
"""

import asyncio
import httpx
import json
import sys
from datetime import datetime, timedelta, timezone

async def diagnose():
    """Diagnose synergy detection issue."""
    
    print("=" * 80)
    print("Synergy Detection Issue Diagnosis")
    print("=" * 80)
    
    base_url = "http://localhost:8006"
    pattern_api_url = "http://localhost:8001"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Check Data API
        print("\n1. Checking Data API...")
        try:
            response = await client.get(f"{base_url}/health")
            if response.status_code == 200:
                print("   [OK] Data API is running")
            else:
                print(f"   [WARNING] Data API returned {response.status_code}")
        except Exception as e:
            print(f"   [ERROR] Data API not accessible: {e}")
            return
        
        # Check Pattern Service API
        print("\n2. Checking Pattern Service API...")
        try:
            response = await client.get(f"{pattern_api_url}/health")
            if response.status_code == 200:
                print("   [OK] Pattern Service API is running")
            else:
                print(f"   [WARNING] Pattern Service returned {response.status_code}")
        except Exception as e:
            print(f"   [ERROR] Pattern Service not accessible: {e}")
            return
        
        # Get synergy statistics
        print("\n3. Getting Synergy Statistics...")
        try:
            response = await client.get(f"{pattern_api_url}/api/v1/synergies/statistics")
            if response.status_code == 200:
                stats = response.json()
                data = stats.get('data', {})
                by_type = data.get('by_type', {})
                
                print(f"   Total synergies: {data.get('total_synergies', 0)}")
                print("\n   Synergy types:")
                for synergy_type, count in sorted(by_type.items(), key=lambda x: x[1], reverse=True):
                    print(f"     {synergy_type}: {count}")
                
                device_pair_count = by_type.get('device_pair', 0)
                device_chain_count = by_type.get('device_chain', 0)
                event_context_count = by_type.get('event_context', 0)
                
                print("\n4. Analysis:")
                if device_pair_count == 0 and device_chain_count == 0:
                    print("   [ERROR] No device_pair or device_chain synergies found!")
                    print("\n   Possible causes:")
                    print("     1. Device pair detection not running")
                    print("     2. No compatible device pairs found")
                    print("     3. Filters too restrictive")
                    print("     4. All pairs already have automations")
                    print("     5. Insufficient event data")
                else:
                    print(f"   [OK] Found {device_pair_count} device_pair and {device_chain_count} device_chain synergies")
                
                if event_context_count > 0:
                    print(f"\n   [INFO] Found {event_context_count} event_context synergies (sports/calendar/holiday scenes)")
                
            else:
                print(f"   [ERROR] Failed to get statistics: {response.status_code}")
        except Exception as e:
            print(f"   [ERROR] Error getting statistics: {e}")
        
        # Get sample synergies
        print("\n5. Sample Synergies...")
        try:
            response = await client.get(f"{pattern_api_url}/api/v1/synergies/list?limit=10")
            if response.status_code == 200:
                data = response.json()
                synergies = data.get('data', {}).get('synergies', [])
                
                print(f"   Retrieved {len(synergies)} synergies")
                
                # Group by type
                by_type_sample = {}
                for synergy in synergies:
                    synergy_type = synergy.get('synergy_type', 'unknown')
                    if synergy_type not in by_type_sample:
                        by_type_sample[synergy_type] = []
                    by_type_sample[synergy_type].append(synergy)
                
                for synergy_type, type_synergies in by_type_sample.items():
                    print(f"\n   {synergy_type} ({len(type_synergies)} samples):")
                    for i, synergy in enumerate(type_synergies[:3], 1):
                        devices = synergy.get('devices', [])
                        print(f"     {i}. Devices: {devices}")
                        print(f"        Impact: {synergy.get('impact_score', 0):.2f}, Confidence: {synergy.get('confidence', 0):.2f}")
                        print(f"        Relationship: {synergy.get('metadata', {}).get('relationship', 'N/A')}")
            else:
                print(f"   [ERROR] Failed to get synergies: {response.status_code}")
        except Exception as e:
            print(f"   [ERROR] Error getting synergies: {e}")
        
        # Check device count
        print("\n6. Checking Device Data...")
        try:
            response = await client.get(f"{base_url}/api/v1/devices?limit=1000")
            if response.status_code == 200:
                devices_data = response.json()
                devices = devices_data.get('data', {}).get('devices', [])
                print(f"   [OK] Found {len(devices)} devices")
                
                # Count by domain
                by_domain = {}
                for device in devices:
                    domain = device.get('domain', 'unknown')
                    by_domain[domain] = by_domain.get(domain, 0) + 1
                
                print(f"   Top domains: {dict(sorted(by_domain.items(), key=lambda x: x[1], reverse=True)[:5])}")
            else:
                print(f"   [WARNING] Failed to get devices: {response.status_code}")
        except Exception as e:
            print(f"   [ERROR] Error getting devices: {e}")
        
        # Check recent events
        print("\n7. Checking Recent Events...")
        try:
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=7)
            
            params = {
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'limit': 1000
            }
            
            response = await client.get(f"{base_url}/api/v1/events", params=params)
            if response.status_code == 200:
                events_data = response.json()
                events = events_data.get('data', {}).get('events', [])
                print(f"   [OK] Found {len(events)} events in last 7 days")
                
                if len(events) == 0:
                    print("   [WARNING] No events found - synergy detection needs events!")
            else:
                print(f"   [WARNING] Failed to get events: {response.status_code}")
        except Exception as e:
            print(f"   [ERROR] Error getting events: {e}")
        
        print("\n" + "=" * 80)
        print("Diagnosis Complete")
        print("=" * 80)
        print("\nRecommendations:")
        print("  1. Check if 'Run Analysis' button is executing full synergy detection")
        print("  2. Verify device pair detection is enabled in pattern_analysis.py")
        print("  3. Check if filters (same_area_required, min_confidence) are too restrictive")
        print("  4. Verify events contain device interactions (not just system events)")
        print("  5. Check if existing automations are blocking new synergy detection")

if __name__ == "__main__":
    asyncio.run(diagnose())
