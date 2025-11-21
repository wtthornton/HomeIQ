#!/usr/bin/env python3
"""Test the exact query the analysis uses"""
import asyncio
import sys

sys.path.insert(0, "/app/src")

from datetime import datetime, timedelta, timezone

from clients.data_api_client import DataAPIClient


async def test():
    print("=" * 70)
    print("TESTING EXACT ANALYSIS QUERY")
    print("=" * 70)

    client = DataAPIClient()

    # Use the exact same logic as daily_analysis.py
    start_date = datetime.now(timezone.utc) - timedelta(days=30)
    end_date = datetime.now(timezone.utc)

    print(f"Query: start={start_date.isoformat()}, end={end_date.isoformat()}, limit=100000")

    try:
        events_df = await client.fetch_events(
            start_time=start_date,
            end_time=end_date,
            limit=100000,
        )

        print(f"\n✅ Result: {len(events_df)} events")
        print(f"   Empty: {events_df.empty}")

        if not events_df.empty:
            print("\nFirst few events:")
            print(events_df.head())
            print(f"\nColumns: {list(events_df.columns)}")
            print("\nTime range in data:")
            print(f"   Earliest: {events_df['timestamp'].min()}")
            print(f"   Latest: {events_df['timestamp'].max()}")
        else:
            print("\n⚠️  DataFrame is empty!")
            print("   This matches what the analysis is seeing.")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.client.aclose()

if __name__ == "__main__":
    asyncio.run(test())

