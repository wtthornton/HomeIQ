"""
Diagnostic script to check why nightly suggestions aren't being created or displayed.
Run this to investigate the issue.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.ai_automation_service.src.database.models import get_db_session
from services.ai_automation_service.src.database.crud import get_suggestions
from sqlalchemy import select, func
from services.ai_automation_service.src.database.models import Suggestion
from datetime import datetime, timedelta, timezone

async def check_suggestions():
    """Check suggestions in database"""
    print("=" * 80)
    print("DIAGNOSTIC: Checking Nightly Suggestions")
    print("=" * 80)
    
    async with get_db_session() as db:
        # Get all suggestions
        all_suggestions = await get_suggestions(db, status=None, limit=100)
        print(f"\n📊 Total suggestions in database: {len(all_suggestions)}")
        
        # Group by status
        status_counts = {}
        for s in all_suggestions:
            status = s.status or 'null'
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print(f"\n📈 Status breakdown:")
        for status, count in sorted(status_counts.items()):
            print(f"   - {status}: {count}")
        
        # Get recent suggestions (last 7 days)
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        recent_query = select(Suggestion).where(
            Suggestion.created_at >= seven_days_ago
        ).order_by(Suggestion.created_at.desc())
        
        result = await db.execute(recent_query)
        recent_suggestions = result.scalars().all()
        
        print(f"\n📅 Recent suggestions (last 7 days): {len(recent_suggestions)}")
        
        if recent_suggestions:
            print("\n🔍 Recent suggestion details:")
            for s in recent_suggestions[:10]:  # Show first 10
                print(f"   - ID: {s.id}, Status: {s.status}, Created: {s.created_at}")
                print(f"     Title: {s.title[:60]}...")
                print(f"     Confidence: {s.confidence:.2f}")
        
        # Check for draft suggestions specifically
        draft_query = select(Suggestion).where(
            Suggestion.status == 'draft'
        ).order_by(Suggestion.created_at.desc())
        
        result = await db.execute(draft_query)
        draft_suggestions = result.scalars().all()
        
        print(f"\n📝 Draft suggestions: {len(draft_suggestions)}")
        
        # Check suggestions created today
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        today_query = select(Suggestion).where(
            Suggestion.created_at >= today_start
        ).order_by(Suggestion.created_at.desc())
        
        result = await db.execute(today_query)
        today_suggestions = result.scalars().all()
        
        print(f"\n📆 Suggestions created today: {len(today_suggestions)}")
        
        if today_suggestions:
            print("\n🔍 Today's suggestions:")
            for s in today_suggestions:
                print(f"   - ID: {s.id}, Status: {s.status}, Created: {s.created_at}")
                print(f"     Title: {s.title[:60]}...")
        else:
            print("\n⚠️  No suggestions created today!")
            print("   This suggests the nightly job may not be running or not creating suggestions.")
        
        # Check for suggestions with pattern_id (from nightly job)
        pattern_query = select(Suggestion).where(
            Suggestion.pattern_id.isnot(None)
        ).order_by(Suggestion.created_at.desc())
        
        result = await db.execute(pattern_query)
        pattern_suggestions = result.scalars().all()
        
        print(f"\n🔗 Suggestions with pattern_id (from nightly job): {len(pattern_suggestions)}")
        
        if pattern_suggestions:
            print("\n🔍 Pattern-based suggestions:")
            for s in pattern_suggestions[:5]:
                print(f"   - ID: {s.id}, Pattern ID: {s.pattern_id}, Status: {s.status}")
                print(f"     Created: {s.created_at}")
                print(f"     Title: {s.title[:60]}...")
        
    print("\n" + "=" * 80)
    print("Diagnostic complete!")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(check_suggestions())

