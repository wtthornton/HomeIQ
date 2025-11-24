#!/usr/bin/env python3
"""
Verify tag completeness in InfluxDB.

This script checks if device_id and area_id tags are populated in InfluxDB events
and reports on tag completeness by time period.
"""
import os
import sys
from datetime import datetime, timedelta
from influxdb_client import InfluxDBClient
from influxdb_client.client.query_api import QueryApi

# Configuration
INFLUXDB_URL = os.getenv('INFLUXDB_URL', 'http://influxdb:8086')
INFLUXDB_TOKEN = os.getenv('INFLUXDB_TOKEN', 'ha-ingestor-token')
INFLUXDB_ORG = os.getenv('INFLUXDB_ORG', 'ha-ingestor')
PRIMARY_BUCKET = os.getenv('INFLUXDB_BUCKET', 'home_assistant_events')

def check_tag_completeness(query_api, bucket, tag_name, time_range_hours=24):
    """Check completeness of a specific tag"""
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=time_range_hours)
    
    # Flux query to count total records and records with the tag
    query = f'''
    from(bucket: "{bucket}")
      |> range(start: {start_time.isoformat()}Z, stop: {end_time.isoformat()}Z)
      |> filter(fn: (r) => r._measurement == "home_assistant_events")
      |> group()
      |> count()
    '''
    
    try:
        # Get total count
        total_result = list(query_api.query(query, org=INFLUXDB_ORG))
        total = 0
        if total_result:
            for table in total_result:
                for record in table.records:
                    total = int(record.get_value())
        
        # Get count with tag
        query_tagged = f'''
        from(bucket: "{bucket}")
          |> range(start: {start_time.isoformat()}Z, stop: {end_time.isoformat()}Z)
          |> filter(fn: (r) => r._measurement == "home_assistant_events")
          |> filter(fn: (r) => exists r.{tag_name})
          |> group()
          |> count()
        '''
        
        tagged_result = list(query_api.query(query_tagged, org=INFLUXDB_ORG))
        tagged = 0
        if tagged_result:
            for table in tagged_result:
                for record in table.records:
                    tagged = int(record.get_value())
        
        missing = total - tagged
        completeness = (tagged / total * 100) if total > 0 else 0.0
        
        return {
            'total': total,
            'tagged': tagged,
            'missing': missing,
            'completeness': completeness
        }
    except Exception as e:
        print(f"  ❌ Error checking {tag_name}: {e}")
        return None

def check_tag_by_time_period(query_api, bucket, tag_name):
    """Check tag completeness by time period (last 24h, 7d, 30d)"""
    periods = [
        ('Last 24 hours', 24),
        ('Last 7 days', 168),
        ('Last 30 days', 720)
    ]
    
    results = {}
    for period_name, hours in periods:
        result = check_tag_completeness(query_api, bucket, tag_name, hours)
        if result:
            results[period_name] = result
    
    return results

def get_tag_value_distribution(query_api, bucket, tag_name, limit=20):
    """Get distribution of tag values"""
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=24)
    
    query = f'''
    from(bucket: "{bucket}")
      |> range(start: {start_time.isoformat()}Z, stop: {end_time.isoformat()}Z)
      |> filter(fn: (r) => r._measurement == "home_assistant_events")
      |> filter(fn: (r) => exists r.{tag_name})
      |> group(columns: ["{tag_name}"])
      |> count()
      |> sort(columns: ["_value"], desc: true)
      |> limit(n: {limit})
    '''
    
    try:
        result = list(query_api.query(query, org=INFLUXDB_ORG))
        distribution = []
        if result:
            for table in result:
                for record in table.records:
                    tag_value = record.values.get(tag_name, 'N/A')
                    count = int(record.get_value())
                    distribution.append({tag_name: tag_value, 'count': count})
        return distribution
    except Exception as e:
        print(f"  ⚠️  Could not get distribution for {tag_name}: {e}")
        return []

def main():
    """Main entry point"""
    print("=" * 80)
    print("VERIFYING INFLUXDB TAG COMPLETENESS")
    print("=" * 80)
    print()
    print(f"URL: {INFLUXDB_URL}")
    print(f"Org: {INFLUXDB_ORG}")
    print(f"Bucket: {PRIMARY_BUCKET}")
    print()
    
    try:
        client = InfluxDBClient(
            url=INFLUXDB_URL,
            token=INFLUXDB_TOKEN,
            org=INFLUXDB_ORG
        )
        query_api = client.query_api()
        
        tags_to_check = ['device_id', 'area_id']
        overall_results = {}
        
        for tag_name in tags_to_check:
            print(f"Checking {tag_name} tag...")
            print("-" * 80)
            
            # Check completeness by time period
            period_results = check_tag_by_time_period(query_api, PRIMARY_BUCKET, tag_name)
            
            for period_name, result in period_results.items():
                print(f"\n{period_name}:")
                print(f"  Total records: {result['total']:,}")
                print(f"  Tagged records: {result['tagged']:,}")
                print(f"  Missing tags: {result['missing']:,}")
                print(f"  Completeness: {result['completeness']:.2f}%")
                
                if result['completeness'] < 95.0:
                    print(f"  ⚠️  WARNING: Completeness below 95% threshold!")
                elif result['completeness'] >= 95.0:
                    print(f"  ✅ Completeness meets threshold (≥95%)")
            
            # Get tag value distribution (for last 24h)
            print(f"\nTop {tag_name} values (last 24h):")
            distribution = get_tag_value_distribution(query_api, PRIMARY_BUCKET, tag_name, limit=10)
            if distribution:
                for i, item in enumerate(distribution[:10], 1):
                    tag_value = item.get(tag_name, 'N/A')
                    count = item.get('count', 0)
                    print(f"  {i}. {tag_value}: {count:,} records")
            else:
                print(f"  (No data available)")
            
            # Store overall result (last 24h)
            if 'Last 24 hours' in period_results:
                overall_results[tag_name] = period_results['Last 24 hours']
            
            print()
        
        # Summary
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print()
        
        all_meet_threshold = True
        for tag_name, result in overall_results.items():
            status = "✅" if result['completeness'] >= 95.0 else "⚠️"
            print(f"{status} {tag_name}: {result['completeness']:.2f}% complete ({result['tagged']:,}/{result['total']:,})")
            if result['completeness'] < 95.0:
                all_meet_threshold = False
        
        print()
        if all_meet_threshold:
            print("✅ All tags meet the 95% completeness threshold")
        else:
            print("⚠️  Some tags are below the 95% completeness threshold")
            print("   Investigate event processing pipeline for missing tag population")
        
        client.close()
        return all_meet_threshold
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

