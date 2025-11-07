#!/usr/bin/env python3
"""Test script to verify synergy query filtering"""
import asyncio
import sys
from pathlib import Path

# Add service to path
sys.path.insert(0, str(Path(__file__).parent / "services" / "ai-automation-service" / "src"))

from database import get_db
from database.crud import get_synergy_opportunities

async def test_query():
    async for db in get_db():
        print("Testing query with synergy_type='event_context'...")
        results = await get_synergy_opportunities(
            db, 
            synergy_type='event_context', 
            min_confidence=0.0, 
            limit=20
        )
        print(f"Found {len(results)} results")
        if results:
            print("First 5 results:")
            for r in results[:5]:
                print(f"  - ID: {r.id}, Type: {r.synergy_type}, Confidence: {r.confidence}")
        else:
            print("No results found!")
        break

if __name__ == "__main__":
    asyncio.run(test_query())

