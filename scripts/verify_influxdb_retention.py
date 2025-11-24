#!/usr/bin/env python3
"""Verify InfluxDB retention policies"""
import os
from influxdb_client import InfluxDBClient

url = os.getenv('INFLUXDB_URL', 'http://influxdb:8086')
token = os.getenv('INFLUXDB_TOKEN', 'ha-ingestor-token')
org = os.getenv('INFLUXDB_ORG', 'ha-ingestor')

client = InfluxDBClient(url=url, token=token, org=org)
buckets = client.buckets_api().find_buckets()

print("Retention Policies:")
print("-" * 40)
for bucket in buckets.buckets:
    if bucket.name in ['home_assistant_events', 'weather_data']:
        if bucket.retention_rules and bucket.retention_rules[0].every_seconds:
            days = bucket.retention_rules[0].every_seconds // 86400
            print(f"{bucket.name}: {days} days")
        else:
            print(f"{bucket.name}: Infinite")

client.close()

