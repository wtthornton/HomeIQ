#!/usr/bin/env python3
"""
Monitor query performance for SQLite and InfluxDB.

This script tracks query execution times and generates performance reports.
"""
import sqlite3
import os
import sys
import time
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from influxdb_client import InfluxDBClient

# Configuration
DB_PATH = Path("/app/data/ai_automation.db")
INFLUXDB_URL = os.getenv('INFLUXDB_URL', 'http://localhost:8086')
INFLUXDB_TOKEN = os.getenv('INFLUXDB_TOKEN', 'ha-ingestor-token')
INFLUXDB_ORG = os.getenv('INFLUXDB_ORG', 'ha-ingestor')
PRIMARY_BUCKET = os.getenv('INFLUXDB_BUCKET', 'home_assistant_events')

# Performance thresholds
SQLITE_SLOW_QUERY_MS = 1000  # 1 second
INFLUXDB_SLOW_QUERY_MS = 5000  # 5 seconds

def test_sqlite_queries(conn):
    """Test common SQLite queries and measure performance"""
    print("Testing SQLite query performance...")
    print("-" * 80)
    
    test_queries = [
        {
            'name': 'Get suggestions by status',
            'query': "SELECT * FROM suggestions WHERE status = 'draft' ORDER BY created_at DESC LIMIT 10",
            'description': 'Common query: Filter by status with date sorting'
        },
        {
            'name': 'Get patterns by type',
            'query': "SELECT * FROM patterns WHERE pattern_type = 'time_of_day' ORDER BY confidence DESC LIMIT 10",
            'description': 'Common query: Filter by pattern type with confidence sorting'
        },
        {
            'name': 'Get user queries',
            'query': "SELECT * FROM ask_ai_queries WHERE user_id = 'anonymous' ORDER BY created_at DESC LIMIT 10",
            'description': 'Common query: User query history'
        },
        {
            'name': 'Join suggestions with patterns',
            'query': """
                SELECT s.*, p.pattern_type, p.confidence as pattern_confidence
                FROM suggestions s
                LEFT JOIN patterns p ON s.pattern_id = p.id
                WHERE s.status = 'draft'
                LIMIT 10
            """,
            'description': 'Common query: JOIN with patterns table'
        }
    ]
    
    results = []
    slow_queries = []
    
    for test in test_queries:
        try:
            cursor = conn.cursor()
            start_time = time.time()
            cursor.execute(test['query'])
            rows = cursor.fetchall()
            elapsed_ms = (time.time() - start_time) * 1000
            
            status = "✅" if elapsed_ms < SQLITE_SLOW_QUERY_MS else "⚠️"
            print(f"  {status} {test['name']}: {elapsed_ms:.2f}ms ({len(rows)} rows)")
            
            results.append({
                'name': test['name'],
                'query': test['query'],
                'elapsed_ms': elapsed_ms,
                'row_count': len(rows),
                'slow': elapsed_ms >= SQLITE_SLOW_QUERY_MS
            })
            
            if elapsed_ms >= SQLITE_SLOW_QUERY_MS:
                slow_queries.append({
                    'name': test['name'],
                    'elapsed_ms': elapsed_ms,
                    'description': test['description']
                })
        except sqlite3.Error as e:
            print(f"  ❌ {test['name']}: Error - {e}")
            results.append({
                'name': test['name'],
                'error': str(e),
                'slow': False
            })
    
    return results, slow_queries

def test_influxdb_queries(query_api, bucket):
    """Test common InfluxDB queries and measure performance"""
    print()
    print("Testing InfluxDB query performance...")
    print("-" * 80)
    
    test_queries = [
        {
            'name': 'Last 24 hours events',
            'query': f'''
                from(bucket: "{bucket}")
                  |> range(start: -24h)
                  |> filter(fn: (r) => r._measurement == "home_assistant_events")
                  |> limit(n: 100)
            ''',
            'description': 'Common query: Recent events'
        },
        {
            'name': 'Events by entity (last hour)',
            'query': f'''
                from(bucket: "{bucket}")
                  |> range(start: -1h)
                  |> filter(fn: (r) => r._measurement == "home_assistant_events")
                  |> filter(fn: (r) => r.entity_id == "light.living_room")
                  |> limit(n: 100)
            ''',
            'description': 'Common query: Filter by entity_id'
        },
        {
            'name': 'Hourly aggregation',
            'query': f'''
                from(bucket: "{bucket}")
                  |> range(start: -7d)
                  |> filter(fn: (r) => r._measurement == "home_assistant_events")
                  |> aggregateWindow(every: 1h, fn: count)
                  |> limit(n: 100)
            ''',
            'description': 'Common query: Time-based aggregation'
        }
    ]
    
    results = []
    slow_queries = []
    
    for test in test_queries:
        try:
            start_time = time.time()
            result = list(query_api.query(test['query'], org=INFLUXDB_ORG))
            elapsed_ms = (time.time() - start_time) * 1000
            
            # Count records
            record_count = sum(len(list(table.records)) for table in result)
            
            status = "✅" if elapsed_ms < INFLUXDB_SLOW_QUERY_MS else "⚠️"
            print(f"  {status} {test['name']}: {elapsed_ms:.2f}ms ({record_count} records)")
            
            results.append({
                'name': test['name'],
                'elapsed_ms': elapsed_ms,
                'record_count': record_count,
                'slow': elapsed_ms >= INFLUXDB_SLOW_QUERY_MS
            })
            
            if elapsed_ms >= INFLUXDB_SLOW_QUERY_MS:
                slow_queries.append({
                    'name': test['name'],
                    'elapsed_ms': elapsed_ms,
                    'description': test['description']
                })
        except Exception as e:
            print(f"  ❌ {test['name']}: Error - {e}")
            results.append({
                'name': test['name'],
                'error': str(e),
                'slow': False
            })
    
    return results, slow_queries

def generate_report(sqlite_results, sqlite_slow, influxdb_results, influxdb_slow):
    """Generate performance report"""
    print()
    print("=" * 80)
    print("PERFORMANCE REPORT")
    print("=" * 80)
    print()
    
    # SQLite summary
    if sqlite_results:
        sqlite_avg = sum(r.get('elapsed_ms', 0) for r in sqlite_results if 'elapsed_ms' in r) / len([r for r in sqlite_results if 'elapsed_ms' in r])
        print(f"SQLite Performance:")
        print(f"  Queries tested: {len(sqlite_results)}")
        print(f"  Average execution time: {sqlite_avg:.2f}ms")
        print(f"  Slow queries (>={SQLITE_SLOW_QUERY_MS}ms): {len(sqlite_slow)}")
        print()
    
    # InfluxDB summary
    if influxdb_results:
        influxdb_times = [r.get('elapsed_ms', 0) for r in influxdb_results if 'elapsed_ms' in r]
        if influxdb_times:
            influxdb_avg = sum(influxdb_times) / len(influxdb_times)
            print(f"InfluxDB Performance:")
            print(f"  Queries tested: {len(influxdb_results)}")
            print(f"  Average execution time: {influxdb_avg:.2f}ms")
            print(f"  Slow queries (>={INFLUXDB_SLOW_QUERY_MS}ms): {len(influxdb_slow)}")
        else:
            print(f"InfluxDB Performance:")
            print(f"  Queries tested: {len(influxdb_results)}")
            print(f"  Average execution time: N/A (no successful queries)")
            print(f"  Slow queries (>={INFLUXDB_SLOW_QUERY_MS}ms): {len(influxdb_slow)}")
        print()
    
    # Slow queries
    if sqlite_slow or influxdb_slow:
        print("⚠️  SLOW QUERIES DETECTED:")
        print("-" * 80)
        
        if sqlite_slow:
            print("\nSQLite Slow Queries:")
            for query in sqlite_slow:
                print(f"  - {query['name']}: {query['elapsed_ms']:.2f}ms")
                print(f"    {query['description']}")
                print(f"    Recommendation: Check indexes, use EXPLAIN QUERY PLAN")
        
        if influxdb_slow:
            print("\nInfluxDB Slow Queries:")
            for query in influxdb_slow:
                print(f"  - {query['name']}: {query['elapsed_ms']:.2f}ms")
                print(f"    {query['description']}")
                print(f"    Recommendation: Optimize time range, add tag filters, check retention policy")
        
        print()
    else:
        print("✅ No slow queries detected")
        print()

def main():
    """Main entry point"""
    print("=" * 80)
    print("QUERY PERFORMANCE MONITORING")
    print("=" * 80)
    print()
    print(f"SQLite Database: {DB_PATH}")
    print(f"InfluxDB Bucket: {PRIMARY_BUCKET}")
    print()
    print(f"Thresholds:")
    print(f"  SQLite slow query: >={SQLITE_SLOW_QUERY_MS}ms")
    print(f"  InfluxDB slow query: >={INFLUXDB_SLOW_QUERY_MS}ms")
    print()
    
    sqlite_results = []
    sqlite_slow = []
    influxdb_results = []
    influxdb_slow = []
    
    # Test SQLite
    if DB_PATH.exists():
        try:
            conn = sqlite3.connect(str(DB_PATH))
            conn.execute("PRAGMA foreign_keys=ON")
            sqlite_results, sqlite_slow = test_sqlite_queries(conn)
            conn.close()
        except Exception as e:
            print(f"❌ SQLite error: {e}")
    else:
        print("⚠️  SQLite database not found")
    
    # Test InfluxDB
    try:
        client = InfluxDBClient(
            url=INFLUXDB_URL,
            token=INFLUXDB_TOKEN,
            org=INFLUXDB_ORG
        )
        query_api = client.query_api()
        influxdb_results, influxdb_slow = test_influxdb_queries(query_api, PRIMARY_BUCKET)
        client.close()
    except Exception as e:
        print(f"❌ InfluxDB error: {e}")
    
    # Generate report
    generate_report(sqlite_results, sqlite_slow, influxdb_results, influxdb_slow)
    
    return len(sqlite_slow) == 0 and len(influxdb_slow) == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

