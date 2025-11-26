#!/usr/bin/env python3
"""
Analyze Production Home Assistant Event Statistics

Compares production HA event patterns with test dataset configuration.
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "services" / "ai-automation-service" / "src"))

from clients.data_api_client import DataAPIClient
import pandas as pd


async def analyze_production_events():
    """Analyze production HA events and compare with test configuration"""
    
    print("=" * 70)
    print("Production Home Assistant Event Analysis")
    print("=" * 70)
    print()
    
    # Initialize Data API client (uses production bucket)
    data_api = DataAPIClient(
        influxdb_url=os.getenv("INFLUXDB_URL", "http://localhost:8086"),
        influxdb_token=os.getenv("INFLUXDB_TOKEN", "ha-ingestor-token"),
        influxdb_org=os.getenv("INFLUXDB_ORG", "ha-ingestor"),
        influxdb_bucket=os.getenv("INFLUXDB_BUCKET", "home_assistant_events")
    )
    
    # Analyze last 7 days (matches test configuration)
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=7)
    
    print(f"📅 Analysis Period: {start_time.strftime('%Y-%m-%d')} to {end_time.strftime('%Y-%m-%d')}")
    print(f"   (7 days - matches test configuration)")
    print()
    
    try:
        # Fetch events
        print("📊 Fetching events from InfluxDB...")
        events_df = await data_api.fetch_events(
            start_time=start_time,
            end_time=end_time,
            limit=1000000  # Large limit to get all events
        )
        
        if events_df.empty:
            print("⚠️  No events found in production InfluxDB")
            print("   Check that websocket-ingestion is running and connected to HA")
            return
        
        total_events = len(events_df)
        print(f"✅ Fetched {total_events:,} events")
        print()
        
        # Calculate statistics
        days = 7
        events_per_day = total_events / days
        
        print("=" * 70)
        print("📈 Event Statistics")
        print("=" * 70)
        print(f"Total Events (7 days):     {total_events:,}")
        print(f"Events per Day:            {events_per_day:,.1f}")
        print(f"Events per Hour:           {events_per_day / 24:,.1f}")
        print(f"Events per Minute:         {events_per_day / 1440:.2f}")
        print()
        
        # Device/Entity analysis
        if 'entity_id' in events_df.columns:
            unique_entities = events_df['entity_id'].nunique()
            print("=" * 70)
            print("🏠 Device/Entity Statistics")
            print("=" * 70)
            print(f"Unique Entities:          {unique_entities:,}")
            print(f"Events per Entity/Day:    {events_per_day / unique_entities:.2f}")
            print()
            
            # Top entities by event count
            entity_counts = events_df['entity_id'].value_counts().head(20)
            print("Top 20 Entities by Event Count:")
            for entity, count in entity_counts.items():
                pct = (count / total_events) * 100
                print(f"  {entity:50s} {count:6,} ({pct:5.2f}%)")
            print()
        
        # Domain analysis
        if 'domain' in events_df.columns:
            domain_counts = events_df['domain'].value_counts()
            print("=" * 70)
            print("🔌 Domain Statistics")
            print("=" * 70)
            print(f"Unique Domains:           {len(domain_counts)}")
            print()
            print("Top Domains by Event Count:")
            for domain, count in domain_counts.head(15).items():
                pct = (count / total_events) * 100
                print(f"  {domain:20s} {count:6,} ({pct:5.2f}%)")
            print()
        
        # Time distribution
        if 'timestamp' in events_df.columns:
            events_df['hour'] = pd.to_datetime(events_df['timestamp']).dt.hour
            hourly_dist = events_df['hour'].value_counts().sort_index()
            
            print("=" * 70)
            print("⏰ Hourly Distribution (Events per Hour)")
            print("=" * 70)
            for hour in range(24):
                count = hourly_dist.get(hour, 0)
                bar = "█" * int((count / hourly_dist.max()) * 50) if hourly_dist.max() > 0 else ""
                print(f"  {hour:2d}:00  {count:6,}  {bar}")
            print()
        
        # Compare with test configuration
        print("=" * 70)
        print("🔬 Comparison with Test Configuration")
        print("=" * 70)
        print()
        
        test_events_per_day = 50
        test_total = 350  # 7 days × 50
        
        print(f"Test Configuration:")
        print(f"  Events per Day:          {test_events_per_day:,}")
        print(f"  Total (7 days):          {test_total:,}")
        print(f"  Devices (home1-us):      14")
        print(f"  Events per Device/Day:   {test_events_per_day / 14:.2f}")
        print()
        
        print(f"Production (Actual):")
        print(f"  Events per Day:          {events_per_day:,.1f}")
        print(f"  Total (7 days):          {total_events:,}")
        if 'entity_id' in events_df.columns:
            print(f"  Unique Entities:         {unique_entities:,}")
            print(f"  Events per Entity/Day:  {events_per_day / unique_entities:.2f}")
        print()
        
        # Ratio analysis
        ratio = events_per_day / test_events_per_day
        print(f"📊 Ratio Analysis:")
        print(f"  Production is {ratio:.1f}x the test configuration")
        print()
        
        if ratio < 0.5:
            print("  ⚠️  Production has FEWER events than test")
            print("     Test may be over-generating events")
        elif ratio < 2.0:
            print("  ✅ Production and test are SIMILAR")
            print("     Test configuration is realistic")
        else:
            print("  ⚠️  Production has MORE events than test")
            print("     Test may be under-generating events")
            print(f"     Consider increasing test to {int(events_per_day * 0.8):,} events/day")
        print()
        
        # Recommendations
        print("=" * 70)
        print("💡 Recommendations")
        print("=" * 70)
        print()
        
        if events_per_day < 50:
            print("  ⚠️  Production has low event volume")
            print("     Current test (50/day) may be appropriate")
        elif events_per_day < 150:
            print("  ✅ Production has moderate event volume")
            print(f"     Recommend test: {int(events_per_day * 0.7):,}-{int(events_per_day * 0.9):,} events/day")
        else:
            print("  ⚠️  Production has high event volume")
            print(f"     Recommend test: {int(events_per_day * 0.5):,}-{int(events_per_day * 0.7):,} events/day")
            print("     (Test doesn't need to match exactly, but should be realistic)")
        print()
        
        # Pattern detection implications
        print("=" * 70)
        print("🎯 Pattern Detection Implications")
        print("=" * 70)
        print()
        
        if 'entity_id' in events_df.columns:
            events_per_entity_per_day = events_per_day / unique_entities
            print(f"Events per Entity per Day: {events_per_entity_per_day:.2f}")
            print()
            
            if events_per_entity_per_day < 2:
                print("  ⚠️  Very sparse events - pattern detection may struggle")
                print("     min_support=5 may be too high")
            elif events_per_entity_per_day < 5:
                print("  ⚠️  Sparse events - pattern detection may be marginal")
                print("     Consider min_support=3 for testing")
            elif events_per_entity_per_day < 10:
                print("  ✅ Moderate event density - pattern detection should work")
                print("     min_support=5 is reasonable")
            else:
                print("  ✅ High event density - pattern detection should work well")
                print("     min_support=5 is appropriate")
        print()
        
    except Exception as e:
        print(f"❌ Error analyzing events: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import asyncio
    asyncio.run(analyze_production_events())

