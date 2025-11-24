#!/usr/bin/env python3
"""
Fix InfluxDB quality issues by applying recommendations.

This script:
1. Sets retention policies for buckets
2. Verifies bucket configuration
3. Provides summary of changes

Usage:
    docker exec homeiq-data-api python /tmp/fix_influxdb_quality.py
"""
import os
import sys

try:
    from influxdb_client import InfluxDBClient
    from influxdb_client.client.exceptions import InfluxDBError
except ImportError:
    print("❌ ERROR: influxdb_client not installed")
    print("   Install with: pip install influxdb-client")
    sys.exit(1)

# Configuration
INFLUXDB_URL = os.getenv('INFLUXDB_URL', 'http://localhost:8086')
INFLUXDB_TOKEN = os.getenv('INFLUXDB_TOKEN', 'ha-ingestor-token')
INFLUXDB_ORG = os.getenv('INFLUXDB_ORG', 'ha-ingestor')

# Retention policies (in seconds)
RETENTION_90_DAYS = 90 * 24 * 60 * 60  # 90 days in seconds
RETENTION_365_DAYS = 365 * 24 * 60 * 60  # 365 days in seconds

def fix_influxdb_quality():
    """Apply all InfluxDB quality recommendations"""
    print("=" * 80)
    print("FIXING INFLUXDB QUALITY ISSUES")
    print("=" * 80)
    print()
    print(f"URL: {INFLUXDB_URL}")
    print(f"Org: {INFLUXDB_ORG}")
    print()
    
    changes_applied = []
    errors = []
    
    try:
        client = InfluxDBClient(
            url=INFLUXDB_URL,
            token=INFLUXDB_TOKEN,
            org=INFLUXDB_ORG,
            timeout=30000
        )
        
        # Check connection
        print("Step 1: Checking Connection")
        print("-" * 80)
        try:
            health = client.health()
            if health.status == "pass":
                print("  ✅ InfluxDB connection: OK")
            else:
                print(f"  ❌ InfluxDB health check: {health.status}")
                return False
        except Exception as e:
            print(f"  ❌ Connection failed: {e}")
            return False
        
        print()
        
        # Get buckets API
        buckets_api = client.buckets_api()
        
        # Step 2: Set retention policy for home_assistant_events
        print("Step 2: Setting Retention Policy for home_assistant_events")
        print("-" * 80)
        
        try:
            buckets = buckets_api.find_buckets()
            home_assistant_bucket = None
            
            for bucket in buckets.buckets:
                if bucket.name == "home_assistant_events":
                    home_assistant_bucket = bucket
                    break
            
            if not home_assistant_bucket:
                errors.append("home_assistant_events bucket not found")
                print("  ❌ home_assistant_events bucket not found")
            else:
                # Check current retention
                current_retention = None
                if home_assistant_bucket.retention_rules:
                    for rule in home_assistant_bucket.retention_rules:
                        if rule.every_seconds:
                            current_retention = rule.every_seconds // 86400
                            print(f"  Current retention: {current_retention} days")
                
                if current_retention is None or current_retention != 90:
                    print("  Current retention: Infinite" if current_retention is None else f"  Current retention: {current_retention} days")
                    # Create retention rule using the bucket's existing structure
                    # The retention_rules is a list of rule objects
                    class RetentionRule:
                        def __init__(self, every_seconds):
                            self.every_seconds = every_seconds
                            self.type = "expire"
                    
                    retention_rule = RetentionRule(RETENTION_90_DAYS)
                    home_assistant_bucket.retention_rules = [retention_rule]
                    buckets_api.update_bucket(bucket=home_assistant_bucket)
                    if current_retention is None:
                        changes_applied.append(f"home_assistant_events: Set retention to 90 days")
                        print(f"  ✅ Set retention to 90 days")
                    else:
                        changes_applied.append(f"home_assistant_events: Updated retention from {current_retention} to 90 days")
                        print(f"  ✅ Updated retention from {current_retention} to 90 days")
                else:
                    print(f"  ✅ Retention already set to 90 days")
        except Exception as e:
            errors.append(f"Failed to set retention for home_assistant_events: {e}")
            print(f"  ❌ Error: {e}")
        
        print()
        
        # Step 3: Set retention policy for weather_data
        print("Step 3: Setting Retention Policy for weather_data")
        print("-" * 80)
        
        try:
            buckets = buckets_api.find_buckets()
            weather_bucket = None
            
            for bucket in buckets.buckets:
                if bucket.name == "weather_data":
                    weather_bucket = bucket
                    break
            
            if not weather_bucket:
                print("  ⚠️  weather_data bucket not found (may not exist)")
            else:
                # Check current retention
                current_retention = None
                if weather_bucket.retention_rules:
                    for rule in weather_bucket.retention_rules:
                        if rule.every_seconds:
                            current_retention = rule.every_seconds // 86400
                            print(f"  Current retention: {current_retention} days")
                
                if current_retention is None or current_retention != 365:
                    print("  Current retention: Infinite" if current_retention is None else f"  Current retention: {current_retention} days")
                    # Create retention rule using the bucket's existing structure
                    class RetentionRule:
                        def __init__(self, every_seconds):
                            self.every_seconds = every_seconds
                            self.type = "expire"
                    
                    retention_rule = RetentionRule(RETENTION_365_DAYS)
                    weather_bucket.retention_rules = [retention_rule]
                    buckets_api.update_bucket(bucket=weather_bucket)
                    if current_retention is None:
                        changes_applied.append(f"weather_data: Set retention to 365 days")
                        print(f"  ✅ Set retention to 365 days")
                    else:
                        changes_applied.append(f"weather_data: Updated retention from {current_retention} to 365 days")
                        print(f"  ✅ Updated retention from {current_retention} to 365 days")
                else:
                    print(f"  ✅ Retention already set to 365 days")
        except Exception as e:
            errors.append(f"Failed to set retention for weather_data: {e}")
            print(f"  ❌ Error: {e}")
        
        print()
        
        # Step 4: Verify changes
        print("Step 4: Verifying Changes")
        print("-" * 80)
        
        try:
            buckets = buckets_api.find_buckets()
            for bucket in buckets.buckets:
                if bucket.name in ["home_assistant_events", "weather_data"]:
                    retention_days = None
                    if bucket.retention_rules:
                        for rule in bucket.retention_rules:
                            if rule.every_seconds:
                                retention_days = rule.every_seconds // 86400
                    
                    if retention_days:
                        print(f"  ✅ {bucket.name}: {retention_days} days retention")
                    else:
                        print(f"  ⚠️  {bucket.name}: Infinite retention (not set)")
        except Exception as e:
            print(f"  ⚠️  Could not verify: {e}")
        
        print()
        
        # Summary
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print()
        
        if changes_applied:
            print("✅ Changes Applied:")
            for change in changes_applied:
                print(f"  - {change}")
            print()
        else:
            print("✅ No changes needed - retention policies already configured")
            print()
        
        if errors:
            print("⚠️  Errors:")
            for error in errors:
                print(f"  - {error}")
            print()
        
        client.close()
        return len(errors) == 0
        
    except InfluxDBError as e:
        print(f"❌ InfluxDB Error: {e}")
        return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main entry point"""
    success = fix_influxdb_quality()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()

