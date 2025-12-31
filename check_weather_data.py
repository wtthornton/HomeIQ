#!/usr/bin/env python3
"""Quick script to check weather data in InfluxDB"""
import os
import sys
from influxdb_client_3 import InfluxDBClient3
from dotenv import load_dotenv

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

load_dotenv()

# Connect to InfluxDB
client = InfluxDBClient3(
    token=os.getenv('INFLUXDB_TOKEN', 'homeiq_admin_token_2024'),
    host='localhost',
    port=8086,
    database='weather_data',
    org='home_assistant'
)

try:
    # Query recent weather data
    query = 'SELECT * FROM weather ORDER BY time DESC LIMIT 10'
    result = client.query(query)
    
    print("=" * 60)
    print("Recent Weather Data in InfluxDB")
    print("=" * 60)
    
    if result:
        count = 0
        for row in result:
            count += 1
            print(f"\nRecord {count}:")
            print(f"  Time: {row.get('time', 'N/A')}")
            print(f"  Location: {row.get('location', 'N/A')}")
            print(f"  Temperature: {row.get('temperature', 'N/A')}C")
            print(f"  Condition: {row.get('condition', 'N/A')}")
            print(f"  Humidity: {row.get('humidity', 'N/A')}%")
            print(f"  Pressure: {row.get('pressure', 'N/A')} hPa")
            print(f"  Wind Speed: {row.get('wind_speed', 'N/A')} m/s")
        
        print(f"\n[OK] Found {count} recent weather records")
    else:
        print("[FAIL] No weather data found in InfluxDB")
        
except Exception as e:
    print(f"[ERROR] Error querying InfluxDB: {e}")
