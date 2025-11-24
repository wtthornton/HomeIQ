#!/usr/bin/env python3
"""
Check InfluxDB for data quality issues.

This script:
1. Checks bucket configuration and retention policies
2. Analyzes data volume and distribution
3. Identifies missing or incomplete data
4. Checks for data gaps
5. Validates schema consistency
6. Provides recommendations

Usage:
    docker exec homeiq-influxdb python /app/check_influxdb_quality.py
    OR
    python scripts/check_influxdb_quality.py
"""
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

try:
    from influxdb_client import InfluxDBClient
    from influxdb_client.client.exceptions import InfluxDBError
except ImportError:
    print("❌ ERROR: influxdb_client not installed")
    print("   Install with: pip install influxdb-client")
    sys.exit(1)

# Configuration - try multiple token sources
INFLUXDB_URL = os.getenv('INFLUXDB_URL', 'http://localhost:8086')
INFLUXDB_TOKEN = (
    os.getenv('INFLUXDB_TOKEN') or 
    os.getenv('DOCKER_INFLUXDB_INIT_ADMIN_TOKEN') or 
    'homeiq-token'
)
INFLUXDB_ORG = os.getenv('INFLUXDB_ORG', 'homeiq')
PRIMARY_BUCKET = os.getenv('INFLUXDB_BUCKET', 'home_assistant_events')

def check_influxdb_quality():
    """Check InfluxDB for data quality issues"""
    print("=" * 80)
    print("INFLUXDB QUALITY CHECK")
    print("=" * 80)
    print()
    print(f"URL: {INFLUXDB_URL}")
    print(f"Org: {INFLUXDB_ORG}")
    print(f"Primary Bucket: {PRIMARY_BUCKET}")
    print()
    
    issues = []
    warnings = []
    info = []
    
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
                info.append("Connection: Healthy")
            else:
                issues.append(f"InfluxDB health check: {health.status}")
                print(f"  ❌ InfluxDB health check: {health.status}")
                return
        except Exception as e:
            issues.append(f"InfluxDB connection failed: {e}")
            print(f"  ❌ Connection failed: {e}")
            return
        
        print()
        
        # Get buckets
        print("Step 2: Checking Buckets")
        print("-" * 80)
        buckets_api = client.buckets_api()
        buckets = buckets_api.find_buckets()
        
        print(f"  Found {len(buckets.buckets)} bucket(s):")
        bucket_info = {}
        for bucket in buckets.buckets:
            retention_days = None
            if bucket.retention_rules:
                for rule in bucket.retention_rules:
                    if rule.every_seconds:
                        retention_days = rule.every_seconds // 86400
            bucket_info[bucket.name] = {
                'id': bucket.id,
                'retention_days': retention_days,
                'created': bucket.created_at
            }
            print(f"    - {bucket.name}")
            if retention_days:
                print(f"      Retention: {retention_days} days")
            else:
                print(f"      Retention: Infinite")
                warnings.append(f"{bucket.name}: No retention policy set (infinite retention)")
        
        if not any(b.name == PRIMARY_BUCKET for b in buckets.buckets):
            issues.append(f"Primary bucket '{PRIMARY_BUCKET}' not found")
            print(f"  ❌ Primary bucket '{PRIMARY_BUCKET}' not found!")
            return
        
        primary_bucket = next(b for b in buckets.buckets if b.name == PRIMARY_BUCKET)
        print(f"  ✅ Primary bucket '{PRIMARY_BUCKET}' found")
        print()
        
        # Query API
        query_api = client.query_api()
        
        # Check data volume
        print("Step 3: Checking Data Volume")
        print("-" * 80)
        
        # Check last 30 days
        query_30d = f'''
            from(bucket: "{PRIMARY_BUCKET}")
              |> range(start: -30d)
              |> count()
        '''
        
        try:
            result_30d = query_api.query(query_30d)
            total_records_30d = sum(len(list(table.records)) for table in result_30d)
            info.append(f"Last 30 days: {total_records_30d:,} records")
            print(f"  Last 30 days: {total_records_30d:,} records")
        except Exception as e:
            warnings.append(f"Could not query 30-day data: {e}")
            print(f"  ⚠️  Could not query 30-day data: {e}")
            total_records_30d = 0
        
        # Check last 7 days
        query_7d = f'''
            from(bucket: "{PRIMARY_BUCKET}")
              |> range(start: -7d)
              |> count()
        '''
        
        try:
            result_7d = query_api.query(query_7d)
            total_records_7d = sum(len(list(table.records)) for table in result_7d)
            info.append(f"Last 7 days: {total_records_7d:,} records")
            print(f"  Last 7 days: {total_records_7d:,} records")
        except Exception as e:
            warnings.append(f"Could not query 7-day data: {e}")
            print(f"  ⚠️  Could not query 7-day data: {e}")
            total_records_7d = 0
        
        # Check last 24 hours
        query_24h = f'''
            from(bucket: "{PRIMARY_BUCKET}")
              |> range(start: -24h)
              |> count()
        '''
        
        try:
            result_24h = query_api.query(query_24h)
            total_records_24h = sum(len(list(table.records)) for table in result_24h)
            info.append(f"Last 24 hours: {total_records_24h:,} records")
            print(f"  Last 24 hours: {total_records_24h:,} records")
        except Exception as e:
            warnings.append(f"Could not query 24-hour data: {e}")
            print(f"  ⚠️  Could not query 24-hour data: {e}")
            total_records_24h = 0
        
        if total_records_24h == 0 and total_records_7d == 0:
            issues.append("No data found in last 7 days - possible ingestion issue")
            print(f"  ❌ No data found in last 7 days!")
        elif total_records_24h == 0:
            warnings.append("No data in last 24 hours - possible recent ingestion issue")
            print(f"  ⚠️  No data in last 24 hours")
        
        print()
        
        # Check measurements
        print("Step 4: Checking Measurements")
        print("-" * 80)
        
        query_measurements = f'''
            from(bucket: "{PRIMARY_BUCKET}")
              |> range(start: -7d)
              |> keys()
              |> keep(columns: ["_measurement"])
              |> distinct()
        '''
        
        try:
            result_meas = query_api.query(query_measurements)
            measurements = set()
            for table in result_meas:
                for record in table.records:
                    if record.get_value():
                        measurements.add(record.get_value())
            
            print(f"  Found {len(measurements)} measurement(s) in last 7 days:")
            measurement_counts = {}
            for measurement in sorted(measurements):
                query_count = f'''
                    from(bucket: "{PRIMARY_BUCKET}")
                      |> range(start: -7d)
                      |> filter(fn: (r) => r["_measurement"] == "{measurement}")
                      |> count()
                '''
                try:
                    result_count = query_api.query(query_count)
                    count = sum(len(list(table.records)) for table in result_count)
                    measurement_counts[measurement] = count
                    print(f"    - {measurement}: {count:,} records")
                except Exception as e:
                    print(f"    - {measurement}: Error counting ({e})")
            
            if not measurements:
                issues.append("No measurements found in last 7 days")
                print(f"  ❌ No measurements found!")
            else:
                info.append(f"Measurements: {', '.join(sorted(measurements))}")
        
        except Exception as e:
            warnings.append(f"Could not query measurements: {e}")
            print(f"  ⚠️  Could not query measurements: {e}")
        
        print()
        
        # Check for data gaps (check hourly distribution)
        print("Step 5: Checking for Data Gaps")
        print("-" * 80)
        
        query_gaps = f'''
            from(bucket: "{PRIMARY_BUCKET}")
              |> range(start: -24h)
              |> aggregateWindow(every: 1h, fn: count, createEmpty: true)
              |> filter(fn: (r) => r._value == 0)
        '''
        
        try:
            result_gaps = query_api.query(query_gaps)
            gap_count = sum(len(list(table.records)) for table in result_gaps)
            if gap_count > 0:
                warnings.append(f"Found {gap_count} hours with no data in last 24 hours")
                print(f"  ⚠️  Found {gap_count} hour(s) with no data in last 24 hours")
            else:
                print(f"  ✅ No data gaps in last 24 hours")
        except Exception as e:
            warnings.append(f"Could not check for data gaps: {e}")
            print(f"  ⚠️  Could not check for data gaps: {e}")
        
        print()
        
        # Check tag cardinality (Database Optimization - 2025)
        print("Step 6: Checking Tag Cardinality")
        print("-" * 80)
        
        tags_to_check = ['entity_id', 'device_id', 'area_id', 'domain', 'event_type']
        cardinality_threshold = 10000  # InfluxDB best practice: tags should have <10,000 unique values
        
        for tag_name in tags_to_check:
            try:
                # Get distinct tag values by grouping and counting unique groups
                query_cardinality = f'''
                    from(bucket: "{PRIMARY_BUCKET}")
                      |> range(start: -7d)
                      |> filter(fn: (r) => exists r.{tag_name})
                      |> keep(columns: ["{tag_name}", "_time"])
                      |> group(columns: ["{tag_name}"])
                      |> group()
                      |> distinct(column: "{tag_name}")
                      |> count()
                '''
                
                result_cardinality = query_api.query(query_cardinality)
                cardinality = 0
                # Count the number of tables (each table represents a distinct tag value)
                table_count = 0
                record_count = 0
                for table in result_cardinality:
                    table_count += 1
                    for record in table.records:
                        record_count += 1
                        value = record.get_value()
                        if value is not None:
                            try:
                                cardinality = int(value)
                                break
                            except (ValueError, TypeError):
                                pass
                
                # If we didn't get a count value, use table count as fallback
                if cardinality == 0 and table_count > 0:
                    cardinality = table_count
                elif cardinality == 0 and record_count > 0:
                    cardinality = record_count
                
                status = "✅" if cardinality < cardinality_threshold else "⚠️"
                print(f"  {status} {tag_name}: {cardinality:,} unique values")
                
                if cardinality >= cardinality_threshold:
                    warnings.append(f"High cardinality tag '{tag_name}': {cardinality:,} values (threshold: {cardinality_threshold:,})")
                    print(f"     ⚠️  WARNING: Tag cardinality exceeds recommended threshold!")
                    print(f"        Consider moving to fields or implementing tag value limits")
                elif cardinality == 0:
                    warnings.append(f"Tag '{tag_name}' has no values in last 7 days")
                    print(f"     ⚠️  No values found in last 7 days")
                else:
                    info.append(f"Tag {tag_name}: {cardinality:,} values (within threshold)")
                    
            except Exception as e:
                warnings.append(f"Could not check cardinality for {tag_name}: {e}")
                print(f"  ⚠️  Could not check {tag_name} cardinality: {e}")
        
        print()
        
        # Check schema consistency (sample recent records)
        print("Step 7: Checking Schema Consistency")
        print("-" * 80)
        
        query_sample = f'''
            from(bucket: "{PRIMARY_BUCKET}")
              |> range(start: -1h)
              |> limit(n: 100)
        '''
        
        try:
            result_sample = query_api.query(query_sample)
            field_counts = defaultdict(set)
            tag_counts = defaultdict(set)
            
            for table in result_sample:
                for record in table.records:
                    measurement = record.get_measurement()
                    if measurement:
                        # Collect fields
                        for field in record.values:
                            if field.startswith('_') and field != '_time' and field != '_measurement' and field != '_field':
                                field_counts[measurement].add(field)
                        # Collect tags
                        for tag in record.values:
                            if not tag.startswith('_'):
                                tag_counts[measurement].add(tag)
            
            if field_counts or tag_counts:
                print(f"  Schema summary (from sample):")
                for measurement in sorted(set(list(field_counts.keys()) + list(tag_counts.keys()))):
                    fields = field_counts.get(measurement, set())
                    tags = tag_counts.get(measurement, set())
                    print(f"    - {measurement}:")
                    if fields:
                        print(f"      Fields: {len(fields)} ({', '.join(sorted(list(fields)[:5]))}{'...' if len(fields) > 5 else ''})")
                    if tags:
                        print(f"      Tags: {len(tags)} ({', '.join(sorted(list(tags)[:5]))}{'...' if len(tags) > 5 else ''})")
            else:
                warnings.append("Could not analyze schema - no recent data")
                print(f"  ⚠️  Could not analyze schema - no recent data")
        
        except Exception as e:
            warnings.append(f"Could not check schema: {e}")
            print(f"  ⚠️  Could not check schema: {e}")
        
        print()
        
        # Check for specific expected measurements
        print("Step 7: Checking Expected Measurements")
        print("-" * 80)
        
        expected_measurements = ['events', 'state_changes', 'devices', 'entities']
        if 'events' in measurements or 'state_changes' in measurements:
            print(f"  ✅ Core event measurements found")
        else:
            warnings.append("Expected measurements 'events' or 'state_changes' not found")
            print(f"  ⚠️  Expected measurements 'events' or 'state_changes' not found")
        
        print()
        
        # Summary
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print()
        
        print("📊 Statistics:")
        for stat in info:
            print(f"  - {stat}")
        print()
        
        if issues:
            print(f"❌ ISSUES FOUND ({len(issues)}):")
            for issue in issues:
                print(f"  - {issue}")
            print()
        else:
            print("✅ No critical issues found")
            print()
        
        if warnings:
            print(f"⚠️  WARNINGS ({len(warnings)}):")
            for warning in warnings:
                print(f"  - {warning}")
            print()
        
        # Recommendations
        print("=" * 80)
        print("RECOMMENDATIONS")
        print("=" * 80)
        print()
        
        if issues:
            print("🔧 Fix Critical Issues:")
            for issue in issues:
                if "No data found" in issue:
                    print(f"  - Investigate ingestion pipeline - check websocket-ingestion logs")
                elif "bucket not found" in issue.lower():
                    print(f"  - Create missing bucket: {PRIMARY_BUCKET}")
            print()
        
        if warnings:
            print("💡 Consider:")
            for warning in warnings:
                if "retention" in warning.lower():
                    print(f"  - Set retention policy to prevent unbounded growth")
                elif "data gaps" in warning.lower():
                    print(f"  - Investigate ingestion interruptions")
            print()
        
        if not issues and not warnings:
            print("✅ InfluxDB looks healthy! No issues found.")
            print()
        
        client.close()
        return len(issues) == 0
        
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
    success = check_influxdb_quality()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()

