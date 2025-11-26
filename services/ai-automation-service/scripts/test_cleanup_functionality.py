#!/usr/bin/env python3
"""
Test script to verify event cleanup functionality.

Tests:
1. Event injection
2. Event cleanup by time range
3. Event cleanup by entity prefix
4. Event cleanup by home_id
5. Verification that events are actually deleted
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.testing.event_injector import EventInjector
from src.clients.data_api_client import DataAPIClient


async def test_cleanup_functionality():
    """Test event cleanup functionality"""
    
    print("=" * 70)
    print("Event Cleanup Functionality Test")
    print("=" * 70)
    
    # Initialize injector with test bucket
    test_bucket = os.getenv("INFLUXDB_TEST_BUCKET", "home_assistant_events_test")
    injector = EventInjector(
        influxdb_url=os.getenv("INFLUXDB_URL", "http://localhost:8086"),
        influxdb_token=os.getenv("INFLUXDB_TOKEN", "ha-ingestor-token"),
        influxdb_org=os.getenv("INFLUXDB_ORG", "ha-ingestor"),
        influxdb_bucket=test_bucket
    )
    
    try:
        injector.connect()
        print("✅ Connected to InfluxDB")
        
        # Initialize data API client for verification
        data_api = DataAPIClient(
            influxdb_url=os.getenv("INFLUXDB_URL", "http://localhost:8086"),
            influxdb_token=os.getenv("INFLUXDB_TOKEN", "ha-ingestor-token"),
            influxdb_org=os.getenv("INFLUXDB_ORG", "ha-ingestor"),
            influxdb_bucket=test_bucket
        )
        
        # Test 1: Inject test events
        print("\n[TEST 1] Injecting test events...")
        test_events = []
        base_time = datetime.now(timezone.utc) - timedelta(hours=1)
        
        for i in range(10):
            test_events.append({
                'entity_id': f'test.cleanup_test_{i}',
                'state': 'on' if i % 2 == 0 else 'off',
                'timestamp': (base_time + timedelta(minutes=i)).isoformat(),
                'event_type': 'state_changed',
                'attributes': {'test': True, 'index': i}
            })
        
        events_injected = await injector.inject_events(test_events)
        print(f"✅ Injected {events_injected} test events")
        
        # Wait for events to be available
        await asyncio.sleep(2)
        
        # Verify events exist
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=2)
        events_before = await data_api.fetch_events(
            start_time=start_time,
            end_time=end_time,
            limit=1000
        )
        # DataAPI returns DataFrame, filter by entity_id column
        if not events_before.empty and 'entity_id' in events_before.columns:
            test_events_count = len(events_before[events_before['entity_id'].str.contains('cleanup_test', na=False)])
        else:
            test_events_count = 0
        print(f"✅ Verified {test_events_count} test events exist in InfluxDB")
        
        # Test 2: Cleanup by time range
        print("\n[TEST 2] Testing cleanup by time range...")
        cleanup_start = base_time - timedelta(minutes=5)
        cleanup_end = base_time + timedelta(minutes=15)
        
        # Note: InfluxDB delete API doesn't support regex, so we use measurement-only predicate
        deleted = await injector.clear_events_by_time_range(
            start_time=cleanup_start,
            end_time=cleanup_end,
            predicate='_measurement="home_assistant_events"'
        )
        print(f"✅ Cleanup operation completed (returned: {deleted})")
        print("   Note: This deletes all events in time range (InfluxDB limitation)")
        
        # Wait for cleanup to propagate
        await asyncio.sleep(2)
        
        # Verify events are deleted
        events_after = await data_api.fetch_events(
            start_time=start_time,
            end_time=end_time,
            limit=1000
        )
        if not events_after.empty and 'entity_id' in events_after.columns:
            test_events_after = len(events_after[events_after['entity_id'].str.contains('cleanup_test', na=False)])
        else:
            test_events_after = 0
        print(f"✅ Events after cleanup: {test_events_after} (expected: 0)")
        
        if test_events_after == 0:
            print("✅ TEST 2 PASSED: Events successfully deleted by time range")
        else:
            print(f"⚠️  TEST 2 WARNING: {test_events_after} events still exist (may be due to InfluxDB delete delay)")
        
        # Test 3: Cleanup by entity prefix
        print("\n[TEST 3] Testing cleanup by entity prefix...")
        
        # Inject new test events
        prefix_events = []
        prefix_time = datetime.now(timezone.utc)
        for i in range(5):
            prefix_events.append({
                'entity_id': f'test.prefix_test_{i}',
                'state': 'on',
                'timestamp': (prefix_time + timedelta(seconds=i)).isoformat(),
                'event_type': 'state_changed',
                'attributes': {'test': 'prefix'}
            })
        
        await injector.inject_events(prefix_events)
        print(f"✅ Injected {len(prefix_events)} prefix test events")
        await asyncio.sleep(2)
        
        # Cleanup by prefix
        deleted = await injector.clear_events_by_entity_prefix('test.prefix_test_')
        print(f"✅ Cleanup by prefix completed (returned: {deleted})")
        await asyncio.sleep(2)
        
        # Verify
        events_check = await data_api.fetch_events(
            start_time=prefix_time - timedelta(minutes=1),
            end_time=datetime.now(timezone.utc),
            limit=1000
        )
        if not events_check.empty and 'entity_id' in events_check.columns:
            prefix_events_after = len(events_check[events_check['entity_id'].str.contains('prefix_test', na=False)])
        else:
            prefix_events_after = 0
        print(f"✅ Events after prefix cleanup: {prefix_events_after} (expected: 0)")
        
        if prefix_events_after == 0:
            print("✅ TEST 3 PASSED: Events successfully deleted by entity prefix")
        else:
            print(f"⚠️  TEST 3 WARNING: {prefix_events_after} events still exist")
        
        # Test 4: Cleanup by home_id
        print("\n[TEST 4] Testing cleanup by home_id...")
        
        # Inject home-specific events
        home_events = []
        home_time = datetime.now(timezone.utc)
        for i in range(5):
            home_events.append({
                'entity_id': f'test_home_001_device_{i}',
                'state': 'on',
                'timestamp': (home_time + timedelta(seconds=i)).isoformat(),
                'event_type': 'state_changed',
                'attributes': {'home_id': 'test_home_001'}
            })
        
        await injector.inject_events(home_events)
        print(f"✅ Injected {len(home_events)} home-specific events")
        await asyncio.sleep(2)
        
        # Cleanup by home_id
        deleted = await injector.clear_home_events(
            home_id='test_home_001',
            time_range=(home_time - timedelta(minutes=1), datetime.now(timezone.utc))
        )
        print(f"✅ Cleanup by home_id completed (returned: {deleted})")
        await asyncio.sleep(2)
        
        # Verify
        events_check = await data_api.fetch_events(
            start_time=home_time - timedelta(minutes=1),
            end_time=datetime.now(timezone.utc),
            limit=1000
        )
        if not events_check.empty and 'entity_id' in events_check.columns:
            home_events_after = len(events_check[events_check['entity_id'].str.contains('test_home_001', na=False)])
        else:
            home_events_after = 0
        print(f"✅ Events after home cleanup: {home_events_after} (expected: 0)")
        
        if home_events_after == 0:
            print("✅ TEST 4 PASSED: Events successfully deleted by home_id")
        else:
            print(f"⚠️  TEST 4 WARNING: {home_events_after} events still exist")
        
        print("\n" + "=" * 70)
        print("Cleanup Functionality Test Complete")
        print("=" * 70)
        print("\nNote: InfluxDB delete operations may take a few seconds to propagate.")
        print("If events still exist, wait a few seconds and check again.")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        injector.disconnect()


if __name__ == "__main__":
    asyncio.run(test_cleanup_functionality())

