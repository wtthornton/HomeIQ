"""
InfluxDB quality checks.
Extracted from check_influxdb_quality.py for modularity.
"""
from collections import defaultdict
from datetime import datetime, timedelta
from typing import List, Tuple, Dict, Set

from influxdb_client import InfluxDBClient
from influxdb_client.client.exceptions import InfluxDBError


def check_connection(client: InfluxDBClient) -> Tuple[bool, List[str]]:
    """Check InfluxDB connection and health."""
    issues = []
    
    try:
        health = client.health()
        if health.status == "pass":
            return True, issues
        else:
            issues.append(f"InfluxDB health check: {health.status}")
            return False, issues
    except Exception as e:
        issues.append(f"InfluxDB connection failed: {e}")
        return False, issues


def check_buckets(client: InfluxDBClient, primary_bucket: str) -> Tuple[Dict, List[str], List[str]]:
    """Check bucket configuration and retention policies."""
    issues = []
    warnings = []
    bucket_info = {}
    
    buckets_api = client.buckets_api()
    buckets = buckets_api.find_buckets()
    
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
        
        if not retention_days:
            warnings.append(f"{bucket.name}: No retention policy set (infinite retention)")
    
    if not any(b.name == primary_bucket for b in buckets.buckets):
        issues.append(f"Primary bucket '{primary_bucket}' not found")
    
    return bucket_info, issues, warnings


def check_data_volume(client: InfluxDBClient, bucket: str) -> Tuple[Dict[str, int], List[str], List[str]]:
    """Check data volume for different time ranges."""
    issues = []
    warnings = []
    volumes = {}
    
    query_api = client.query_api()
    
    # Check last 30 days
    query_30d = f'''
        from(bucket: "{bucket}")
          |> range(start: -30d)
          |> count()
    '''
    try:
        result_30d = query_api.query(query_30d)
        total_records_30d = sum(len(list(table.records)) for table in result_30d)
        volumes['30d'] = total_records_30d
    except Exception as e:
        warnings.append(f"Could not query 30-day data: {e}")
        volumes['30d'] = 0
    
    # Check last 7 days
    query_7d = f'''
        from(bucket: "{bucket}")
          |> range(start: -7d)
          |> count()
    '''
    try:
        result_7d = query_api.query(query_7d)
        total_records_7d = sum(len(list(table.records)) for table in result_7d)
        volumes['7d'] = total_records_7d
    except Exception as e:
        warnings.append(f"Could not query 7-day data: {e}")
        volumes['7d'] = 0
    
    # Check last 24 hours
    query_24h = f'''
        from(bucket: "{bucket}")
          |> range(start: -24h)
          |> count()
    '''
    try:
        result_24h = query_api.query(query_24h)
        total_records_24h = sum(len(list(table.records)) for table in result_24h)
        volumes['24h'] = total_records_24h
    except Exception as e:
        warnings.append(f"Could not query 24-hour data: {e}")
        volumes['24h'] = 0
    
    if volumes['24h'] == 0 and volumes['7d'] == 0:
        issues.append("No data found in last 7 days - possible ingestion issue")
    elif volumes['24h'] == 0:
        warnings.append("No data in last 24 hours - possible recent ingestion issue")
    
    return volumes, issues, warnings


def check_measurements(client: InfluxDBClient, bucket: str) -> Tuple[Set[str], Dict[str, int], List[str], List[str]]:
    """Check available measurements and their record counts."""
    issues = []
    warnings = []
    measurements = set()
    measurement_counts = {}
    
    query_api = client.query_api()
    
    query_measurements = f'''
        from(bucket: "{bucket}")
          |> range(start: -7d)
          |> keys()
          |> keep(columns: ["_measurement"])
          |> distinct()
    '''
    
    try:
        result_meas = query_api.query(query_measurements)
        for table in result_meas:
            for record in table.records:
                if record.get_value():
                    measurements.add(record.get_value())
        
        for measurement in sorted(measurements):
            query_count = f'''
                from(bucket: "{bucket}")
                  |> range(start: -7d)
                  |> filter(fn: (r) => r["_measurement"] == "{measurement}")
                  |> count()
            '''
            try:
                result_count = query_api.query(query_count)
                count = sum(len(list(table.records)) for table in result_count)
                measurement_counts[measurement] = count
            except Exception as e:
                warnings.append(f"Error counting {measurement}: {e}")
        
        if not measurements:
            issues.append("No measurements found in last 7 days")
    except Exception as e:
        warnings.append(f"Could not query measurements: {e}")
    
    return measurements, measurement_counts, issues, warnings


def check_data_gaps(client: InfluxDBClient, bucket: str) -> Tuple[int, List[str]]:
    """Check for data gaps in the last 24 hours."""
    warnings = []
    
    query_api = client.query_api()
    
    query_gaps = f'''
        from(bucket: "{bucket}")
          |> range(start: -24h)
          |> aggregateWindow(every: 1h, fn: count, createEmpty: true)
          |> filter(fn: (r) => r._value == 0)
    '''
    
    try:
        result_gaps = query_api.query(query_gaps)
        gap_count = sum(len(list(table.records)) for table in result_gaps)
        if gap_count > 0:
            warnings.append(f"Found {gap_count} hours with no data in last 24 hours")
        return gap_count, warnings
    except Exception as e:
        warnings.append(f"Could not check for data gaps: {e}")
        return 0, warnings


def check_tag_cardinality(client: InfluxDBClient, bucket: str, threshold: int = 10000) -> Tuple[Dict[str, int], List[str]]:
    """Check tag cardinality for common tags."""
    warnings = []
    cardinalities = {}
    
    tags_to_check = ['entity_id', 'device_id', 'area_id', 'domain', 'event_type']
    query_api = client.query_api()
    
    for tag_name in tags_to_check:
        try:
            query_cardinality = f'''
                from(bucket: "{bucket}")
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
            
            for table in result_cardinality:
                for record in table.records:
                    value = record.get_value()
                    if value is not None:
                        try:
                            cardinality = int(value)
                            break
                        except (ValueError, TypeError):
                            pass
            
            cardinalities[tag_name] = cardinality
            
            if cardinality >= threshold:
                warnings.append(f"High cardinality tag '{tag_name}': {cardinality:,} values (threshold: {threshold:,})")
            elif cardinality == 0:
                warnings.append(f"Tag '{tag_name}' has no values in last 7 days")
        except Exception as e:
            warnings.append(f"Could not check cardinality for {tag_name}: {e}")
    
    return cardinalities, warnings


def check_schema_consistency(client: InfluxDBClient, bucket: str) -> Tuple[Dict[str, Set[str]], Dict[str, Set[str]], List[str]]:
    """Check schema consistency by sampling recent records."""
    warnings = []
    field_counts = defaultdict(set)
    tag_counts = defaultdict(set)
    
    query_api = client.query_api()
    
    query_sample = f'''
        from(bucket: "{bucket}")
          |> range(start: -1h)
          |> limit(n: 100)
    '''
    
    try:
        result_sample = query_api.query(query_sample)
        
        for table in result_sample:
            for record in table.records:
                measurement = record.get_measurement()
                if measurement:
                    # Collect fields
                    for field in record.values:
                        if field.startswith('_') and field not in ('_time', '_measurement', '_field'):
                            field_counts[measurement].add(field)
                    # Collect tags
                    for tag in record.values:
                        if not tag.startswith('_'):
                            tag_counts[measurement].add(tag)
        
        if not field_counts and not tag_counts:
            warnings.append("Could not analyze schema - no recent data")
    except Exception as e:
        warnings.append(f"Could not check schema: {e}")
    
    return dict(field_counts), dict(tag_counts), warnings

