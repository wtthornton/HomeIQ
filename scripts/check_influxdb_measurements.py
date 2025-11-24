#!/usr/bin/env python3
"""Quick check of InfluxDB measurements"""
import os
from influxdb_client import InfluxDBClient

url = os.getenv('INFLUXDB_URL', 'http://influxdb:8086')
token = os.getenv('INFLUXDB_TOKEN', 'ha-ingestor-token')
org = os.getenv('INFLUXDB_ORG', 'ha-ingestor')
bucket = os.getenv('INFLUXDB_BUCKET', 'home_assistant_events')

client = InfluxDBClient(url=url, token=token, org=org)
query_api = client.query_api()

# Get sample data
query = f'''
    from(bucket: "{bucket}")
      |> range(start: -1h)
      |> limit(n: 10)
'''

result = query_api.query(query)
tables = list(result)

print(f"Found {len(tables)} table(s)")
measurements = set()
for i, table in enumerate(tables):
    records = list(table.records)
    if records:
        measurement = records[0].get_measurement()
        measurements.add(measurement)
        print(f"  Table {i}: {len(records)} records, measurement: {measurement}")
        if records:
            print(f"    Sample tags: {list(records[0].values.keys())[:5]}")

print(f"\nUnique measurements: {sorted(measurements)}")
client.close()

