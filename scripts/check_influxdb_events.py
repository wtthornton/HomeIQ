#!/usr/bin/env python3
"""Check if events exist in InfluxDB"""
import os

from influxdb_client import InfluxDBClient

try:
    url = os.getenv("INFLUXDB_URL", "http://influxdb:8086")
    token = os.getenv("INFLUXDB_TOKEN", "homeiq-token")
    org = os.getenv("INFLUXDB_ORG", "homeiq")
    bucket = os.getenv("INFLUXDB_BUCKET", "home_assistant_events")

    print("=" * 70)
    print("CHECKING INFLUXDB FOR EVENTS")
    print("=" * 70)
    print(f"URL: {url}")
    print(f"Org: {org}")
    print(f"Bucket: {bucket}")
    print()

    client = InfluxDBClient(url=url, token=token, org=org)
    query_api = client.query_api()

    # Check last 30 days
    query_30d = f"""
        from(bucket: "{bucket}")
          |> range(start: -30d)
          |> limit(n: 10)
    """

    print("📊 Checking last 30 days...")
    result_30d = query_api.query(query_30d)
    events_30d = list(result_30d)
    total_records_30d = sum(len(list(table.records)) for table in events_30d)
    print(f"   Found {total_records_30d} records in {len(events_30d)} tables")

    # Check last 7 days
    query_7d = f"""
        from(bucket: "{bucket}")
          |> range(start: -7d)
          |> limit(n: 10)
    """

    print("📊 Checking last 7 days...")
    result_7d = query_api.query(query_7d)
    events_7d = list(result_7d)
    total_records_7d = sum(len(list(table.records)) for table in events_7d)
    print(f"   Found {total_records_7d} records in {len(events_7d)} tables")

    # Check all time
    query_all = f"""
        from(bucket: "{bucket}")
          |> range(start: 0)
          |> limit(n: 10)
    """

    print("📊 Checking all time...")
    result_all = query_api.query(query_all)
    events_all = list(result_all)
    total_records_all = sum(len(list(table.records)) for table in events_all)
    print(f"   Found {total_records_all} records in {len(events_all)} tables")

    # Get earliest and latest timestamps
    query_time_range = f"""
        from(bucket: "{bucket}")
          |> range(start: 0)
          |> first()
    """

    print("📊 Getting time range...")
    try:
        result_range = query_api.query(query_time_range)
        tables = list(result_range)
        if tables and len(tables) > 0:
            records = list(tables[0].records)
            if records:
                first_time = records[0].get_time()
                print(f"   First event: {first_time}")
    except:
        print("   Could not get first event")

    query_last = f"""
        from(bucket: "{bucket}")
          |> range(start: 0)
          |> last()
    """

    try:
        result_last = query_api.query(query_last)
        tables = list(result_last)
        if tables and len(tables) > 0:
            records = list(tables[0].records)
            if records:
                last_time = records[0].get_time()
                print(f"   Last event: {last_time}")
    except:
        print("   Could not get last event")

    # Count total events
    query_count = f"""
        from(bucket: "{bucket}")
          |> range(start: 0)
          |> count()
    """

    print("📊 Counting total events...")
    try:
        result_count = query_api.query(query_count)
        tables = list(result_count)
        if tables and len(tables) > 0:
            records = list(tables[0].records)
            if records:
                count = records[0].get_value()
                print(f"   Total events: {count}")
    except Exception as e:
        print(f"   Could not count events: {e}")

    print("=" * 70)

    if total_records_30d > 0:
        print("✅ Events found in last 30 days - Data API should be able to fetch them")
    else:
        print("⚠️  No events found in last 30 days")
        if total_records_all > 0:
            print("   But events exist in the database - may be older than 30 days")

    client.close()

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

