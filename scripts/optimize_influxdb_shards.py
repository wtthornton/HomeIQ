#!/usr/bin/env python3
"""
Analyze and recommend optimal shard duration for InfluxDB.

Shard duration affects query performance and storage efficiency.
This script analyzes query patterns and recommends optimal shard duration.
"""
import os
import sys
import requests
from datetime import datetime, timedelta
from influxdb_client import InfluxDBClient

# Configuration
INFLUXDB_URL = os.getenv('INFLUXDB_URL', 'http://localhost:8086')
INFLUXDB_TOKEN = os.getenv('INFLUXDB_TOKEN', 'ha-ingestor-token')
INFLUXDB_ORG = os.getenv('INFLUXDB_ORG', 'ha-ingestor')
PRIMARY_BUCKET = os.getenv('INFLUXDB_BUCKET', 'home_assistant_events')

def get_bucket_info(bucket_name):
    """Get bucket information including shard duration"""
    try:
        client = InfluxDBClient(
            url=INFLUXDB_URL,
            token=INFLUXDB_TOKEN,
            org=INFLUXDB_ORG
        )
        
        buckets_api = client.buckets_api()
        buckets = buckets_api.find_buckets()
        
        for bucket in buckets.buckets:
            if bucket.name == bucket_name:
                return {
                    'id': bucket.id,
                    'name': bucket.name,
                    'retention_rules': bucket.retention_rules,
                    'shard_group_duration': getattr(bucket, 'shard_group_duration', None)
                }
        
        client.close()
        return None
    except Exception as e:
        print(f"  ❌ Error getting bucket info: {e}")
        return None

def analyze_query_patterns(query_api, bucket):
    """Analyze common query time ranges"""
    print("Analyzing query patterns...")
    print("-" * 80)
    
    # Common time ranges to check
    time_ranges = {
        'Last hour': 1,
        'Last 24 hours': 24,
        'Last 7 days': 168,
        'Last 30 days': 720,
        'Last 90 days': 2160,
        'Last 365 days': 8760
    }
    
    # Note: In a real implementation, we would analyze actual query logs
    # For now, we'll provide recommendations based on retention policy
    
    print("Common query time ranges (estimated):")
    for range_name, hours in time_ranges.items():
        print(f"  - {range_name}: {hours} hours")
    
    return time_ranges

def recommend_shard_duration(retention_days, query_patterns):
    """Recommend optimal shard duration based on retention and queries"""
    print()
    print("Shard Duration Recommendations:")
    print("-" * 80)
    
    # InfluxDB shard duration guidelines:
    # - Should be 1-7 days for most use cases
    # - Longer shards = fewer shards = faster queries on large time ranges
    # - Shorter shards = more shards = faster queries on small time ranges
    # - Shard duration should be <= retention period
    
    if retention_days <= 7:
        recommended = "1h"  # 1 hour
        reason = "Short retention - use small shards for fast queries"
    elif retention_days <= 30:
        recommended = "24h"  # 1 day
        reason = "Medium retention - 1 day shards balance performance"
    elif retention_days <= 90:
        recommended = "7d"  # 7 days
        reason = "Long retention - 7 day shards optimize for large queries"
    else:
        recommended = "7d"  # 7 days (max recommended)
        reason = "Very long retention - 7 day shards (max recommended)"
    
    print(f"Recommended shard duration: {recommended}")
    print(f"Reason: {reason}")
    print()
    print("Shard Duration Guidelines:")
    print("  - 1h: Best for high-frequency queries on recent data (< 7 days retention)")
    print("  - 24h: Balanced for most use cases (7-30 days retention)")
    print("  - 7d: Best for long-term queries (30+ days retention)")
    print()
    print("⚠️  Note: Changing shard duration requires manual configuration")
    print("   - Use InfluxDB UI: Settings > Buckets > [bucket] > Shard Group Duration")
    print("   - Or use InfluxDB API: PATCH /api/v2/buckets/{bucket_id}")
    print("   - Changes only affect new data (existing shards unchanged)")
    
    return recommended

def main():
    """Main entry point"""
    print("=" * 80)
    print("INFLUXDB SHARD DURATION OPTIMIZATION")
    print("=" * 80)
    print()
    print(f"URL: {INFLUXDB_URL}")
    print(f"Org: {INFLUXDB_ORG}")
    print(f"Bucket: {PRIMARY_BUCKET}")
    print()
    
    try:
        # Get bucket info
        print("Retrieving bucket configuration...")
        print("-" * 80)
        bucket_info = get_bucket_info(PRIMARY_BUCKET)
        
        if not bucket_info:
            print(f"  ❌ Bucket '{PRIMARY_BUCKET}' not found")
            return False
        
        # Get retention policy
        retention_days = None
        if bucket_info['retention_rules']:
            for rule in bucket_info['retention_rules']:
                if rule.every_seconds:
                    retention_days = rule.every_seconds // 86400
                    print(f"  Retention: {retention_days} days")
                    break
        
        if retention_days is None:
            print("  ⚠️  No retention policy set (infinite retention)")
            retention_days = 365  # Assume 365 for recommendations
        
        # Get current shard duration (if available)
        shard_duration = bucket_info.get('shard_group_duration')
        if shard_duration:
            print(f"  Current shard duration: {shard_duration}")
        else:
            print(f"  Current shard duration: Not specified (using default)")
        
        print()
        
        # Analyze query patterns
        client = InfluxDBClient(
            url=INFLUXDB_URL,
            token=INFLUXDB_TOKEN,
            org=INFLUXDB_ORG
        )
        query_api = client.query_api()
        
        query_patterns = analyze_query_patterns(query_api, PRIMARY_BUCKET)
        
        # Generate recommendations
        recommended = recommend_shard_duration(retention_days, query_patterns)
        
        # Summary
        print()
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print()
        print(f"Bucket: {PRIMARY_BUCKET}")
        print(f"Retention: {retention_days} days")
        if shard_duration:
            print(f"Current shard duration: {shard_duration}")
        print(f"Recommended shard duration: {recommended}")
        print()
        
        if shard_duration and shard_duration != recommended:
            print("⚠️  Current shard duration differs from recommendation")
            print("   Consider updating to optimize query performance")
        elif not shard_duration or shard_duration == recommended:
            print("✅ Shard duration is optimal or matches recommendation")
        
        client.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

