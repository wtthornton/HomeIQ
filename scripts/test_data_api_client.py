#!/usr/bin/env python3
"""Test DataAPIClient fetch_events"""
import asyncio
import sys
sys.path.insert(0, '/app/src')

from clients.data_api_client import DataAPIClient
from datetime import datetime, timedelta, timezone

async def test():
    print("=" * 70)
    print("TESTING DataAPIClient.fetch_events")
    print("=" * 70)
    
    client = DataAPIClient()
    start = datetime.now(timezone.utc) - timedelta(days=30)
    end = datetime.now(timezone.utc)
    
    print(f"Fetching events from {start} to {end}...")
    
    try:
        df = await client.fetch_events(start_time=start, end_time=end, limit=100)
        print(f"\n✅ Got DataFrame with {len(df)} rows")
        print(f"   Empty: {df.empty}")
        print(f"   Columns: {list(df.columns)}")
        
        if not df.empty:
            print(f"\nFirst few rows:")
            print(df.head())
        else:
            print("\n⚠️  DataFrame is empty!")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.client.aclose()

if __name__ == "__main__":
    asyncio.run(test())

