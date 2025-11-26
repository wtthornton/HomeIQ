#!/usr/bin/env python3
"""
Analyze Production Device Type Event Frequencies

Analyzes production HA data to determine realistic event frequencies per device type.
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from collections import defaultdict

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "services" / "ai-automation-service" / "src"))

from clients.data_api_client import DataAPIClient
import pandas as pd


async def analyze_device_type_frequencies():
    """Analyze event frequencies by device type from production data"""
    
    print("=" * 70)
    print("Device Type Event Frequency Analysis")
    print("=" * 70)
    print()
    
    # Initialize Data API client
    data_api = DataAPIClient(
        influxdb_url=os.getenv("INFLUXDB_URL", "http://localhost:8086"),
        influxdb_token=os.getenv("INFLUXDB_TOKEN", "ha-ingestor-token"),
        influxdb_org=os.getenv("INFLUXDB_ORG", "ha-ingestor"),
        influxdb_bucket=os.getenv("INFLUXDB_BUCKET", "home_assistant_events")
    )
    
    # Analyze last 7 days
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=7)
    
    print(f"📅 Analysis Period: {start_time.strftime('%Y-%m-%d')} to {end_time.strftime('%Y-%m-%d')}")
    print(f"   (7 days)")
    print()
    
    try:
        # Fetch events
        print("📊 Fetching events from InfluxDB...")
        events_df = await data_api.fetch_events(
            start_time=start_time,
            end_time=end_time,
            limit=1000000
        )
        
        if events_df.empty:
            print("⚠️  No events found in production InfluxDB")
            return
        
        total_events = len(events_df)
        days = 7
        print(f"✅ Fetched {total_events:,} events")
        print()
        
        # Extract domain from entity_id
        if 'entity_id' in events_df.columns:
            events_df['domain'] = events_df['entity_id'].str.split('.').str[0]
        
        # Group by domain and entity
        domain_stats = defaultdict(lambda: {'entities': set(), 'events': 0})
        entity_stats = defaultdict(lambda: {'domain': '', 'events': 0})
        
        for _, row in events_df.iterrows():
            entity_id = row.get('entity_id', 'unknown')
            domain = row.get('domain', 'unknown')
            
            domain_stats[domain]['entities'].add(entity_id)
            domain_stats[domain]['events'] += 1
            
            entity_stats[entity_id]['domain'] = domain
            entity_stats[entity_id]['events'] += 1
        
        # Calculate statistics
        print("=" * 70)
        print("📊 Event Frequency by Device Type (Domain)")
        print("=" * 70)
        print()
        
        domain_results = []
        for domain, stats in sorted(domain_stats.items(), key=lambda x: x[1]['events'], reverse=True):
            entity_count = len(stats['entities'])
            total_events_domain = stats['events']
            events_per_day = total_events_domain / days
            events_per_entity_per_day = events_per_day / entity_count if entity_count > 0 else 0
            
            domain_results.append({
                'domain': domain,
                'entities': entity_count,
                'total_events': total_events_domain,
                'events_per_day': events_per_day,
                'events_per_entity_per_day': events_per_entity_per_day
            })
            
            print(f"{domain:20s} | {entity_count:4d} entities | {total_events_domain:6,} events | "
                  f"{events_per_day:7.1f}/day | {events_per_entity_per_day:6.2f}/entity/day")
        
        print()
        
        # Top entities by event count
        print("=" * 70)
        print("🔝 Top 20 Entities by Event Count")
        print("=" * 70)
        print()
        
        top_entities = sorted(entity_stats.items(), key=lambda x: x[1]['events'], reverse=True)[:20]
        for entity_id, stats in top_entities:
            domain = stats['domain']
            events = stats['events']
            events_per_day = events / days
            print(f"{entity_id:50s} | {domain:15s} | {events:6,} events | {events_per_day:7.1f}/day")
        
        print()
        
        # Recommendations
        print("=" * 70)
        print("💡 Recommended Event Frequencies per Device Type")
        print("=" * 70)
        print()
        print("Based on production data (7.5 events/device/day average):")
        print()
        
        # Categorize by typical event frequency
        high_frequency = ['sensor', 'binary_sensor', 'image', 'automation']
        medium_frequency = ['light', 'switch', 'media_player', 'cover']
        low_frequency = ['climate', 'lock', 'vacuum', 'scene', 'select']
        
        for domain_result in domain_results:
            domain = domain_result['domain']
            avg_events = domain_result['events_per_entity_per_day']
            
            if domain in high_frequency:
                category = "HIGH"
                recommended = max(avg_events * 0.5, 10)  # At least 10/day
            elif domain in medium_frequency:
                category = "MEDIUM"
                recommended = max(avg_events * 0.5, 3)  # At least 3/day
            elif domain in low_frequency:
                category = "LOW"
                recommended = max(avg_events * 0.5, 1)  # At least 1/day
            else:
                category = "VARIABLE"
                recommended = max(avg_events * 0.5, 2)  # At least 2/day
            
            print(f"{domain:20s} | {category:8s} | Production: {avg_events:6.2f}/day | "
                  f"Recommended: {recommended:6.2f}/day")
        
        print()
        
        # Summary statistics
        print("=" * 70)
        print("📈 Summary Statistics")
        print("=" * 70)
        print()
        
        avg_events_per_entity = sum(r['events_per_entity_per_day'] for r in domain_results) / len(domain_results)
        print(f"Average events per entity per day: {avg_events_per_entity:.2f}")
        print(f"Total unique entities: {sum(r['entities'] for r in domain_results):,}")
        print(f"Total events (7 days): {total_events:,}")
        print(f"Events per day (total): {total_events / days:,.1f}")
        print()
        
    except Exception as e:
        print(f"❌ Error analyzing events: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import asyncio
    asyncio.run(analyze_device_type_frequencies())

